#!/usr/bin/env python3
"""Pruebas locales de seleccion de imagenes, sin servidor ni Docker."""
import importlib.machinery
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

try:
    import fcntl
except ImportError:
    sys.modules['fcntl'] = types.ModuleType('fcntl')

root = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('cloud_update', str(root / 'scripts/cloud-update'))
spec = importlib.util.spec_from_loader(loader.name, loader)
update = importlib.util.module_from_spec(spec)
loader.exec_module(update)


class UpdateTests(unittest.TestCase):
    def test_immich_patch_changes_only_both_application_images(self):
        source = (root / 'immich/compose.yaml').read_text(encoding='utf-8')
        old, changed = update.plan_change('immich', source, '3.3.6')
        self.assertEqual(old, (3, 3, 3))
        self.assertEqual(changed.count(':v3.3.6'), 2)
        self.assertEqual(source.replace(':v3.3.3', ':v3.3.6'), changed)

    def test_nextcloud_preserves_anchor_and_other_images(self):
        source = (root / 'nextcloud/compose.yaml').read_text(encoding='utf-8')
        _, changed = update.plan_change('nextcloud', source, '35.0.3')
        self.assertEqual(source.replace('nextcloud:35.0.2-apache', 'nextcloud:35.0.3-apache'), changed)

    def test_rejects_major_minor_equal_and_older(self):
        source = (root / 'immich/compose.yaml').read_text(encoding='utf-8')
        for version in ('4.0.0', '3.4.0', '3.3.3', '3.3.2', 'latest'):
            with self.subTest(version=version), self.assertRaises(RuntimeError):
                update.plan_change('immich', source, version)

    def test_rejects_mismatched_images(self):
        source = (root / 'immich/compose.yaml').read_text(encoding='utf-8')
        source = source.replace('immich-machine-learning:v3.3.3', 'immich-machine-learning:v3.3.2')
        with self.assertRaises(RuntimeError):
            update.plan_change('immich', source, '3.3.6')

    def test_health_retries_when_container_is_replaced(self):
        inspect_error = update.subprocess.CalledProcessError(1, 'docker inspect', stderr='No such object')
        with patch.object(update, 'compose', side_effect=['server', 'old-id', 'new-id']), \
             patch.object(update, 'run', side_effect=[inspect_error, 'running healthy']) as inspect, \
             patch.object(update.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)), \
             patch.object(update.time, 'sleep') as sleep:
            update.healthy('immich')
        self.assertEqual(inspect.call_count, 2)
        sleep.assert_called_once_with(5)

    def test_check_images_rejects_old_running_image(self):
        with patch.object(update, 'compose', return_value='container-id'), \
             patch.object(update, 'run', return_value='ghcr.io/immich-app/immich-server:v3.3.3'):
            with self.assertRaisesRegex(RuntimeError, 'no la imagen esperada'):
                update.check_images('immich', '3.3.6')

    def test_backup_creates_and_verifies_one_new_point(self):
        old = Path('/tmp/old')
        new = Path('/tmp/new')
        with patch.object(update, 'points', side_effect=[[old], [old, new]]), \
             patch.object(update, 'healthy') as healthy, patch.object(update, 'report'), \
             patch.object(update, 'run') as run:
            self.assertEqual(update.backup_point(), new)
        self.assertEqual(healthy.call_count, 4)
        run.assert_any_call(update.TOOL, 'backup-and-resume')
        run.assert_any_call(update.TOOL, 'verify', new)

    def test_failed_download_restores_compose_without_restart_or_pruning(self):
        source = (root / 'immich/compose.yaml').read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'immich'
            project.mkdir()
            path = project / 'compose.yaml'
            path.write_text(source, encoding='utf-8')
            before = Path(directory) / 'old'
            point = Path(directory) / 'new'
            def fake_compose(app, *args, **kwargs):
                if args[0] == 'pull':
                    raise update.subprocess.CalledProcessError(1, 'pull')
            with patch.object(update, 'ROOT', Path(directory)), \
                 patch.object(update.os, 'geteuid', return_value=0, create=True), \
                 patch.object(update.os, 'chown', create=True), \
                 patch.object(update, 'points', side_effect=[[before], [before, point]]), \
                 patch.object(update, 'healthy'), patch.object(update, 'report'), \
                 patch.object(update, 'compose', side_effect=fake_compose), \
                 patch.object(update, 'run') as run, patch.object(update, 'prune') as prune:
                with self.assertRaises(update.subprocess.CalledProcessError):
                    update.update('immich', '3.3.6')
                self.assertEqual(path.read_text(encoding='utf-8'), source)
                self.assertFalse(any(call.args[:2] == ('systemctl', 'restart') for call in run.call_args_list))
                prune.assert_not_called()

    def test_prune_keeps_four_most_recent_complete_points(self):
        with tempfile.TemporaryDirectory() as directory:
            points = Path(directory)
            for day in range(1, 6):
                point = points / f'2026110{day}T120000Z.abc123'
                point.mkdir()
                (point / 'COMPLETE').write_text('test')
            newest = points / '20261105T120000Z.abc123'
            with patch.object(update, 'POINTS', points), patch.object(update, 'run'), \
                 patch.object(update.fcntl, 'flock', create=True), \
                 patch.object(update.fcntl, 'LOCK_EX', 1, create=True), \
                 patch.object(update.fcntl, 'LOCK_NB', 2, create=True), \
                 patch('builtins.open', return_value=io.StringIO()):
                update.prune(newest)
            self.assertEqual(len(list(points.iterdir())), 4)
            self.assertFalse((points / '20261101T120000Z.abc123').exists())
            self.assertTrue(newest.exists())

    def test_verification_failure_never_prunes(self):
        with tempfile.TemporaryDirectory() as directory:
            points = Path(directory)
            for day in range(1, 6):
                point = points / f'2026110{day}T120000Z.abc123'
                point.mkdir()
                (point / 'COMPLETE').write_text('test')
            with patch.object(update, 'POINTS', points), \
                 patch.object(update, 'run', side_effect=update.subprocess.CalledProcessError(1, 'verify')):
                with self.assertRaises(update.subprocess.CalledProcessError):
                    update.prune(points / '20261105T120000Z.abc123')
            self.assertEqual(len(list(points.iterdir())), 5)


if __name__ == '__main__':
    unittest.main()
