"""Safety tests use only temporary fake sysfs and deterministic in-memory devices."""
import copy
import http.client
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/app/bin'))
from hardware import Hardware, HardwareError
import controller as controller_module
import server as server_module
from controller import Controller, DEFAULT_CONFIG, validate_config
from server import Auth, FanServer


class TrackingHardware(Hardware):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []

    def write(self, cid, value=None, enable=None):
        self.writes.append((cid, value, enable))
        return super().write(cid, value=value, enable=enable)


class FakeHardwareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / 'sys/class/hwmon'
        self.root.mkdir(parents=True)
        self.chip = self.base / 'sys/devices/platform/demo-controller.0/hwmon/hwmon10'
        self.chip.mkdir(parents=True)
        for name, value in {'name': 'demo-controller', 'pwm1': '70', 'pwm1_enable': '2', 'pwm2': '81',
                            'pwm2_enable': '1', 'fan1_input': '1250', 'fan2_input': '1770'}.items():
            (self.chip / name).write_text(value)
        (self.root / 'hwmon10').symlink_to(self.chip)
        self.cpu = self.base / 'sys/devices/platform/coretemp.0/hwmon/hwmon2'
        self.cpu.mkdir(parents=True)
        (self.cpu / 'name').write_text('coretemp')
        (self.cpu / 'temp1_input').write_text('43000')
        (self.root / 'hwmon2').symlink_to(self.cpu)
        self.hardware = TrackingHardware(self.root)
        self.controller = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.cid = self.hardware.scan()['pwm_channels'][0]['id']

    def tearDown(self):
        self.controller.shutdown()
        self.tmp.cleanup()

    def group(self, number=0):
        return self.controller.config['fan_groups'][number]

    def assign(self, number=0, cid=None, **changes):
        groups = copy.deepcopy(self.controller.config['fan_groups'])
        cid = cid or self.hardware.scan()['pwm_channels'][number]['id']
        groups[number].update({'pwm_ids': [cid], 'verified_pwm_ids': [cid], **changes})
        self.controller.update_config({'fan_groups': groups})
        return groups[number]['id']

    def test_scan_seeds_two_stable_fans_without_pwm_assumptions_or_writes(self):
        groups = self.controller.config['fan_groups']
        self.assertEqual(len(groups), 2)
        self.assertEqual([group['name'] for group in groups], ['FAN1', 'FAN2'])
        self.assertTrue(all(group['rpm_verified'] and not group['pwm_ids'] for group in groups))
        groups[0]['name'] = 'CPU FAN'
        self.controller.update_config({'fan_groups': groups})
        with patch('controller.atomic_json') as writer:
            self.controller.sample()
            self.controller.sample()
            writer.assert_not_called()
        restarted = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.assertEqual(restarted.config['fan_groups'], self.controller.config['fan_groups'])

    def test_deleting_detected_fan_suppresses_it_across_restart(self):
        groups = copy.deepcopy(self.controller.config['fan_groups'])
        deleted = groups.pop(0)
        self.controller.update_config({'fan_groups': groups,
                                       'ignored_rpm_ids': [deleted['rpm_id']]})
        self.assertEqual(len(self.controller.config['fan_groups']), 1)
        restarted = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.assertEqual(len(restarted.config['fan_groups']), 1)
        self.assertEqual(restarted.config['ignored_rpm_ids'], [deleted['rpm_id']])
        self.assertEqual(self.hardware.writes, [])
        restarted.shutdown()

    def test_manual_defaults_to_50_and_release_restores_exact_state_clears_intent(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'manual'})
        self.assertEqual(self.hardware.writes[:2], [(self.cid, None, 1), (self.cid, 128, None)])
        self.assertEqual(self.controller.status()['fan_groups'][0]['saved_percent'], 50)
        self.controller.release_fan(gid)
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.assertEqual((self.chip / 'pwm2').read_text(), '81')
        self.assertEqual(self.controller.desired_modes, {})

    def test_invalid_speed_paths_and_unverified_group_never_write(self):
        gid = self.assign()
        for speed in (0, 24, 101, float('nan'), True, '50'):
            with self.assertRaises((ValueError, HardwareError)):
                self.controller.control({'id': gid, 'mode': 'manual', 'percent': speed})
        groups = copy.deepcopy(self.controller.config['fan_groups'])
        groups[0]['verified_pwm_ids'] = []
        self.controller.update_config({'fan_groups': groups})
        with self.assertRaises(ValueError):
            self.controller.control({'id': gid, 'mode': 'full'})
        with self.assertRaises(HardwareError):
            self.hardware.set_percent('/etc/passwd', 100)
        self.assertEqual(self.hardware.writes, [])

    def test_runtime_sensor_and_rpm_failures_use_50_percent_only_for_owned_outputs(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 25})
        (self.cpu / 'temp1_input').write_text('invalid')
        self.controller.sample()
        self.controller.apply_controls()
        self.assertEqual((self.chip / 'pwm1').read_text(), '128')
        self.assertEqual(self.controller.status()['fan_groups'][0]['effective_mode'], 'failsafe')
        (self.cpu / 'temp1_input').write_text('43000')
        (self.chip / 'fan1_input').write_text('0')
        self.controller.modes[self.cid]['acquired_at'] = time.monotonic() - 7
        for _ in range(2):
            self.controller.sample()
            self.controller.apply_controls()
        self.assertTrue(self.controller.modes[self.cid]['rpm_fault'])
        self.assertEqual((self.chip / 'pwm1').read_text(), '128')
        self.assertEqual((self.chip / 'pwm2').read_text(), '81')

    def test_hot_temperature_is_advisory_in_manual_mode(self):
        gid = self.assign()
        (self.cpu / 'temp1_input').write_text('90000')
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 25})
        self.assertEqual((self.chip / 'pwm1').read_text(), '64')
        self.assertIn('cpu_hot', [alarm['code'] for alarm in self.controller.alarms])

    def test_custom_group_curve_and_source_are_independent_of_global(self):
        gid = self.assign(curve_mode='custom', temperature_source='cpu',
                          curve=[{'temp': 0, 'percent': 35}, {'temp': 70, 'percent': 100}])
        self.controller.update_config({'curve': [{'temp': 0, 'percent': 80}, {'temp': 70, 'percent': 100}],
                                       'temperature_source': 'disk'})
        self.controller.control({'id': gid, 'mode': 'auto'})
        expected = round((35 + 43 / 70 * 65) * 255 / 100)
        self.assertEqual(int((self.chip / 'pwm1').read_text()), expected)
        self.assertEqual(self.controller.status()['fan_groups'][0]['source_temp'], 43)
        groups = copy.deepcopy(self.controller.config['fan_groups'])
        groups[0]['curve_mode'] = 'global'
        self.controller.update_config({'fan_groups': groups})
        self.assertEqual(int((self.chip / 'pwm1').read_text()), 128)
        self.assertEqual(self.controller.status()['fan_groups'][0]['effective_mode'], 'failsafe')

    def test_global_curve_edits_affect_global_group_without_resetting_saved_mode(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'auto'})
        self.controller.update_config({'curve': [{'temp': 0, 'percent': 80}, {'temp': 70, 'percent': 100}]})
        self.assertEqual(self.controller.desired_modes[gid]['mode'], 'auto')
        self.assertGreater(int((self.chip / 'pwm1').read_text()), 200)
        self.assertEqual(self.controller.status()['fan_groups'][0]['mode'], 'auto')

    def test_shutdown_restores_hardware_but_restart_restores_manual_intent(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 61})
        self.controller.shutdown()
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')
        restarted = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.assertEqual(restarted.status()['fan_groups'][0]['mode'], 'manual')
        self.assertEqual(restarted.status()['fan_groups'][0]['saved_percent'], 61)
        self.assertEqual((self.chip / 'pwm1').read_text(), str(round(61 * 255 / 100)))
        self.assertEqual(restarted.owned[self.cid], {'pwm': 70, 'enable': 2})
        restarted.release()
        restarted.shutdown()

    def test_crash_recovery_restores_exact_snapshot_before_resuming_saved_mode(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'full'})
        before = len(self.hardware.writes)
        restarted = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.assertEqual(self.hardware.writes[before:before + 3],
                         [(self.cid, None, 1), (self.cid, 70, None), (self.cid, None, 2)])
        self.assertEqual(restarted.status()['fan_groups'][0]['mode'], 'full')
        self.assertEqual(restarted.owned[self.cid], {'pwm': 70, 'enable': 2})
        restarted.release()
        restarted.shutdown()
        self.controller.modes.clear()
        self.controller.owned.clear()

    def test_restart_bad_sensor_stops_only_affected_group_and_clears_its_intent(self):
        first = self.assign()
        second = self.assign(1)
        self.controller.control({'id': first, 'mode': 'manual', 'percent': 61})
        self.controller.control({'id': second, 'mode': 'full'})
        self.controller.shutdown()
        (self.chip / 'fan1_input').write_text('0')
        restarted = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        statuses = {group['id']: group for group in restarted.status()['fan_groups']}
        self.assertEqual(statuses[first]['mode'], 'monitor')
        self.assertTrue(statuses[first]['startup_error'])
        self.assertNotIn(first, restarted.desired_modes)
        self.assertEqual(statuses[second]['mode'], 'full')
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        restarted.release()
        restarted.shutdown()

    def test_corrupt_journal_blocks_test_and_takeover_without_hardware_writes(self):
        gid = self.assign()
        (self.base / 'var').mkdir(exist_ok=True)
        (self.base / 'var/owned-channels.json').write_text('{broken')
        restarted = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.assertTrue(restarted.recovery_blocked)
        with self.assertRaises(ValueError):
            restarted.control({'id': gid, 'mode': 'full'})
        with self.assertRaises(ValueError):
            restarted.pwm_test_control({'id': self.cid, 'action': 'start'})
        self.assertEqual(self.hardware.writes, [])
        restarted.shutdown()

    def test_unverified_unassigned_pwm_test_runs_full_even_without_temperature(self):
        (self.cpu / 'temp1_input').write_text('invalid')
        status = self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        self.assertEqual(status['pwm_test']['id'], self.cid)
        self.assertEqual(status['pwm_test']['remaining_seconds'], 10)
        self.assertEqual(status['pending_recovery_ids'], [])
        self.assertEqual((self.chip / 'pwm1').read_text(), '255')
        self.assertEqual(self.controller.desired_modes, {})
        record = json.loads(self.controller.journal.read_text())
        self.assertEqual(record['channels'][self.cid], {'pwm': 70, 'enable': 2})
        (self.chip / 'fan1_input').write_text('1600')
        status = self.controller.pwm_test_control({'id': self.cid, 'action': 'stop'})
        result = status['pwm_test_result']
        fid = self.group()['rpm_id']
        self.assertEqual(result['baseline_rpms'][fid], 1250)
        self.assertEqual(result['final_rpms'][fid], 1600)
        self.assertTrue(result['ok'])
        self.assertIsNone(status['pwm_test'])
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')

    def test_pwm_test_timer_restores_at_ten_seconds_without_polling_control_loop(self):
        self.controller.update_config({'poll_interval': 30})
        ended = threading.Event()
        original = self.controller.finish_pwm_test
        def finished(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            finally:
                ended.set()
        started = time.monotonic()
        with patch.object(self.controller, 'finish_pwm_test', side_effect=finished):
            self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
            self.assertTrue(ended.wait(10.8), 'Independent server timer must restore before 30-second loop poll')
        elapsed = time.monotonic() - started
        self.assertGreaterEqual(elapsed, 9.8)
        self.assertLess(elapsed, 10.8)
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.assertEqual(self.controller.pwm_test_result['reason'], 'timeout')
        self.assertFalse(self.controller.owned)

    def test_test_blocks_only_its_pwm_while_unrelated_group_remains_usable(self):
        first = self.assign()
        second = self.assign(1)
        self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        with self.assertRaises(ValueError):
            self.controller.control({'id': first, 'mode': 'full'})
        self.controller.control({'id': second, 'mode': 'manual', 'percent': 60})
        self.assertEqual((self.chip / 'pwm2').read_text(), '153')
        with self.assertRaises(ValueError):
            self.controller.pwm_test_control({'id': self.hardware.scan()['pwm_channels'][1]['id'], 'action': 'start'})
        groups = copy.deepcopy(self.controller.config['fan_groups'])
        groups[0]['pwm_ids'] = []
        groups[0]['verified_pwm_ids'] = []
        with self.assertRaises(ValueError):
            self.controller.update_config({'fan_groups': groups})
        self.controller.pwm_test_control({'id': self.cid, 'action': 'stop'})
        self.assertEqual(self.controller.status()['fan_groups'][1]['mode'], 'manual')

    def test_pwm_restore_failure_is_pending_and_does_not_block_unrelated_group(self):
        gid = self.assign(1)
        self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        original = self.hardware.restore
        def restore(cid, snapshot):
            if cid == self.cid:
                raise HardwareError('Invalid argument')
            return original(cid, snapshot)
        with patch.object(self.hardware, 'restore', side_effect=restore):
            with self.assertRaises(HardwareError):
                self.controller.pwm_test_control({'id': self.cid, 'action': 'stop'})
            status = self.controller.status()
            self.assertEqual(status['pending_recovery_ids'], [self.cid])
            self.assertFalse(status['recovery_blocked'])
            self.assertFalse(status['pwm_test_result']['ok'])
            self.assertIn('Invalid argument', status['pwm_test_result']['error'])
            self.controller.control({'id': gid, 'mode': 'manual', 'percent': 50})
            with self.assertRaises(ValueError):
                self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        self.controller.release()
        self.assertFalse(self.controller.owned)

    def test_pending_pwm_retry_leaves_other_fan_owned_and_saved(self):
        gid = self.assign(1)
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 67})
        self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        with patch.object(self.hardware, 'restore', side_effect=HardwareError('Invalid argument')):
            with self.assertRaises(HardwareError):
                self.controller.pwm_test_control({'id': self.cid, 'action': 'stop'})
        status = self.controller.release_pending(self.cid)
        self.assertEqual(status['pending_recovery_ids'], [])
        self.assertEqual(self.controller.desired_modes[gid], {'mode': 'manual', 'percent': 67})
        self.assertEqual(status['fan_groups'][1]['mode'], 'manual')
        self.assertEqual((self.chip / 'pwm2').read_text(), '171')
        with self.assertRaises(ValueError):
            self.controller.release_pending(self.hardware.scan()['pwm_channels'][1]['id'])
        with self.assertRaises(ValueError):
            self.controller.release_pending(self.cid)

    def test_switching_to_auto_full_preserves_last_manual_percent_across_restart(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 67})
        self.controller.control({'id': gid, 'mode': 'auto'})
        self.controller.control({'id': gid, 'mode': 'full'})
        self.assertEqual(self.controller.status()['fan_groups'][0]['saved_percent'], 67)
        self.controller.shutdown()
        restarted = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.assertEqual(restarted.status()['fan_groups'][0]['mode'], 'full')
        self.assertEqual(restarted.status()['fan_groups'][0]['saved_percent'], 67)
        restarted.control({'id': gid, 'mode': 'manual'})
        self.assertEqual((self.chip / 'pwm1').read_text(), '171')
        restarted.release()
        restarted.shutdown()

    def test_test_crash_recovery_never_saves_or_resumes_test_as_fan_mode(self):
        self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        self.controller._test_timer.cancel()
        restarted = Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.assertFalse(restarted.owned)
        self.assertIsNone(restarted.status()['pwm_test'])
        self.assertEqual(restarted.desired_modes, {})
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')
        restarted.shutdown()
        self.controller.pwm_test = None
        self.controller.owned.clear()

    def test_old_timer_callback_cannot_end_a_new_test(self):
        self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        old_test = self.controller.pwm_test
        self.controller.pwm_test_control({'id': self.cid, 'action': 'stop'})
        self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        new_test = self.controller.pwm_test
        self.controller._test_timeout(old_test)
        self.assertIs(self.controller.pwm_test, new_test)
        self.assertEqual((self.chip / 'pwm1').read_text(), '255')
        self.controller.pwm_test_control({'id': self.cid, 'action': 'stop'})

    def test_test_final_rpm_scan_failure_cannot_skip_exact_restoration(self):
        self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        original = self.hardware.scan
        called = [False]
        def scan():
            if not called[0]:
                called[0] = True
                raise RuntimeError('RPM scanner unavailable')
            return original()
        with patch.object(self.hardware, 'scan', side_effect=scan):
            status = self.controller.pwm_test_control({'id': self.cid, 'action': 'stop'})
        self.assertIsNone(status['pwm_test'])
        self.assertFalse(status['pwm_test_result']['ok'])
        self.assertIn('RPM scanner unavailable', status['pwm_test_result']['error'])
        self.assertFalse(self.controller.owned)
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')

    def test_shutdown_sample_failure_after_test_does_not_skip_other_fan_restoration(self):
        gid = self.assign(1)
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 60})
        self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        with patch.object(self.controller, 'sample', side_effect=RuntimeError('sampling unavailable')):
            self.controller.shutdown()
        self.assertFalse(self.controller.owned)
        self.assertIsNone(self.controller.pwm_test)
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.assertEqual((self.chip / 'pwm2').read_text(), '81')
        self.assertEqual((self.chip / 'pwm2_enable').read_text(), '1')

    def test_journal_save_failure_prevents_any_test_hardware_write(self):
        with patch.object(self.controller, 'persist_owned', side_effect=OSError('fsync failure')):
            with self.assertRaises(OSError):
                self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        self.assertEqual(self.hardware.writes, [])
        self.assertFalse(self.controller.owned)
        self.assertIsNone(self.controller.pwm_test)

    def test_test_write_failure_rolls_back_and_records_failure(self):
        with patch.object(self.hardware, 'set_percent', side_effect=HardwareError('readback mismatch')):
            with self.assertRaises(HardwareError):
                self.controller.pwm_test_control({'id': self.cid, 'action': 'start'})
        self.assertFalse(self.controller.owned)
        self.assertIsNone(self.controller.pwm_test)
        self.assertFalse(self.controller.pwm_test_result['ok'])
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')

    def test_failed_release_clears_intent_but_keeps_pending_ownership(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'full'})
        with patch.object(self.hardware, 'restore', side_effect=HardwareError('Invalid argument')):
            with self.assertRaises(HardwareError):
                self.controller.release_fan(gid)
        self.assertNotIn(gid, self.controller.desired_modes)
        self.assertIn(self.cid, self.controller.pending_ids())
        self.assertFalse(self.controller.recovery_blocked)
        self.controller.release()

    def test_intent_save_failure_during_release_still_restores_hardware(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 60})
        original = controller_module.atomic_json
        def save(path, value):
            if Path(path) == self.controller.desired_path:
                raise OSError('disk full')
            return original(path, value)
        with patch('controller.atomic_json', side_effect=save):
            with self.assertRaises(OSError):
                self.controller.release_fan(gid)
        self.assertFalse(self.controller.modes)
        self.assertFalse(self.controller.owned)
        self.assertNotIn(gid, self.controller.desired_modes)
        self.assertTrue(self.controller._desired_dirty)
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.controller.release()
        self.assertFalse(self.controller._desired_dirty)
        self.assertEqual(json.loads(self.controller.desired_path.read_text())['groups'], {})

    def test_runtime_write_failure_restores_even_when_intent_cannot_be_saved(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 60})
        original = controller_module.atomic_json
        def save(path, value):
            if Path(path) == self.controller.desired_path:
                raise OSError('disk full')
            return original(path, value)
        with patch('controller.atomic_json', side_effect=save), patch.object(self.hardware, 'set_percent', side_effect=HardwareError('unavailable')):
            with self.assertRaises(OSError):
                self.controller.apply_controls()
        self.assertFalse(self.controller.modes)
        self.assertFalse(self.controller.owned)
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.controller.release()

    def test_renaming_fan_does_not_drop_disappeared_temperature_sensor_baseline(self):
        disk = self.base / 'sys/devices/disk/sda/hwmon/hwmon9'
        disk.mkdir(parents=True)
        (disk / 'name').write_text('drivetemp')
        (disk / 'temp1_input').write_text('39000')
        link = self.root / 'hwmon9'
        link.symlink_to(disk)
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'auto'})
        link.unlink()
        self.controller.sample()
        self.controller.apply_controls()
        self.assertEqual((self.chip / 'pwm1').read_text(), '128')
        baseline = set(self.controller.modes[self.cid]['sensor_baseline'])
        groups = copy.deepcopy(self.controller.config['fan_groups'])
        groups[0]['name'] = 'CPU FAN'
        groups[0]['curve'] = [{'temp': 0, 'percent': 35}, {'temp': 70, 'percent': 100}]
        self.controller.update_config({'fan_groups': groups})
        self.assertEqual(self.controller.modes[self.cid]['sensor_baseline'], baseline)
        self.assertTrue(self.controller.status()['fan_groups'][0]['sensor_failed'])
        self.assertEqual((self.chip / 'pwm1').read_text(), '128')
        self.controller.update_config({'temperature_source': 'cpu'})
        self.assertFalse(self.controller.status()['fan_groups'][0]['sensor_failed'])

    def test_constructor_failure_after_takeover_restores_hardware_before_raising(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'full'})
        self.controller.shutdown()
        original = Controller.sample
        active_samples = [0]
        def sample(instance):
            result = original(instance)
            if instance.modes:
                active_samples[0] += 1
            if active_samples[0] >= 2:
                raise RuntimeError('sample failed after takeover')
            return result
        with patch.object(Controller, 'sample', autospec=True, side_effect=sample):
            with self.assertRaises(RuntimeError):
                Controller(self.hardware, self.base / 'etc', self.base / 'var')
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')

    def test_control_sampling_exception_stops_selected_fan_and_restores_exactly(self):
        gid = self.assign()
        original = self.controller.sample
        def sample():
            result = original()
            if self.controller.modes:
                raise RuntimeError('scanner unavailable')
            return result
        with patch.object(self.controller, 'sample', side_effect=sample):
            with self.assertRaises(HardwareError):
                self.controller.control({'id': gid, 'mode': 'full'})
        self.assertFalse(self.controller.modes)
        self.assertFalse(self.controller.owned)
        self.assertNotIn(gid, self.controller.desired_modes)
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')

    def test_server_bind_failure_cleans_up_resumed_hardware(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'full'})
        with patch.object(server_module, 'Controller', return_value=self.controller), \
                patch.object(server_module, 'FanServer', side_effect=OSError('address already in use')), \
                patch.object(sys, 'argv', ['server.py']), \
                patch.dict(os.environ, {'TRIM_PKGETC': str(self.controller.etc), 'TRIM_PKGVAR': str(self.controller.state)}):
            with self.assertRaises(OSError):
                server_module.main()
        self.assertFalse(self.controller.owned)
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')
        self.assertEqual((self.chip / 'pwm1').read_text(), '70')
        self.assertEqual(self.controller.desired_modes[gid]['mode'], 'full')

    def test_runtime_write_failure_stops_group_and_clears_saved_intent(self):
        gid = self.assign()
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 60})
        with patch.object(self.hardware, 'set_percent', side_effect=HardwareError('disconnected')):
            self.controller.apply_controls()
        self.assertNotIn(gid, self.controller.desired_modes)
        self.assertFalse(self.controller.modes)
        self.assertFalse(self.controller.owned)
        self.assertEqual((self.chip / 'pwm1_enable').read_text(), '2')

    def test_hwmon_renumber_preserves_fan_and_pwm_identity(self):
        groups = copy.deepcopy(self.controller.config['fan_groups'])
        (self.root / 'hwmon10').unlink()
        target = self.chip.with_name('hwmon27')
        self.chip.rename(target)
        self.chip = target
        (self.root / 'hwmon27').symlink_to(target)
        self.controller.sample()
        self.assertEqual(self.controller.config['fan_groups'], groups)
        self.assertIn(self.cid, [channel['id'] for channel in self.controller.status()['channels']])

    def test_config_normalizes_old_groups_and_rejects_invalid_custom_curve(self):
        config = copy.deepcopy(DEFAULT_CONFIG)
        group = copy.deepcopy(self.group())
        for field in ('curve_mode', 'temperature_source', 'curve'):
            group.pop(field)
        config['fan_groups'] = [group]
        normalized = validate_config(config)['fan_groups'][0]
        self.assertEqual(normalized['curve_mode'], 'global')
        self.assertEqual(normalized['curve'], config['curve'])
        group['curve'] = [{'temp': 0, 'percent': 0}, {'temp': 70, 'percent': 100}]
        with self.assertRaises(ValueError):
            validate_config(config)
        with self.assertRaises(ValueError):
            self.controller.update_config({'arbitrary_path': '/etc/passwd'})
        self.assertEqual(self.hardware.writes, [])


class AuthInitCLITests(unittest.TestCase):
    def test_init_stdin_is_hardware_free_and_preserves_existing_auth(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            env = dict(os.environ, TRIM_PKGETC=str(base / 'etc'), TRIM_PKGVAR=str(base / 'var'), FAN_HWMON_ROOT=str(base / 'missing-sysfs'))
            server = str(Path(__file__).resolve().parents[1] / 'src/app/bin/server.py')
            password = '  safe-password-1234  '
            result = subprocess.run([sys.executable, server, '--init-auth-stdin'], input=password, text=True, env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(password, result.stdout + result.stderr)
            auth = Auth(base / 'etc/auth.json')
            self.assertTrue(auth.verify(password))
            original = auth.path.read_text()
            result = subprocess.run([sys.executable, server, '--init-auth-stdin'], input='another-password', text=True, env=env, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(auth.path.read_text(), original)
            self.assertFalse((base / 'var').exists())


class AuthHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        static = base / 'static'
        static.mkdir()
        (static / 'index.html').write_text('<html>Fan Studio</html>')
        self.controller = Controller(Hardware(demo=True), base / 'etc', base / 'var')
        self.auth = Auth(base / 'etc/auth.json')
        self.server = FanServer(('127.0.0.1', 0), self.controller, self.auth, static)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        self.cookie = None
        self.csrf = None

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.controller.shutdown()
        self.tmp.cleanup()

    def request(self, method, path, body=None, csrf=True, origin=True, host=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        headers = {'Host': host or '127.0.0.1:' + str(self.port)}
        if origin:
            headers['Origin'] = 'http://127.0.0.1:' + str(self.port)
        if self.cookie:
            headers['Cookie'] = self.cookie
        if csrf and self.csrf:
            headers['X-CSRF-Token'] = self.csrf
        if body is not None:
            headers['Content-Type'] = 'application/json'
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse()
        data = response.read()
        cookie = response.getheader('Set-Cookie')
        if cookie:
            self.cookie = cookie.split(';')[0]
        code = response.status
        conn.close()
        return code, json.loads(data) if data.startswith(b'{') else data, cookie

    def setup_admin(self):
        code, body, cookie = self.request('POST', '/api/setup', {'password': 'safe-password-1234'})
        self.assertEqual(code, 200)
        self.csrf = body['csrf_token']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)

    def configured_group(self):
        groups = copy.deepcopy(self.controller.config['fan_groups'])
        cid = self.controller.status()['channels'][0]['id']
        groups[0].update({'pwm_ids': [cid], 'verified_pwm_ids': [cid]})
        self.controller.update_config({'fan_groups': groups})
        return groups[0]['id']

    def test_pwm_test_endpoint_obeys_auth_csrf_and_hardware_errors(self):
        cid = self.controller.status()['channels'][0]['id']
        body = {'id': cid, 'action': 'start'}
        self.assertEqual(self.request('POST', '/api/pwm-test', body)[0], 401)
        self.setup_admin()
        self.assertEqual(self.request('POST', '/api/pwm-test', body, csrf=False)[0], 403)
        code, status, _ = self.request('POST', '/api/pwm-test', body)
        self.assertEqual(code, 200)
        self.assertEqual(status['pwm_test']['id'], cid)
        with patch.object(self.controller.hardware, 'restore', side_effect=HardwareError('Invalid argument')):
            code, result, _ = self.request('POST', '/api/pwm-test', {'id': cid, 'action': 'stop'})
        self.assertEqual(code, 409)
        self.assertEqual(result['code'], 'hardware_error')
        self.assertEqual(self.controller.status()['pending_recovery_ids'], [cid])
        self.assertEqual(self.request('POST', '/api/release', {'pwm_id': cid})[0], 200)
        self.assertEqual(self.request('POST', '/api/release', {'pwm_id': cid})[0], 400)
        self.assertEqual(self.request('POST', '/api/release', {'pwm_id': cid, 'id': 'group'})[0], 400)

    def test_auth_setup_login_csrf_and_logout(self):
        self.assertEqual(self.request('GET', '/api/status')[0], 401)
        self.assertTrue(self.request('GET', '/api/auth/status')[1]['setup_required'])
        self.setup_admin()
        self.assertEqual(self.request('POST', '/api/setup', {'password': 'another-password'})[0], 400)
        self.assertEqual(self.request('GET', '/api/status')[0], 200)
        cid = self.configured_group()
        self.assertEqual(self.request('POST', '/api/control', {'id': cid, 'mode': 'full'}, csrf=False)[0], 403)
        self.assertEqual(self.request('POST', '/api/control', {'id': cid, 'mode': 'full'}, origin=False)[0], 403)
        self.assertEqual(self.request('POST', '/api/control', {'id': cid, 'mode': 'full'})[0], 200)
        self.assertEqual(self.request('POST', '/api/logout', {})[0], 200)
        self.assertEqual(self.request('GET', '/api/status')[0], 401)
        self.assertEqual(self.request('POST', '/api/login', {'password': 'wrong-password'})[0], 401)
        code, result, _ = self.request('POST', '/api/login', {'password': 'safe-password-1234'})
        self.assertEqual(code, 200)
        self.assertIn('csrf_token', result)
        self.assertEqual(self.auth.path.stat().st_mode & 0o777, 0o600)
        saved = json.loads(self.auth.path.read_text())
        self.assertNotIn('password', saved)

    def test_origin_host_and_traversal_rejected(self):
        self.assertEqual(self.request('POST', '/api/setup', {'password': 'safe-password-1234'}, origin=False)[0], 403)
        self.assertEqual(self.request('GET', '/api/auth/status', host='evil.example')[0], 403)
        self.assertEqual(self.request('GET', '/%2e%2e/etc/auth.json')[0], 404)
        self.setup_admin()
        self.assertEqual(self.request('POST', '/api/unknown', {})[0], 404)
        self.assertEqual(self.request('POST', '/api/control', {'id': 'demo-controller:pwm1', 'mode': 'manual', 'percent': 5})[0], 400)

    def test_demo_saved_manual_mode_resumes_after_controller_restart(self):
        gid = self.configured_group()
        self.controller.control({'id': gid, 'mode': 'manual', 'percent': 67})
        self.controller.shutdown()
        restarted = Controller(self.controller.hardware, self.controller.etc, self.controller.state)
        status = next(group for group in restarted.status()['fan_groups'] if group['id'] == gid)
        self.assertEqual(status['mode'], 'manual')
        self.assertEqual(status['saved_percent'], 67)
        self.assertFalse(restarted.journal.exists())
        restarted.release()
        restarted.shutdown()

    def test_rate_limit_and_demo_no_hardware_journal(self):
        for _ in range(8):
            self.request('POST', '/api/login', {'password': 'wrong-password'})
        self.assertEqual(self.request('POST', '/api/login', {'password': 'wrong-password'})[0], 429)
        cid = self.configured_group()
        self.controller.control({'id': cid, 'mode': 'full'})
        self.assertFalse(self.controller.journal.exists())


if __name__ == '__main__':
    unittest.main()
