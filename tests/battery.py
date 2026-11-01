#!/usr/bin/env python3
"""Pruebas simuladas: nunca consultan el equipo, SMTP ni ejecutan systemctl."""
import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('battery', str(ROOT / 'scripts/cloud-battery'))
spec = importlib.util.spec_from_loader(loader.name, loader)
battery = importlib.util.module_from_spec(spec)
loader.exec_module(battery)
CONFIG = {'shutdown_percent': 50, 'external_power_confirmed': True}


class BatteryTests(unittest.TestCase):
    def test_threshold_only_without_mains(self):
        self.assertFalse(battery.decision(20, False, 50))
        self.assertFalse(battery.decision(51, True, 50))
        self.assertTrue(battery.decision(50, True, 50))

    def test_low_battery_acts_even_without_smtp(self):
        with patch.object(battery, 'reading', return_value=(40, True, 'Discharging')), \
             patch.object(battery, 'notify', return_value=False), \
             patch.object(battery.subprocess, 'run') as run:
            battery.check(CONFIG)
            run.assert_called_once_with(
                ['systemctl', 'start', '--no-block', 'cloud-battery-shutdown.service'], check=True)

    def test_mains_and_high_battery_do_not_start_job(self):
        for reading in ((10, False, 'Charging'), (80, True, 'Discharging')):
            with tempfile.TemporaryDirectory() as tmp, \
                 patch.object(battery, 'reading', return_value=reading), \
                 patch.object(battery, 'notify', return_value=True) as mail, \
                 patch.object(battery.subprocess, 'run') as run:
                state = Path(tmp) / 'state.json'
                battery.check(CONFIG, state)
                battery.check(CONFIG, state)
                self.assertEqual(mail.call_count, 1)
                run.assert_not_called()

    def test_unconfirmed_external_cannot_arm(self):
        with patch.object(battery, 'reading') as reading:
            with self.assertRaisesRegex(RuntimeError, 'externo'):
                battery.check(dict(CONFIG, external_power_confirmed=False))
            reading.assert_not_called()

    def test_invalid_threshold_rejected(self):
        for value in (0, 19, 96, True, '50'):
            with self.assertRaises(RuntimeError):
                battery.check(dict(CONFIG, shutdown_percent=value))

    def test_invalid_sensor_does_not_start_job(self):
        with patch.object(battery, 'reading', side_effect=OSError('sensor ausente')), \
             patch.object(battery.subprocess, 'run') as run:
            with self.assertRaises(OSError):
                battery.check(CONFIG)
            run.assert_not_called()

    def test_sysfs_readings_and_absent_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bat, ac = root / 'BAT1', root / 'ACAD'
            bat.mkdir()
            ac.mkdir()
            for path, value in ((bat / 'type', 'Battery'), (bat / 'capacity', '42'),
                                (bat / 'status', 'Discharging'), (ac / 'type', 'Mains'),
                                (ac / 'online', '0')):
                path.write_text(value)
            with patch.object(battery, 'SUPPLIES', root):
                self.assertEqual(battery.reading(), (42, True, 'Discharging'))
                (ac / 'online').write_text('1')
                self.assertEqual(battery.reading(), (42, False, 'Discharging'))
                (ac / 'type').write_text('USB')
                with self.assertRaises(RuntimeError):
                    battery.reading()

    def test_shutdown_even_if_notification_crashes(self):
        with patch.object(battery, 'notify', side_effect=RuntimeError('fallo SMTP')), \
             patch.object(battery.subprocess, 'run') as run:
            with self.assertRaises(RuntimeError):
                battery.finish()
            run.assert_called_once_with(['systemctl', '--no-block', 'poweroff'], check=True, timeout=15)

    def test_job_bounds_entire_group_and_shuts_down_on_failure(self):
        unit = (ROOT / 'systemd/cloud-battery-shutdown.service').read_text()
        for expected in ('TimeoutStartSec=10min', 'KillMode=control-group',
                         'ExecStopPost=/usr/local/sbin/cloud-battery finish',
                         'ExecStartPre=/usr/local/sbin/cloud-storage-check'):
            self.assertIn(expected, unit)


if __name__ == '__main__':
    unittest.main()
