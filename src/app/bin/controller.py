"""Conservative control loop with durable ownership and exact-state recovery."""
import copy
import hashlib
import json
import logging
import math
import os
import threading
import time
from collections import deque
from pathlib import Path
from hardware import HardwareError

DEFAULT_CONFIG = {
    'temperature_source': 'max',
    'curve': [{'temp': 30, 'percent': 35}, {'temp': 40, 'percent': 45},
              {'temp': 50, 'percent': 55}, {'temp': 60, 'percent': 70},
              {'temp': 70, 'percent': 80}, {'temp': 82, 'percent': 90}, {'temp': 95, 'percent': 100}],
    'poll_interval': 3,
    'fan_groups': [],
    'ignored_rpm_ids': [],
    'ignored_temperature_sensor_ids': [],
    'ignored_pwm_ids': [],
    'legacy_pwm_candidates': [],
}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name('.' + path.name + '.' + str(os.getpid()) + '.tmp')
    with open(temporary, 'w', encoding='utf-8') as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load_json(path, fallback):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return copy.deepcopy(fallback)


def valid_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def migrate_config(value):
    """Archive old PWM/RPM associations without turning them into physical FAN groups."""
    if not isinstance(value, dict):
        return value, False
    value = copy.deepcopy(value)
    existing_candidates = value.get('legacy_pwm_candidates', [])
    if not isinstance(existing_candidates, list):
        raise ValueError('历史 PWM 关联记录无效')
    candidates = copy.deepcopy(existing_candidates)
    migrated = False
    if 'channels' in value:
        legacy = value.pop('channels')
        if not isinstance(legacy, dict):
            raise ValueError('旧版 PWM 关联配置无效')
        for pwm_id, mapping in legacy.items():
            if (not isinstance(pwm_id, str) or len(pwm_id) > 128 or not isinstance(mapping, dict)
                    or set(mapping) != {'fan_id'}):
                raise ValueError('旧版 PWM 关联配置无效')
            rpm_id = mapping['fan_id']
            if rpm_id is not None and (not isinstance(rpm_id, str) or len(rpm_id) > 128):
                raise ValueError('旧版 RPM 关联配置无效')
            candidates.append({'pwm_id': pwm_id, 'rpm_id': rpm_id, 'former_group': '旧版 PWM 关联'})
        migrated = True

    groups = value.get('fan_groups', [])
    if isinstance(groups, list):
        active_groups = []
        for group in groups:
            generated_placeholder = (isinstance(group, dict) and isinstance(group.get('id'), str)
                                     and group['id'].startswith('legacy-')
                                     and isinstance(group.get('name'), str)
                                     and group['name'].startswith('待确认风扇 ')
                                     and not group.get('verified_pwm_ids') and not group.get('rpm_verified'))
            if generated_placeholder:
                if (not isinstance(group.get('name'), str) or not group['name'].strip() or len(group['name']) > 64
                        or not isinstance(group.get('pwm_ids'), list)
                        or any(not isinstance(pwm_id, str) for pwm_id in group['pwm_ids'])):
                    raise ValueError('旧版待确认 FAN 关联配置无效')
                rpm_id = group.get('rpm_id')
                if rpm_id is not None and (not isinstance(rpm_id, str) or len(rpm_id) > 128):
                    raise ValueError('旧版 RPM 关联配置无效')
                candidates.extend({'pwm_id': pwm_id, 'rpm_id': rpm_id, 'former_group': group['name']}
                                  for pwm_id in group['pwm_ids'])
                migrated = True
            else:
                active_groups.append(group)
        if migrated:
            value['fan_groups'] = active_groups

    if migrated:
        # Keep one readable, non-operational reference per PWM. It never reserves an output.
        unique = {}
        for candidate in candidates:
            if not isinstance(candidate, dict) or not isinstance(candidate.get('pwm_id'), str):
                raise ValueError('历史 PWM 关联记录无效')
            unique.setdefault(candidate['pwm_id'], candidate)
        value['legacy_pwm_candidates'] = list(unique.values())
    return value, migrated


def detach_ignored_pwm(value):
    """Keep ignored outputs visible, but remove them from every FAN route."""
    if not isinstance(value, dict) or not isinstance(value.get('ignored_pwm_ids', []), list):
        return value
    if any(not isinstance(cid, str) for cid in value.get('ignored_pwm_ids', [])):
        return value
    ignored = set(value.get('ignored_pwm_ids', []))
    groups = value.get('fan_groups')
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            if isinstance(group.get('pwm_ids'), list):
                group['pwm_ids'] = [cid for cid in group['pwm_ids'] if not isinstance(cid, str) or cid not in ignored]
            if isinstance(group.get('verified_pwm_ids'), list):
                group['verified_pwm_ids'] = [cid for cid in group['verified_pwm_ids']
                                             if not isinstance(cid, str) or cid not in ignored]
    return value


def validate_curve(curve):
    if not isinstance(curve, list) or not 2 <= len(curve) <= 12:
        raise ValueError('曲线需要 2 至 12 个点')
    last_temp, last_percent = -100, 0
    for point in curve:
        if not isinstance(point, dict) or set(point) != {'temp', 'percent'}:
            raise ValueError('曲线点需要 temp 和 percent')
        temp, percent = point['temp'], point['percent']
        if not valid_number(temp) or not 0 <= temp <= 100 or temp <= last_temp:
            raise ValueError('曲线温度必须递增且在 0 至 100°C 之间')
        if not valid_number(percent) or not 35 <= percent <= 100 or percent < last_percent:
            raise ValueError('自动曲线转速必须递增且至少为 35%')
        last_temp, last_percent = temp, percent
    return copy.deepcopy(curve)


def validate_config(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULT_CONFIG):
        raise ValueError('配置包含未知字段')
    merged = copy.deepcopy(DEFAULT_CONFIG)
    merged.update(copy.deepcopy(value))
    if merged['temperature_source'] not in ('cpu', 'disk', 'max'):
        raise ValueError('温度来源应为 cpu、disk 或 max')
    interval = merged['poll_interval']
    if not valid_number(interval) or not 1 <= interval <= 30:
        raise ValueError('刷新间隔应为 1 至 30 秒')
    merged['curve'] = validate_curve(merged['curve'])
    groups = merged['fan_groups']
    if not isinstance(groups, list) or len(groups) > 32:
        raise ValueError('FAN 分组最多 32 个')
    group_ids, assigned_pwm, assigned_rpm = set(), set(), set()
    for group in groups:
        fields = {'id', 'name', 'pwm_ids', 'verified_pwm_ids', 'rpm_id', 'rpm_verified'}
        optional = {'curve_mode', 'temperature_source', 'curve', 'ignored_temperature_sensor_ids'}
        if not isinstance(group, dict) or not fields.issubset(group) or set(group) - fields - optional:
            raise ValueError('FAN 分组字段无效')
        group.setdefault('curve_mode', 'global')
        group.setdefault('temperature_source', merged['temperature_source'])
        group.setdefault('curve', copy.deepcopy(merged['curve']))
        group.setdefault('ignored_temperature_sensor_ids', [])
        if group['curve_mode'] not in ('global', 'custom'):
            raise ValueError('FAN 曲线模式应为 global 或 custom')
        if group['temperature_source'] not in ('cpu', 'disk', 'max'):
            raise ValueError('FAN 温度来源应为 cpu、disk 或 max')
        ignored_sensors = group['ignored_temperature_sensor_ids']
        if (not isinstance(ignored_sensors, list) or len(ignored_sensors) > 256
                or any(not isinstance(sensor_id, str) or not 1 <= len(sensor_id) <= 128 for sensor_id in ignored_sensors)
                or len(set(ignored_sensors)) != len(ignored_sensors)):
            raise ValueError('FAN 温度来源忽略列表无效')
        group['curve'] = validate_curve(group['curve'])
        group['name'] = group['name'].strip() if isinstance(group.get('name'), str) else group.get('name')
        gid, name = group['id'], group['name']
        if not isinstance(gid, str) or not 1 <= len(gid) <= 128 or gid in group_ids:
            raise ValueError('FAN 分组标识无效或重复')
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 64:
            raise ValueError('FAN 名称需要为 1 至 64 个字符')
        group_ids.add(gid)
        pwm_ids, verified = group['pwm_ids'], group['verified_pwm_ids']
        if (not isinstance(pwm_ids, list) or len(pwm_ids) > 16 or
                any(not isinstance(cid, str) or not 1 <= len(cid) <= 128 for cid in pwm_ids) or
                len(set(pwm_ids)) != len(pwm_ids)):
            raise ValueError('FAN 分组 PWM 输出列表无效')
        if (not isinstance(verified, list) or
                any(not isinstance(cid, str) or not 1 <= len(cid) <= 128 for cid in verified) or
                len(set(verified)) != len(verified) or any(cid not in pwm_ids for cid in verified)):
            raise ValueError('已验证 PWM 必须属于当前 FAN 分组')
        overlap = assigned_pwm.intersection(pwm_ids)
        if overlap:
            raise ValueError('同一个 PWM 输出不能分配到多个 FAN 分组')
        assigned_pwm.update(pwm_ids)
        rpm_id = group['rpm_id']
        if rpm_id is not None:
            if not isinstance(rpm_id, str) or not 1 <= len(rpm_id) <= 128:
                raise ValueError('RPM 输入标识无效')
            if rpm_id in assigned_rpm:
                raise ValueError('同一个 RPM 输入不能分配到多个 FAN 分组')
            assigned_rpm.add(rpm_id)
        if type(group['rpm_verified']) is not bool or (group['rpm_verified'] and rpm_id is None):
            raise ValueError('RPM 验证状态无效')
    ignored_rpm_ids = merged['ignored_rpm_ids']
    if (not isinstance(ignored_rpm_ids, list) or len(ignored_rpm_ids) > 128
            or any(not isinstance(rpm_id, str) or not 1 <= len(rpm_id) <= 128 for rpm_id in ignored_rpm_ids)
            or len(set(ignored_rpm_ids)) != len(ignored_rpm_ids)):
        raise ValueError('已删除的 RPM 输入记录无效')
    for key, label in (('ignored_temperature_sensor_ids', '温度传感器忽略列表'), ('ignored_pwm_ids', 'PWM 忽略列表')):
        values = merged[key]
        limit = 256 if key == 'ignored_temperature_sensor_ids' else 128
        if (not isinstance(values, list) or len(values) > limit
                or any(not isinstance(value, str) or not 1 <= len(value) <= 128 for value in values)
                or len(set(values)) != len(values)):
            raise ValueError(label + '无效')
    candidates = merged['legacy_pwm_candidates']
    if not isinstance(candidates, list) or len(candidates) > 512:
        raise ValueError('历史 PWM 关联记录无效')
    candidate_ids = set()
    for candidate in candidates:
        if not isinstance(candidate, dict) or set(candidate) != {'pwm_id', 'rpm_id', 'former_group'}:
            raise ValueError('历史 PWM 关联记录字段无效')
        pwm_id, rpm_id, former_group = candidate['pwm_id'], candidate['rpm_id'], candidate['former_group']
        if not isinstance(pwm_id, str) or not 1 <= len(pwm_id) <= 128 or pwm_id in candidate_ids:
            raise ValueError('历史 PWM 关联标识无效或重复')
        if rpm_id is not None and (not isinstance(rpm_id, str) or not 1 <= len(rpm_id) <= 128):
            raise ValueError('历史 RPM 关联标识无效')
        if former_group is not None and (not isinstance(former_group, str) or len(former_group) > 64):
            raise ValueError('历史 FAN 名称无效')
        candidate_ids.add(pwm_id)
    return merged


class Controller:
    def __init__(self, hardware, etc, state):
        self.hardware = hardware
        self.etc, self.state = Path(etc), Path(state)
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.history = deque(maxlen=2400)
        self.logs = deque(maxlen=250)
        self.owned = {}
        self.modes = {}
        self.alarms = []
        self.known_temp_sensors = {}
        self.sensor_baseline = set()
        self.shutdown_started = False
        self.recovery_blocked = False
        self.journal_corrupt = False
        self.journal = self.state / 'owned-channels.json'
        self.desired_path = self.state / 'desired-fans.json'
        self.desired_modes = {}
        self._desired_dirty = False
        self.startup_errors = {}
        self.pwm_test = None
        self.pwm_test_result = None
        self._test_timer = None
        try:
            raw_config = load_json(self.etc / 'config.json', DEFAULT_CONFIG)
            raw_config, migrated = migrate_config(raw_config)
            raw_config = detach_ignored_pwm(raw_config)
            self.config = validate_config(raw_config)
            if migrated:
                atomic_json(self.etc / 'config.json', self.config)
                self.log('info', '旧版 PWM/RPM 关联已存档为历史参考；未创建实体 FAN 组，也未自动接管')
        except (ValueError, OSError) as exc:
            self.config = copy.deepcopy(DEFAULT_CONFIG)
            self.log('error', '配置损坏，已使用安全默认配置：' + str(exc))
        self.hardware.set_ignored_pwm_ids(self.config['ignored_pwm_ids'])
        self.load_desired()
        self.recover()
        self.sample()
        try:
            self.resume_desired()
        except BaseException:
            self.shutdown()
            raise

    def log(self, level, message):
        self.logs.append({'time': time.time(), 'level': level, 'message': message})
        getattr(logging, level if level in ('error', 'warning', 'info') else 'info')(message)

    def seed_detected_fans(self):
        represented = {group['rpm_id'] for group in self.config['fan_groups'] if group['rpm_id']}
        ignored = set(self.config.get('ignored_rpm_ids', []))
        groups = copy.deepcopy(self.config['fan_groups'])
        used_ids = {group['id'] for group in groups}
        for index, fan in enumerate(self.hw['fans'], 1):
            if fan['id'] in represented or fan['id'] in ignored or len(groups) >= 32:
                continue
            gid = 'fan-' + hashlib.sha256(fan['id'].encode()).hexdigest()[:20]
            if gid in used_ids:
                continue
            groups.append({'id': gid, 'name': 'FAN' + str(index), 'pwm_ids': [],
                           'verified_pwm_ids': [], 'rpm_id': fan['id'], 'rpm_verified': True,
                           'curve_mode': 'global', 'temperature_source': self.config['temperature_source'],
                           'curve': copy.deepcopy(self.config['curve'])})
            represented.add(fan['id'])
            used_ids.add(gid)
        if groups != self.config['fan_groups']:
            candidate = {**self.config, 'fan_groups': groups}
            atomic_json(self.etc / 'config.json', candidate)
            self.config = candidate
            self.log('info', '已按检测到的 RPM 输入添加 FAN；尚未关联或接管任何 PWM')

    def load_desired(self):
        try:
            record = load_json(self.desired_path, {'version': 1, 'groups': {}})
            if (not isinstance(record, dict) or set(record) != {'version', 'groups'}
                    or record['version'] != 1 or not isinstance(record['groups'], dict)):
                raise ValueError('已保存 FAN 模式记录无效')
            for gid, mode in record['groups'].items():
                if (not isinstance(gid, str) or not 1 <= len(gid) <= 128 or not isinstance(mode, dict)
                        or set(mode) != {'mode', 'percent'} or mode['mode'] not in ('auto', 'manual', 'full')
                        or not valid_number(mode['percent']) or not 25 <= mode['percent'] <= 100):
                    raise ValueError('已保存 FAN 模式记录无效')
            self.desired_modes = record['groups']
        except (ValueError, OSError) as exc:
            self.log('error', '已保存 FAN 模式无法读取；本次启动仅监测：' + str(exc))

    def set_desired(self, group_id, mode):
        candidate = {**self.desired_modes, group_id: dict(mode)}
        atomic_json(self.desired_path, {'version': 1, 'groups': candidate})
        self.desired_modes = candidate
        self._desired_dirty = False

    def clear_desired(self, group_ids):
        remove = set(group_ids)
        candidate = {gid: mode for gid, mode in self.desired_modes.items() if gid not in remove}
        if candidate != self.desired_modes or self._desired_dirty:
            try:
                atomic_json(self.desired_path, {'version': 1, 'groups': candidate})
            except OSError:
                self.desired_modes = candidate
                self._desired_dirty = True
                raise
            self.desired_modes = candidate
            self._desired_dirty = False

    def resume_desired(self):
        for group_id, mode in list(self.desired_modes.items()):
            group = self.group(group_id)
            if group is None or not group['pwm_ids']:
                self.startup_errors[group_id] = '没有可恢复的 PWM 输出；当前保持监测'
                self.clear_desired([group_id])
                self.log('warning', 'FAN 没有可恢复的 PWM 输出，保持监测：' + group_id)
                continue
            try:
                self.control({'id': group_id, **mode}, restoring=True)
                self.log('info', '已恢复 FAN 保存的控制模式：' + group_id)
            except (ValueError, HardwareError, OSError) as exc:
                self.startup_errors[group_id] = str(exc)
                group = self.group(group_id)
                if group:
                    self._release_targets(group['pwm_ids'])
                try:
                    self.clear_desired([group_id])
                except OSError as persist_exc:
                    # Never resume this group in the current process after a failed start.
                    self.desired_modes.pop(group_id, None)
                    self.log('error', '启动失败状态无法保存：' + str(persist_exc))
                self.log('error', 'FAN 启动恢复失败，已停止此组并尝试恢复原始状态：' + group_id + '，' + str(exc))
        self.sample()

    def pending_ids(self):
        testing = {self.pwm_test['id']} if self.pwm_test else set()
        ignored = set(self.config.get('ignored_pwm_ids', []))
        return set(self.owned) - set(self.modes) - testing - ignored

    def test_status(self):
        if not self.pwm_test:
            return None
        return {'id': self.pwm_test['id'], 'started_at': self.pwm_test['started_at'],
                'baseline_rpms': dict(self.pwm_test['baseline_rpms']),
                'remaining_seconds': max(0, math.ceil(self.pwm_test['deadline'] - time.monotonic()))}

    def pwm_test_control(self, body):
        if not isinstance(body, dict) or set(body) != {'id', 'action'}:
            raise ValueError('PWM 测试需要 id 和 action')
        cid, action = body['id'], body['action']
        if not isinstance(cid, str) or action not in ('start', 'stop'):
            raise ValueError('请选择有效 PWM 和测试操作')
        with self.lock:
            if self.shutdown_started:
                raise ValueError('服务正在关闭')
            if action == 'stop':
                if not self.pwm_test or self.pwm_test['id'] != cid:
                    raise ValueError('此 PWM 当前未在测试')
                failures = self.finish_pwm_test('stopped')
                if failures:
                    raise HardwareError('；'.join(failures))
                return self.status()
            if self.journal_corrupt:
                raise ValueError('恢复记录损坏，已暂停 PWM 测试')
            if self.pwm_test:
                raise ValueError('已有 PWM 正在测试，请先结束当前测试')
            if cid in self.owned:
                raise ValueError('此 PWM 正在接管或等待恢复，请先释放或恢复此接口')
            self.sample()
            channel = next((item for item in self.hw['pwm_channels'] if item['id'] == cid), None)
            if not channel or not channel['writable']:
                raise ValueError('PWM 接口不存在或不可写')
            snapshot = self.hardware.snapshot(cid)
            candidate = {**self.owned, cid: snapshot}
            self.persist_owned(candidate)
            self.owned = candidate
            self.pwm_test = {'id': cid, 'started_at': time.time(), 'deadline': time.monotonic() + 10,
                             'baseline_rpms': {fan['id']: fan['rpm'] for fan in self.hw['fans']}}
            self.pwm_test_result = None
            try:
                # Explicit full-speed test bypasses temperature and RPM fallback rules.
                self.hardware.set_percent(cid, 100)
            except (HardwareError, OSError) as exc:
                self.finish_pwm_test('write_failed', str(exc))
                raise HardwareError('PWM 测试写入失败，已尝试恢复原始状态：' + str(exc)) from exc
            self.pwm_test['deadline'] = time.monotonic() + 10
            self._test_timer = threading.Timer(10, self._test_timeout, args=(self.pwm_test,))
            self._test_timer.daemon = True
            self._test_timer.start()
            self.sample()
            self.log('info', '开始 PWM 全速测试，10 秒后自动恢复：' + cid)
            return self.status()

    def _test_timeout(self, expected_test):
        with self.lock:
            if self.pwm_test is expected_test:
                self.finish_pwm_test('timeout')

    def finish_pwm_test(self, reason, write_error=None):
        if not self.pwm_test:
            return []
        test = self.pwm_test
        if self._test_timer:
            self._test_timer.cancel()
            self._test_timer = None
        errors = [write_error] if write_error else []
        final_rpms = {}
        try:
            self.hw = self.hardware.scan()
            final_rpms = {fan['id']: fan['rpm'] for fan in self.hw['fans']}
        except Exception as exc:
            errors.append('测试结束时转速读取失败：' + str(exc))
        # Observing RPM is optional; it must never prevent restoring the saved PWM state.
        try:
            failures = self._release_targets([test['id']])
        finally:
            self.pwm_test = None
        errors.extend(failures)
        try:
            self.sample()
        except Exception as exc:
            errors.append('恢复后设备状态读取失败：' + str(exc))
        self.pwm_test_result = {'id': test['id'], 'ok': not errors, 'error': '；'.join(errors) if errors else None,
                                'baseline_rpms': test['baseline_rpms'], 'final_rpms': final_rpms,
                                'started_at': test['started_at'], 'ended_at': time.time(), 'reason': reason}
        self.log('error' if errors else 'info', 'PWM 测试结束' + ('，仍待恢复：' if failures else '，已恢复测试前状态：') + test['id'])
        return failures

    def persist_owned(self, candidate=None):
        # Demo never records hardware ownership on disk.
        if not self.hardware.demo:
            atomic_json(self.journal, {'version': 1, 'channels': self.owned if candidate is None else candidate})

    def recover(self):
        if self.hardware.demo:
            return
        try:
            record = load_json(self.journal, {'version': 1, 'channels': {}})
            if not isinstance(record, dict) or record.get('version') != 1 or not isinstance(record.get('channels'), dict):
                raise ValueError('无效接管记录')
            for cid, snap in record['channels'].items():
                if (not isinstance(cid, str) or not isinstance(snap, dict) or set(snap) != {'pwm', 'enable'} or
                    type(snap['pwm']) is not int or not 0 <= snap['pwm'] <= 255 or
                    type(snap['enable']) is not int or not 0 <= snap['enable'] <= 5):
                    raise ValueError('无效通道快照')
            self.owned = record['channels']
            for cid in list(self.owned):
                if cid in self.config.get('ignored_pwm_ids', []):
                    continue
                try:
                    self.hardware.restore(cid, self.owned[cid])
                    remaining = dict(self.owned)
                    del remaining[cid]
                    self.persist_owned(remaining)
                    self.owned = remaining
                    self.log('warning', '已从上次意外退出恢复通道：' + cid)
                except (HardwareError, OSError) as exc:
                    self.log('error', '待恢复通道不可用：' + cid + '，' + str(exc))
            self.persist_owned()
        except (ValueError, OSError) as exc:
            self.log('error', '接管记录无法读取；为避免误写，禁止自动接管：' + str(exc))
            self.recovery_blocked = True
            self.journal_corrupt = True
        else:
            self.recovery_blocked = self.journal_corrupt

    def start(self):
        self.thread = threading.Thread(target=self._run, name='fan-control', daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stop_event.wait(self.config['poll_interval']):
            try:
                with self.lock:
                    self.sample()
                    self.apply_controls()
            except BaseException as exc:
                with self.lock:
                    self.log('error', '控制线程异常，正在恢复接管通道：' + str(exc))
                    try:
                        self.release()
                    except (HardwareError, OSError) as recovery_exc:
                        self.log('error', '控制线程恢复未全部完成，请检查恢复记录：' + str(recovery_exc))
                return

    def sample(self):
        self.hw = self.hardware.scan()
        self.seed_detected_fans()
        sensors = self.hw['temperature_sensors']
        self.known_temp_sensors.update({s['id']: {'kind': s['kind'], 'block_devices': tuple(s.get('block_devices', []))}
                                        for s in sensors})
        ignored = set(self.config.get('ignored_temperature_sensor_ids', []))
        cpu = [s for s in sensors if s['kind'] == 'cpu' and s['temperature'] is not None]
        disk = [s for s in sensors if s['kind'] == 'disk' and s['temperature'] is not None]
        raw_cpu_temp = max((s['temperature'] for s in cpu), default=None)
        raw_disk_temp = max((s['temperature'] for s in disk), default=None)
        cpu_temp = max((s['temperature'] for s in cpu if s['id'] not in ignored), default=None)
        disk_temp = max((s['temperature'] for s in disk if s['id'] not in ignored), default=None)
        valid = [n for n in (cpu_temp, disk_temp) if n is not None]
        max_temp = max(valid, default=None)
        source = self.config['temperature_source']
        source_temp, sensor_failed, missing_sensors = self.temperature_state(source, self.sensor_baseline, ignored)
        required = ('cpu', 'disk') if source == 'max' else (source,)
        if self.modes:
            self.sensor_baseline.update(s['id'] for s in sensors if s['kind'] in required and s['id'] not in ignored)
        for mode in self.modes.values():
            group = self.group(mode.get('group_id'))
            settings = self.curve_settings(group)
            selected = settings['temperature_source']
            excluded = set(settings.get('ignored_temperature_sensor_ids', []))
            kinds = ('cpu', 'disk') if selected == 'max' else (selected,)
            mode.setdefault('sensor_baseline', set()).update(
                s['id'] for s in sensors if s['kind'] in kinds and s['id'] not in excluded)
        self.system = {'cpu_temp': cpu_temp, 'disk_temp': disk_temp, 'max_temp': max_temp,
                       'raw_cpu_temp': raw_cpu_temp, 'raw_disk_temp': raw_disk_temp,
                       'source_temp': source_temp, 'temperature_source': source,
                       'sensor_failed': sensor_failed or source_temp is None, 'missing_sensor_ids': missing_sensors}
        alarms = []
        if self.journal_corrupt:
            alarms.append({'code': 'recovery_record_invalid', 'level': 'critical', 'message': '恢复记录损坏，已禁止接管；请检查日志'})
        if self.system['sensor_failed']:
            alarms.append({'code': 'temperature_unavailable', 'level': 'critical',
                           'message': '温度读取失败'})
        if raw_disk_temp is not None and raw_disk_temp >= 60:
            peak = [s for s in disk if s['temperature'] == raw_disk_temp]
            excluded_peak = bool(peak) and all(s['id'] in ignored for s in peak)
            note = '（最高读数来自已排除节点；仍保留原始高温提醒）' if excluded_peak else ''
            alarms.append({'code': 'disk_hot', 'level': 'critical',
                           'message': '磁盘温度偏高：' + str(raw_disk_temp) + '°C' + note})
        if raw_cpu_temp is not None and raw_cpu_temp >= 85:
            peak = [s for s in cpu if s['temperature'] == raw_cpu_temp]
            excluded_peak = bool(peak) and all(s['id'] in ignored for s in peak)
            note = '（最高读数来自已排除节点；仍保留原始高温提醒）' if excluded_peak else ''
            alarms.append({'code': 'cpu_hot', 'level': 'critical',
                           'message': 'CPU 温度偏高：' + str(raw_cpu_temp) + '°C' + note})
        failed_groups = {mode.get('group_id') for mode in self.modes.values() if mode.get('rpm_fault')}
        for group_id in sorted(failed_groups):
            group = next((item for item in self.config['fan_groups'] if item['id'] == group_id), None)
            name = group['name'] if group else group_id
            alarms.append({'code': 'fan_stall:' + group_id, 'level': 'critical',
                           'message': '风扇组转速反馈异常，已接管输出按 50% 兜底：' + name})
        for cid in self.pending_ids():
            if cid not in self.modes:
                alarms.append({'code': 'pending_recovery', 'level': 'critical', 'message': '通道仍待恢复：' + cid})
        for alarm in alarms:
            if alarm['code'] not in {a['code'] for a in self.alarms}:
                self.log('warning', alarm['message'])
        self.alarms = alarms
        temperatures = {kind: {sensor['id']: sensor['temperature'] for sensor in sensors
                               if sensor['kind'] == kind}
                        for kind in ('cpu', 'disk')}
        self.history.append({'time': time.time(), 'cpu_temp': cpu_temp, 'disk_temp': disk_temp,
                             'temperatures': temperatures, 'max_temp': max_temp,
                             'fans': {fan['id']: fan['rpm'] for fan in self.hw['fans']},
                             'channels': {channel['id']: channel['percent'] for channel in self.hw['pwm_channels']}})

    def rebuild_sensor_baseline(self):
        source = self.config['temperature_source']
        required = ('cpu', 'disk') if source == 'max' else (source,)
        ignored = set(self.config.get('ignored_temperature_sensor_ids', []))
        self.sensor_baseline = {sid for sid, metadata in self.known_temp_sensors.items()
                                if metadata['kind'] in required and sid not in ignored}

    def group(self, group_id):
        return next((group for group in self.config['fan_groups'] if group['id'] == group_id), None)

    def curve_settings(self, group=None):
        return group if group and group['curve_mode'] == 'custom' else self.config

    @staticmethod
    def _disk_sensor_covered(sensor, sensors, ignored):
        blocks = set(sensor.get('block_devices', []))
        return bool(blocks) and any(
            other['id'] not in ignored and other['kind'] == 'disk' and other['temperature'] is not None
            and blocks.intersection(other.get('block_devices', [])) for other in sensors)

    def temperature_state(self, source, baseline=(), ignored=()):
        sensors = self.hw['temperature_sensors']
        required = ('cpu', 'disk') if source == 'max' else (source,)
        ignored = set(ignored)
        relevant = [sensor for sensor in sensors if sensor['kind'] in required and sensor['id'] not in ignored]
        values = [sensor['temperature'] for sensor in relevant if sensor['temperature'] is not None]
        present = {sensor['id'] for sensor in relevant}
        missing = []
        for sensor_id in set(baseline) - ignored - present:
            metadata = self.known_temp_sensors.get(sensor_id, {})
            if metadata.get('kind') == 'disk' and self._disk_sensor_covered(
                    {'block_devices': metadata.get('block_devices', ())}, sensors, ignored):
                continue
            missing.append(sensor_id)
        unreadable = any(sensor['temperature'] is None and not self._disk_sensor_covered(sensor, sensors, ignored)
                         for sensor in relevant)
        failed = not values or bool(missing) or unreadable
        return max(values, default=None), failed, sorted(missing)

    def curve_percent(self, temp, curve=None):
        curve = self.config['curve'] if curve is None else curve
        if temp >= curve[-1]['temp']:
            return curve[-1]['percent']
        if temp <= curve[0]['temp']:
            return curve[0]['percent']
        for low, high in zip(curve, curve[1:]):
            if low['temp'] <= temp <= high['temp']:
                ratio = (temp - low['temp']) / (high['temp'] - low['temp'])
                return round(low['percent'] + ratio * (high['percent'] - low['percent']), 1)
        return curve[-1]['percent']

    def effective_percent(self, mode):
        settings = self.curve_settings(self.group(mode.get('group_id')))
        temp, failed, _ = self.temperature_state(settings['temperature_source'], mode.get('sensor_baseline', ()),
                                                  settings.get('ignored_temperature_sensor_ids', []))
        if mode.get('rpm_fault') or failed:
            return 50, 'failsafe'
        if mode['mode'] == 'auto':
            return self.curve_percent(temp, settings['curve']), 'auto'
        if mode['mode'] == 'full':
            return 100, 'full'
        return mode['percent'], 'manual'

    def apply_controls(self):
        failed_groups = set()
        rpm_checks = {}
        now = time.monotonic()
        ignored_pwm = set(self.config.get('ignored_pwm_ids', []))
        for cid, mode in list(self.modes.items()):
            if cid in ignored_pwm:
                continue
            fan_id = mode.get('fan_id')
            fan = next((f for f in self.hw['fans'] if f['id'] == fan_id), None) if fan_id else None
            group_id = mode.get('group_id')
            check_id = group_id or cid
            if fan_id and now - mode['acquired_at'] >= 6:
                if check_id not in rpm_checks:
                    bad = fan is None or fan['rpm'] is None or fan['rpm'] <= 0
                    peer = next((item for item in self.modes.values()
                                 if (item.get('group_id') or '') == (group_id or '') and item.get('fan_id') == fan_id), mode)
                    bad_samples = peer.get('rpm_bad_samples', 0) + 1 if bad else 0
                    rpm_checks[check_id] = (bad_samples, bad_samples >= 2, peer.get('rpm_fault', False))
                bad_samples, rpm_fault, was_fault = rpm_checks[check_id]
                mode.update({'rpm_bad_samples': bad_samples, 'rpm_fault': rpm_fault})
                if rpm_fault and not was_fault:
                    self.log('warning', 'FAN 组 RPM 反馈异常，PWM 输出按 50% 兜底：' + (group_id or cid))
            percent, effective = self.effective_percent(mode)
            try:
                self.hardware.set_percent(cid, percent)
                mode.update({'effective_mode': effective, 'target_percent': percent, 'error': None})
            except HardwareError as exc:
                mode['error'] = str(exc)
                group_id = mode.get('group_id')
                failed_groups.add(group_id or cid)
                self.log('error', 'FAN 组 PWM 控制失败，尝试恢复整组：' + (group_id or cid) + '，' + str(exc))
        for group_id in failed_groups:
            if group_id in {group['id'] for group in self.config['fan_groups']}:
                targets = [channel_id for channel_id, mode in self.modes.items() if mode.get('group_id') == group_id]
            else:
                targets = [group_id]
            try:
                self.clear_desired([group_id])
            finally:
                self._release_targets(targets)
        self.recovery_blocked = self.journal_corrupt
        self.alarms = [a for a in self.alarms if not a['code'].startswith('fan_stall:')]
        failed_groups = {mode.get('group_id') for mode in self.modes.values() if mode.get('rpm_fault')}
        for group_id in sorted(failed_groups):
            group = next((item for item in self.config['fan_groups'] if item['id'] == group_id), None)
            name = group['name'] if group else group_id
            self.alarms.append({'code': 'fan_stall:' + group_id, 'level': 'critical',
                                'message': '风扇组转速反馈异常，已接管输出按 50% 兜底：' + name})
        # Read actual driver values, rather than echoing a requested target as success.
        self.hw = self.hardware.scan()

    def control(self, body, restoring=False):
        if not isinstance(body, dict) or set(body) - {'id', 'mode', 'percent'}:
            raise ValueError('无效控制请求')
        group_id, mode = body.get('id'), body.get('mode')
        if not isinstance(group_id, str) or mode not in ('monitor', 'manual', 'auto', 'full'):
            raise ValueError('请选择有效 FAN 分组和模式')
        with self.lock:
            if self.shutdown_started:
                raise ValueError('服务正在关闭')
            if mode == 'monitor':
                self.release_fan(group_id)
                return self.status()
            self.sample()
            group = next((item for item in self.config['fan_groups'] if item['id'] == group_id), None)
            if not group:
                raise ValueError('FAN 分组不存在')
            if self.recovery_blocked:
                raise ValueError('恢复记录损坏，已暂停所有接管；请检查事件记录')
            pending = self.pending_ids()
            blocked_outputs = pending.intersection(group['pwm_ids'])
            if blocked_outputs:
                raise ValueError('此 FAN 组含有仍待恢复的 PWM：' + '、'.join(sorted(blocked_outputs)))
            if self.pwm_test and self.pwm_test['id'] in group['pwm_ids']:
                raise ValueError('此 FAN 组的 PWM 正在测试，请先结束测试')
            if not group['pwm_ids']:
                raise ValueError('请先为该 FAN 分组添加并手动验证至少一个 PWM 输出')
            if set(group['verified_pwm_ids']) != set(group['pwm_ids']):
                raise ValueError('该 FAN 分组含有尚未手动验证的 PWM 输出，暂不能控制')
            channels = {c['id']: c for c in self.hw['pwm_channels']}
            if any(cid in self.config.get('ignored_pwm_ids', []) for cid in group['pwm_ids']):
                raise ValueError('FAN 组含有已忽略的 PWM 接口，请先解除忽略或调整归属')
            missing = [cid for cid in group['pwm_ids'] if cid not in channels]
            if missing:
                raise ValueError('FAN 分组包含当前未发现的 PWM 输出，请重新扫描并检查分组')
            unwritable = [cid for cid in group['pwm_ids'] if not channels[cid]['writable']]
            if unwritable:
                raise ValueError('FAN 分组含有不可写 PWM 输出：' + ', '.join(unwritable))
            last_manual = self.desired_modes.get(group_id, {}).get('percent', 50)
            percent = body.get('percent', last_manual) if mode == 'manual' else 100
            if mode == 'manual' and (not valid_number(percent) or not 25 <= percent <= 100):
                raise ValueError('手动转速必须在 25% 至 100% 之间')
            rpm_id = group['rpm_id'] if group['rpm_verified'] else None
            if rpm_id is not None and rpm_id not in {f['id'] for f in self.hw['fans']}:
                raise ValueError('已验证的 RPM 输入当前不可用，请检查风扇组关联')
            settings = self.curve_settings(group)
            if restoring:
                _, sensor_failed, _ = self.temperature_state(settings['temperature_source'], (),
                                                              settings.get('ignored_temperature_sensor_ids', []))
                rpm = next((fan['rpm'] for fan in self.hw['fans'] if fan['id'] == rpm_id), None)
                if sensor_failed or (rpm_id is not None and (rpm is None or rpm <= 0)):
                    raise ValueError('启动时温度或 RPM 反馈不可用，已暂停此 FAN')
            baseline = {sensor['id'] for sensor in self.hw['temperature_sensors']
                        if sensor['kind'] in (('cpu', 'disk') if settings['temperature_source'] == 'max'
                                              else (settings['temperature_source'],))
                        and sensor['id'] not in settings.get('ignored_temperature_sensor_ids', [])}
            snapshots = {cid: self.hardware.snapshot(cid) for cid in group['pwm_ids'] if cid not in self.owned}
            if snapshots:
                candidate = {**self.owned, **snapshots}
                self.persist_owned(candidate)
                self.owned = candidate
            if not self.modes:
                self.rebuild_sensor_baseline()
            for cid in group['pwm_ids']:
                previous = self.modes.get(cid, {})
                same_group = previous.get('group_id') == group_id and previous.get('fan_id') == rpm_id
                self.modes[cid] = {'mode': mode, 'percent': percent, 'fan_id': rpm_id, 'group_id': group_id,
                                   'acquired_at': previous.get('acquired_at', time.monotonic()) if same_group else time.monotonic(),
                                   'sensor_baseline': previous.get('sensor_baseline', baseline) if same_group else set(baseline),
                                   'rpm_bad_samples': previous.get('rpm_bad_samples', 0) if same_group else 0,
                                   'rpm_fault': previous.get('rpm_fault', False) if same_group else False}
            try:
                self.sample()
                self.apply_controls()
                if not all(cid in self.modes and not self.modes[cid].get('error') for cid in group['pwm_ids']):
                    raise HardwareError('FAN 组控制失败，已尝试恢复整组；请检查事件记录')
                self.set_desired(group_id, {'mode': mode, 'percent': percent if mode == 'manual' else last_manual})
            except Exception as exc:
                try:
                    self.clear_desired([group_id])
                except OSError as persist_exc:
                    self.log('error', '停止 FAN 的状态无法保存：' + str(persist_exc))
                finally:
                    self._release_targets(group['pwm_ids'])
                if isinstance(exc, (ValueError, HardwareError, OSError)):
                    raise
                raise HardwareError('FAN 控制异常，已尝试恢复此组原始状态：' + str(exc)) from exc
            self.startup_errors.pop(group_id, None)
            self.log('info', '设置 FAN 分组 ' + group['name'] + ' 的 ' + str(len(group['pwm_ids'])) + ' 路 PWM 为 ' + mode)
            return self.status()

    def _release_with_intent(self, targets, group_ids):
        persistence_error = None
        try:
            self.clear_desired(group_ids)
        except OSError as exc:
            persistence_error = exc
            self.log('error', '停止 FAN 的状态无法保存，仍将恢复硬件：' + str(exc))
        failures = []
        if self.pwm_test and self.pwm_test['id'] in targets:
            tested = self.pwm_test['id']
            failures.extend(self.finish_pwm_test('released'))
            targets = [cid for cid in targets if cid != tested]
        failures.extend(self._release_targets(targets))
        self.recovery_blocked = self.journal_corrupt
        self.sample()
        if failures:
            detail = '；'.join(failures)
            if persistence_error:
                detail += '；停止状态保存失败：' + str(persistence_error)
            raise HardwareError(detail)
        if persistence_error:
            raise persistence_error
        return self.status()

    def release(self, cid=None):
        with self.lock:
            if cid is not None and not isinstance(cid, str):
                raise ValueError('无效通道')
            ignored = set(self.config.get('ignored_pwm_ids', []))
            if cid is not None and cid in ignored:
                raise ValueError('此 PWM 接口已忽略；解除忽略后才能尝试恢复')
            targets = [cid] if cid is not None else [owned_id for owned_id in self.owned if owned_id not in ignored]
            group_ids = [group['id'] for group in self.config['fan_groups']
                         if cid is None or cid in group['pwm_ids']]
            return self._release_with_intent(targets, group_ids)

    def release_pending(self, cid):
        with self.lock:
            if not isinstance(cid, str) or cid in self.config.get('ignored_pwm_ids', []) or cid not in self.pending_ids():
                raise ValueError('只允许重试仍待恢复的 PWM；正在控制或测试的接口请先结束操作')
            failures = self._release_targets([cid])
            self.sample()
            if failures:
                raise HardwareError('；'.join(failures))
            return self.status()

    def release_fan(self, group_id):
        with self.lock:
            group = self.group(group_id)
            if not group:
                raise ValueError('FAN 分组不存在')
            return self._release_with_intent(list(group['pwm_ids']), [group_id])

    def _release_targets(self, targets):
        failures = []
        ignored = set(self.config.get('ignored_pwm_ids', []))
        for target in list(dict.fromkeys(targets)):
            if target in ignored:
                self.modes.pop(target, None)
                continue
            if target not in self.owned:
                self.modes.pop(target, None)
                continue
            try:
                self.hardware.restore(target, self.owned[target])
                remaining = dict(self.owned)
                del remaining[target]
                self.persist_owned(remaining)
                self.owned = remaining
                self.modes.pop(target, None)
                self.log('info', '已恢复 PWM 输出原始状态：' + target)
            except Exception as exc:
                failures.append(target + '：' + str(exc))
                self.modes.pop(target, None)
                self.log('error', 'PWM 输出恢复失败，将保留恢复记录：' + target + '，' + str(exc))
        return failures

    def update_config(self, body):
        with self.lock:
            merged = copy.deepcopy(self.config)
            if not isinstance(body, dict):
                raise ValueError('配置必须为对象')
            merged.update(body)
            detach_ignored_pwm(merged)
            new = validate_config(merged)
            newly_ignored = set(new['ignored_pwm_ids']) - set(self.config['ignored_pwm_ids'])
            # An output that is actively owned or under timed testing cannot be
            # ignored. A failed, already-paused recovery may be quarantined:
            # retain its exact snapshot in the recovery journal, but do not
            # access the interface again until the user explicitly unignores it.
            pending = self.pending_ids()
            blocked = newly_ignored.intersection(set(self.owned) - pending)
            if self.pwm_test and self.pwm_test['id'] in newly_ignored:
                blocked.add(self.pwm_test['id'])
            if blocked:
                raise ValueError('正在接管或测试中的 PWM 不能忽略；请先释放或结束测试。待恢复接口可以忽略，恢复记录会保留')
            pwm_ids = {c['id'] for c in self.hw['pwm_channels']}
            rpm_inputs = {f['id'] for f in self.hw['fans']}
            # Preserve stale references long enough for the UI to remove them; they can never be controlled.
            pwm_ids.update(cid for group in self.config['fan_groups'] for cid in group['pwm_ids'])
            rpm_inputs.update(group['rpm_id'] for group in self.config['fan_groups'] if group['rpm_id'] is not None)
            for group in new['fan_groups']:
                if any(cid not in pwm_ids for cid in group['pwm_ids']):
                    raise ValueError('FAN 分组引用了当前不存在的 PWM 输出')
                if group['rpm_id'] is not None and group['rpm_id'] not in rpm_inputs:
                    raise ValueError('FAN 分组引用了当前不存在的 RPM 输入')
            active_group_ids = {mode.get('group_id') for mode in self.modes.values() if mode.get('group_id')}
            old_groups = {group['id']: group for group in self.config['fan_groups']}
            new_groups = {group['id']: group for group in new['fan_groups']}
            routing_fields = ('pwm_ids', 'verified_pwm_ids', 'rpm_id', 'rpm_verified')
            for group_id in active_group_ids:
                old, replacement = old_groups.get(group_id), new_groups.get(group_id)
                if replacement is None or any(old[field] != replacement[field] for field in routing_fields):
                    raise ValueError('请先释放正在接管的 FAN 组，再修改该组的 PWM 或 RPM 关联')
            if self.pwm_test:
                tested = self.pwm_test['id']
                old_mapping = [(group['id'], tested in group['verified_pwm_ids']) for group in old_groups.values() if tested in group['pwm_ids']]
                new_mapping = [(group['id'], tested in group['verified_pwm_ids']) for group in new_groups.values() if tested in group['pwm_ids']]
                if old_mapping != new_mapping:
                    raise ValueError('请先结束 PWM 测试，再修改该接口的 FAN 归属')
            atomic_json(self.etc / 'config.json', new)
            old_global_source = self.config['temperature_source']
            old_global_ignored = set(self.config['ignored_temperature_sensor_ids'])
            source_changed = old_global_source != new['temperature_source'] or old_global_ignored != set(new['ignored_temperature_sensor_ids'])
            self.config = new
            self.hardware.set_ignored_pwm_ids(new['ignored_pwm_ids'])
            self.hw = self.hardware.scan()
            if source_changed and self.modes:
                self.rebuild_sensor_baseline()
            for mode in self.modes.values():
                old = old_groups.get(mode.get('group_id'))
                replacement = new_groups.get(mode.get('group_id'))
                old_source = old['temperature_source'] if old and old['curve_mode'] == 'custom' else old_global_source
                old_ignored = set(old.get('ignored_temperature_sensor_ids', [])) if old and old['curve_mode'] == 'custom' else old_global_ignored
                settings = self.curve_settings(replacement)
                if old_source != settings['temperature_source'] or old_ignored != set(settings.get('ignored_temperature_sensor_ids', [])):
                    kinds = ('cpu', 'disk') if settings['temperature_source'] == 'max' else (settings['temperature_source'],)
                    excluded = set(settings.get('ignored_temperature_sensor_ids', []))
                    mode['sensor_baseline'] = {sensor['id'] for sensor in self.hw['temperature_sensors']
                                               if sensor['kind'] in kinds and sensor['id'] not in excluded}
            self.clear_desired(set(old_groups) - set(new_groups))
            self.sample()
            self.apply_controls()
            self.log('info', '已保存温度曲线、温度来源或 FAN/PWM/RPM 分组')
            return copy.deepcopy(self.config)

    def status(self):
        with self.lock:
            fans = {f['id']: f for f in self.hw['fans']}
            channels = []
            for channel in self.hw['pwm_channels']:
                item = dict(channel)
                mode = self.modes.get(channel['id'])
                item.update({'mode': mode['mode'] if mode else 'monitor', 'owned': channel['id'] in self.owned,
                             'group_id': (mode or {}).get('group_id'),
                             'effective_mode': (mode or {}).get('effective_mode', 'monitor'),
                             'target_percent': (mode or {}).get('target_percent'), 'error': (mode or {}).get('error'),
                             'rpm_protection': bool((mode or {}).get('fan_id')) and not item.get('ignored'),
                             'rpm_fault': bool((mode or {}).get('rpm_fault')) and not item.get('ignored')})
                channels.append(item)
            group_status = []
            for group in self.config['fan_groups']:
                outputs = [next((channel for channel in channels if channel['id'] == cid), None) for cid in group['pwm_ids']]
                outputs = [channel for channel in outputs if channel is not None]
                rpm = fans.get(group['rpm_id']) if group['rpm_id'] and group['rpm_verified'] else None
                owned_outputs = [channel for channel in outputs if channel['owned']]
                modes = {channel['mode'] for channel in owned_outputs}
                effective_modes = {channel['effective_mode'] for channel in owned_outputs}
                errors = [channel['error'] for channel in outputs if channel['error']]
                settings = self.curve_settings(group)
                live_mode = next((mode for mode in self.modes.values() if mode.get('group_id') == group['id']), {})
                source_temp, sensor_failed, missing_sensors = self.temperature_state(
                    settings['temperature_source'], live_mode.get('sensor_baseline', ()),
                    settings.get('ignored_temperature_sensor_ids', []))
                group_status.append({**copy.deepcopy(group), 'outputs': outputs,
                                     'rpm_name': rpm['name'] if rpm else None,
                                     'rpm': rpm['rpm'] if rpm else None,
                                     'owned': any(cid in self.owned for cid in group['pwm_ids']),
                                     'pending': bool(self.pending_ids().intersection(group['pwm_ids'])),
                                     'testing': bool(self.pwm_test and self.pwm_test['id'] in group['pwm_ids']),
                                     'saved_mode': self.desired_modes.get(group['id'], {}).get('mode', 'monitor'),
                                     'saved_percent': self.desired_modes.get(group['id'], {}).get('percent', 50),
                                     'startup_error': self.startup_errors.get(group['id']),
                                     'source_temp': source_temp, 'sensor_failed': sensor_failed,
                                     'effective_temperature_source': settings['temperature_source'],
                                     'missing_sensor_ids': missing_sensors,
                                     'mode': next(iter(modes)) if len(modes) == 1 and len(owned_outputs) == len(outputs) else ('mixed' if owned_outputs else 'monitor'),
                                     'effective_mode': 'failsafe' if 'failsafe' in effective_modes else next(iter(effective_modes)) if len(effective_modes) == 1 else ('monitor' if not effective_modes else 'mixed'),
                                     'target_percent': max((channel['target_percent'] for channel in outputs if channel['target_percent'] is not None), default=None),
                                     'writable': bool(outputs) and len(outputs) == len(group['pwm_ids']) and all(channel['writable'] for channel in outputs),
                                     'ready': bool(outputs) and len(outputs) == len(group['pwm_ids']) and all(channel['writable'] for channel in outputs) and set(group['verified_pwm_ids']) == set(group['pwm_ids']),
                                     'rpm_fault': any(channel['rpm_fault'] for channel in outputs),
                                     'error': '；'.join(errors) if errors else None})
            return {'ok': True, 'demo': self.hardware.demo, 'time': time.time(),
                    'system': copy.deepcopy(self.system), 'channels': channels, 'fans': copy.deepcopy(self.hw['fans']),
                    'fan_groups': group_status, 'rpm_inputs': copy.deepcopy(self.hw['fans']),
                    'alarms': copy.deepcopy(self.alarms), 'mode_summary': 'active' if self.modes else 'monitor',
                    'driver_available': any(not channel.get('ignored') for channel in channels), 'recovery_blocked': self.recovery_blocked,
                    'pending_recovery_ids': sorted(self.pending_ids()),
                    'pwm_test': self.test_status(), 'pwm_test_result': copy.deepcopy(self.pwm_test_result)}

    def shutdown(self):
        self.stop_event.set()
        with self.lock:
            self.shutdown_started = True
            if self._test_timer:
                self._test_timer.cancel()
            try:
                if self.pwm_test:
                    self.finish_pwm_test('shutdown')
            finally:
                self._release_targets([cid for cid in self.owned if cid not in self.config.get('ignored_pwm_ids', [])])
