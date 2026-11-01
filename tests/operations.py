#!/usr/bin/env python3
"""Pruebas sin root, sin Docker, sin SMTP real y sin modificar el servidor."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

# En Windows no se ejercita flock: todos los comandos/servicios estan simulados.
try:
    import fcntl
except ImportError:
    sys.modules['fcntl'] = types.ModuleType('fcntl')


def load(name):
    path = Path(__file__).resolve().parents[1] / 'scripts' / name
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


space = load('cloud-space')
recovery = load('cloud-recovery')


class SpaceTests(unittest.TestCase):
    def test_thresholds_and_hysteresis(self):
        self.assertEqual([space.level(p) for p in (60, 75, 84, 85, 90, 100)],
                         [0, 75, 75, 85, 90, 90])
        self.assertEqual(space.transition(90, 88), 90)
        self.assertEqual(space.transition(90, 86), 85)
        self.assertEqual(space.transition(75, 71), 0)

    def test_delivery_retry_recovery_and_reminder(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / 'state.json'
            with patch.object(space, 'measurement', return_value=(76, 1000)), \
                 patch.object(space.subprocess, 'run', return_value=types.SimpleNamespace(returncode=1)), \
                 patch.object(space.time, 'time', return_value=100000), \
                 patch.object(space, 'send') as mail:
                space.check({}, state)
                self.assertEqual(mail.call_count, 1)
                space.check({}, state)
                self.assertEqual(mail.call_count, 1)
                with patch.object(space.time, 'time', return_value=200000):
                    space.check({}, state)
                self.assertEqual(mail.call_count, 2)
                with patch.object(space, 'measurement', return_value=(91, 100)):
                    space.check({}, state)
                self.assertEqual(json.loads(state.read_text())['SSD']['level'], 90)
                with patch.object(space, 'measurement', return_value=(50, 10000)):
                    space.check({}, state)
                self.assertEqual(json.loads(state.read_text())['SSD']['level'], 0)
                with patch.object(space, 'send', side_effect=OSError('SMTP no disponible')):
                    with self.assertRaises(OSError):
                        space.check({}, state)
                self.assertEqual(json.loads(state.read_text())['SSD']['level'], 0)
                space.check({}, state)
                self.assertEqual(json.loads(state.read_text())['SSD']['level'], 75)

    def test_absent_usb_not_measured(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(space, 'measurement', return_value=(10, 10000)) as measure, \
             patch.object(space.subprocess, 'run', return_value=types.SimpleNamespace(returncode=1)):
            space.check({}, Path(tmp) / 'state.json')
            measure.assert_called_once_with('/')


class RecoveryTests(unittest.TestCase):
    def exercise_transfer(self, fail):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            control, units = base / 'control', base / 'units'
            control.mkdir()
            units.mkdir()
            marker = control / 'recovery-maintenance'
            marker.write_text('punto anterior')
            (control / 'recovery-freeze-restored').write_text('congelado')
            (units / 'cloud-restore@.service').write_text('unidad anterior')
            point = base / 'punto-nuevo'
            manifest = {'storage_uuid': 'uuid', 'architecture': recovery.platform.machine()}
            effect = RuntimeError('preparacion interrumpida') if fail else None
            with patch.object(recovery, 'CONTROL', control), \
                 patch.object(recovery, 'SYSTEMD', units), \
                 patch.object(recovery, 'MARKER', marker), \
                 patch.object(recovery, 'verify', return_value=(point, manifest)), \
                 patch.object(recovery, 'storage_uuid', return_value='uuid'), \
                 patch.object(recovery, 'assert_stopped'), \
                 patch.object(recovery, 'run'), \
                 patch.object(recovery.subprocess, 'run', return_value=types.SimpleNamespace(stdout='not-found')), \
                 patch.object(recovery, 'prepare', side_effect=effect) as prepare:
                if fail:
                    with self.assertRaisesRegex(RuntimeError, 'interrumpida'):
                        recovery.prepare_next(point)
                else:
                    recovery.prepare_next(point)
                prepare.assert_called_once_with(point)
            history = list(control.glob('before-restore.*'))
            self.assertEqual(len(history), 1)
            self.assertEqual((history[0] / 'cloud-restore@.service').read_text(), 'unidad anterior')
            self.assertEqual((history[0] / 'recovery-maintenance').read_text(), 'punto anterior')
            self.assertEqual(Path(marker.read_text().strip()), point)
            self.assertEqual((control / 'recovery-next-started').exists(), fail)

    def test_transfer_preserves_previous_controls(self):
        self.exercise_transfer(False)

    def test_interrupted_transfer_keeps_guard_and_history(self):
        self.exercise_transfer(True)

    def test_no_resume_after_restore_started(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'maintenance'
            marker.write_text('/point')
            with patch.object(recovery, 'MARKER', marker), \
                 patch.object(recovery.Path, 'exists', return_value=True), \
                 patch.object(recovery, 'run') as command:
                with self.assertRaisesRegex(RuntimeError, 'restauracion'):
                    recovery.resume_source()
                command.assert_not_called()
                self.assertTrue(marker.is_file())

    def test_failed_start_restores_guard_and_stops_services(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'maintenance'
            marker.write_text('/point')
            calls = []

            def command(args, **kwargs):
                calls.append(args)
                if args[:2] == ['systemctl', 'start']:
                    raise RuntimeError('arranque fallido')

            with patch.object(recovery, 'MARKER', marker), \
                 patch.object(recovery.Path, 'exists', return_value=False), \
                 patch.object(recovery.Path, 'glob', return_value=[]), \
                 patch.object(recovery, 'verify', return_value=(Path('/point'), {'prefix': 'cloud', 'storage_uuid': 'uuid'})), \
                 patch.object(recovery, 'storage_uuid', return_value='uuid'), \
                 patch.object(recovery, 'assert_stopped'), \
                 patch.object(recovery, 'run', side_effect=command):
                with self.assertRaisesRegex(RuntimeError, 'arranque fallido'):
                    recovery.resume_source()
            self.assertEqual(Path(marker.read_text().strip()), Path('/point'))
            self.assertEqual(calls[-1][:2], ['systemctl', 'stop'])

    def test_new_host_rejects_existing_state_before_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'projects/nextcloud').mkdir(parents=True)
            (base / 'projects/nextcloud/.env').write_text('dato de prueba')
            marker = base / 'maintenance'
            with patch.object(recovery, 'PROJECTS', base / 'projects'), \
                 patch.object(recovery, 'MARKER', marker), \
                 patch.object(recovery, 'verify', return_value=(base, {'architecture': recovery.platform.machine(), 'storage_uuid': 'uuid'})), \
                 patch.object(recovery, 'storage_uuid', return_value='uuid'):
                with self.assertRaisesRegex(RuntimeError, 'instalacion de origen'):
                    recovery.prepare(base, new_host=True)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
