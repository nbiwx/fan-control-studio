"""Read hwmon dynamically; writes are limited to discovered PWM attributes."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path


class HardwareError(RuntimeError):
    pass


def read_number(path):
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def device_metadata(directory, name):
    model = None
    for candidate in (directory / 'device/model', directory / 'device/device/model'):
        try:
            model = ' '.join(candidate.read_text().split())[:160]
            if model:
                break
        except OSError:
            pass
    blocks = set()
    for candidate in list((directory / 'device/block').glob('*')) + list((directory / 'device').glob('nvme*n*')):
        if re.fullmatch(r'(?:sd[a-z]+|vd[a-z]+|nvme\d+n\d+|mmcblk\d+)', candidate.name):
            blocks.add(candidate.name)
    block_names = sorted(blocks)
    if name == 'nvme' and not block_names:
        try:
            controller = (directory / 'device').resolve().name
            if re.fullmatch(r'nvme\d+', controller):
                block_names = sorted(candidate.name for candidate in Path('/sys/class/block').glob(controller + 'n*')
                                     if re.fullmatch(r'nvme\d+n\d+', candidate.name))
        except OSError:
            pass
    components = [', '.join(b.upper() for b in block_names)] if block_names else []
    if model:
        components.append(model)
    return {'display_name': ' · '.join(components) if components else name,
            'model': model, 'block_devices': block_names}


class Hardware:
    def __init__(self, root='/sys/class/hwmon', demo=False, block_root='/sys/class/block'):
        self.root = Path(root)
        self.block_root = Path(block_root)
        self.demo = demo
        self._paths = {}
        self._sim = {}
        self.ignored_pwm_ids = set()
        self.smartctl = shutil.which('smartctl') or next(
            (path for path in ('/usr/sbin/smartctl', '/sbin/smartctl') if os.access(path, os.X_OK)), None)
        self._smart_lock = threading.Lock()
        self._smart_cache = {}
        self._smart_queue = []
        self._smart_worker_active = False

    def set_ignored_pwm_ids(self, ids):
        self.ignored_pwm_ids = set(ids)
        self._paths = {cid: paths for cid, paths in self._paths.items() if cid not in self.ignored_pwm_ids}

    def scan(self):
        if self.demo:
            return self._demo()
        devices, fans, channels, sensors = [], [], [], []
        paths = {}
        for directory in sorted(self.root.glob('hwmon*')):
            try:
                name = (directory / 'name').read_text().strip()
                real = str(directory.resolve())
                # hwmon indices change at boot; the parent bus/device identity does not.
                identity = re.sub(r'/hwmon(?:/hwmon\d+)?$', '', real)
                device_id = 'dev-' + hashlib.sha256((identity + ':' + name).encode()).hexdigest()[:12]
                metadata = device_metadata(directory, name)
                devices.append({'id': device_id, 'name': name, 'identity': identity, **metadata})
                for attribute in sorted(directory.glob('fan*_input')):
                    stem = attribute.name[:-6]
                    label_path = directory / (stem + '_label')
                    label = label_path.read_text().strip() if label_path.exists() else stem.upper()
                    fans.append({'id': device_id + ':' + stem, 'device_id': device_id, 'name': label,
                                 'rpm': read_number(attribute)})
                for attribute in sorted(directory.glob('temp*_input')):
                    stem = attribute.name[:-6]
                    label_path = directory / (stem + '_label')
                    label = label_path.read_text().strip() if label_path.exists() else stem
                    group = ('cpu' if name in ('coretemp', 'k10temp', 'cpu_thermal', 'zenpower') else
                             'disk' if name in ('drivetemp', 'nvme') or metadata['block_devices'] else 'other')
                    if group == 'disk':
                        suffix = (' · ' + label) if label != stem else ''
                        label = metadata['display_name'] + suffix
                    value = read_number(attribute)
                    temp = value / 1000 if value is not None and -20_000 <= value <= 150_000 else None
                    sensors.append({'id': device_id + ':' + stem, 'device_id': device_id,
                                    'name': label, 'kind': group, 'temperature': temp,
                                    'block_devices': metadata['block_devices'], 'source': 'hwmon'})
                for attribute in sorted(directory.glob('pwm*')):
                    if not re.fullmatch(r'pwm\d+', attribute.name):
                        continue
                    cid = device_id + ':' + attribute.name
                    if cid in self.ignored_pwm_ids:
                        channels.append({'id': cid, 'device_id': device_id,
                                         'name': name + ' · ' + attribute.name.upper(),
                                         'pwm': None, 'percent': None, 'enable': None,
                                         'writable': False, 'ignored': True})
                        continue
                    enable = directory / (attribute.name + '_enable')
                    if not enable.is_file():
                        continue
                    value, enabled = read_number(attribute), read_number(enable)
                    channels.append({'id': cid, 'device_id': device_id,
                                     'name': name + ' · ' + attribute.name.upper(),
                                     'pwm': value, 'percent': round(value * 100 / 255) if value is not None else None,
                                     'enable': enabled, 'writable': os.access(attribute, os.W_OK) and os.access(enable, os.W_OK),
                                     'ignored': False,
                                     })
                    paths[cid] = (attribute.resolve(), enable.resolve(), identity)
            except (OSError, ValueError):
                continue
        self._paths = paths
        disks = self._scan_disks(sensors)
        return {'devices': devices, 'fans': fans, 'pwm_channels': channels, 'temperature_sensors': sensors,
                'disks': disks, 'demo': False}

    def _demo(self):
        did = 'demo-controller'
        for i in range(1, 6):
            self._sim.setdefault(did + ':pwm' + str(i), {'pwm': 112, 'enable': 2})
        devices = [{'id': did, 'name': 'demo-controller', 'identity': 'simulation/demo-controller'},
                   {'id': 'demo-cpu', 'name': 'coretemp', 'identity': 'simulation/cpu'},
                   {'id': 'demo-disk', 'name': 'drivetemp', 'identity': 'simulation/disk'}]
        channels = [{'id': cid, 'device_id': did, 'name': 'Demo Controller · PWM' + cid[-1],
                     'pwm': v['pwm'], 'percent': round(v['pwm'] / 2.55), 'enable': v['enable'],
                     'writable': True, 'ignored': False} for cid, v in self._sim.items()
                    if cid not in self.ignored_pwm_ids]
        channels.extend({'id': cid, 'device_id': did, 'name': 'Demo Controller · PWM' + cid[-1],
                         'pwm': None, 'percent': None, 'enable': None,
                         'writable': False, 'ignored': True}
                        for cid in self.ignored_pwm_ids if cid.startswith(did + ':'))
        # These response pairs exist only in the clearly labelled simulation.
        # Real PWM/tachometer associations are never inferred by this reader.
        duty1 = self._sim[did + ':pwm1']['pwm'] / 255
        duty2 = self._sim[did + ':pwm2']['pwm'] / 255
        fans = [{'id': did + ':fan1', 'device_id': did, 'name': 'FAN1', 'rpm': round(650 + duty1 * 1200)},
                {'id': did + ':fan2', 'device_id': did, 'name': 'FAN2', 'rpm': round(700 + duty2 * 1700)}]
        sensors = [{'id': 'demo-cpu:temp1', 'device_id': 'demo-cpu', 'name': 'CPU Package', 'kind': 'cpu', 'temperature': 46.0},
                   {'id': 'demo-disk:temp1', 'device_id': 'demo-disk', 'name': 'Demo Disk 1', 'kind': 'disk', 'temperature': 38.0,
                    'block_devices': ['demo-disk-1'], 'source': 'hwmon'}]
        return {'devices': devices, 'fans': fans, 'pwm_channels': channels, 'temperature_sensors': sensors,
                'disks': [{'id': 'disk:demo-disk-1', 'name': 'demo-disk-1', 'model': 'Demo Disk 1',
                           'temperature': 38.0, 'source': 'hwmon', 'status': 'available',
                           'detail': '温度传感器'}], 'demo': True}

    def _scan_disks(self, sensors):
        inventory = []
        names = set()
        try:
            block_entries = sorted(self.block_root.iterdir()) if self.block_root.exists() else []
        except OSError:
            block_entries = []
        for entry in block_entries:
            name = entry.name
            if not re.fullmatch(r'(?:sd[a-z]+|hd[a-z]+|vd[a-z]+|nvme\d+n\d+|mmcblk\d+)', name):
                continue
            if (entry / 'partition').exists():
                continue
            try:
                resolved = entry.resolve()
            except OSError:
                resolved = entry
            if '/virtual/' in str(resolved):
                continue
            names.add(name)
            model = ''
            for candidate in (entry / 'device/model', entry / 'device/name', entry / 'device/label'):
                try:
                    model = ' '.join(candidate.read_text().split())[:160]
                    if model:
                        break
                except OSError:
                    pass
            matched = [sensor for sensor in sensors if name in sensor.get('block_devices', [])]
            readings = [sensor for sensor in matched if sensor.get('temperature') is not None]
            temperature = max((sensor['temperature'] for sensor in readings), default=None)
            source = 'hwmon' if temperature is not None else None
            status, detail = ('available', '温度传感器') if temperature is not None else ('unavailable', '未检测到温度读数')
            sensor_id = 'smart:' + hashlib.sha256(str(resolved).encode()).hexdigest()[:16]
            record = {'id': 'disk:' + name, 'name': name, 'model': model or name, 'sensor_id': sensor_id,
                      'temperature': temperature, 'source': source, 'status': status, 'detail': detail}
            if temperature is None:
                smart = self._cached_smart_temperature(name)
                if smart and smart.get('temperature') is not None:
                    record.update({'temperature': smart['temperature'], 'source': 'smartctl',
                                   'status': 'available', 'detail': 'SMART 温度'})
                    if time.monotonic() - smart.get('checked_at', 0) >= 60:
                        self._queue_smart_read(name, self._runtime_status(entry))
                else:
                    runtime_status = self._runtime_status(entry)
                    if runtime_status in ('suspended', 'suspending'):
                        record.update({'status': 'sleeping', 'detail': '设备休眠，暂不唤醒读取'})
                    elif self.smartctl:
                        self._queue_smart_read(name, runtime_status)
                        cache = self._smart_cache.get(name, {})
                        if cache.get('checked_at'):
                            record.update({'status': 'unavailable', 'detail': 'SMART 温度读取失败'})
                        else:
                            record.update({'status': 'reading', 'detail': '正在读取 SMART 温度'})
                    elif runtime_status not in ('suspended', 'suspending'):
                        record.update({'status': 'unavailable', 'detail': '系统未提供 smartctl；hwmon 没有温度读数'})
            inventory.append(record)
        for sensor in sensors:
            if sensor.get('kind') != 'disk' or sensor.get('block_devices'):
                continue
            if sensor.get('temperature') is None:
                continue
            key = 'unknown:' + sensor['device_id']
            if key in names:
                continue
            inventory.append({'id': 'disk:' + key, 'name': sensor['name'], 'model': sensor['name'],
                              'temperature': sensor['temperature'], 'source': 'hwmon',
                              'status': 'available', 'detail': 'hwmon 温度传感器'})
        # A SMART fallback becomes a normal disk sensor, so it can drive curves and be excluded by node.
        for disk in inventory:
            if disk['source'] == 'smartctl' and not any(
                    sensor.get('kind') == 'disk' and disk['name'] in sensor.get('block_devices', [])
                    and sensor.get('temperature') is not None for sensor in sensors):
                sensors.append({'id': disk['sensor_id'], 'device_id': disk['id'],
                                'name': disk['model'] + ' · SMART', 'kind': 'disk',
                                'temperature': disk['temperature'], 'block_devices': [disk['name']],
                                'source': 'smartctl'})
        return inventory

    @staticmethod
    def _runtime_status(entry):
        for candidate in (entry / 'device/power/runtime_status', entry / 'device/device/power/runtime_status'):
            try:
                return candidate.read_text().strip().lower()
            except OSError:
                pass
        return None

    def _cached_smart_temperature(self, name):
        with self._smart_lock:
            entry = self._smart_cache.get(name)
            return dict(entry) if entry else None

    def _queue_smart_read(self, name, runtime_status):
        if not self.smartctl or runtime_status in ('suspended', 'suspending'):
            return
        now = time.monotonic()
        with self._smart_lock:
            last = self._smart_cache.get(name, {}).get('checked_at', 0)
            if now - last < 60 or name in self._smart_queue:
                return
            self._smart_queue.append(name)
            if not self._smart_worker_active:
                self._smart_worker_active = True
                threading.Thread(target=self._smart_worker, name='disk-smart-read', daemon=True).start()

    def _smart_worker(self):
        while True:
            with self._smart_lock:
                if not self._smart_queue:
                    self._smart_worker_active = False
                    return
                name = self._smart_queue.pop(0)
            temperature = None
            try:
                completed = subprocess.run([self.smartctl, '-n', 'standby', '-j', '-A', '/dev/' + name],
                                           capture_output=True, text=True, timeout=8, check=False)
                data = json.loads(completed.stdout)
                if not isinstance(data, dict):
                    raise ValueError('Invalid SMART response')
                temp_info = data.get('temperature')
                node = temp_info.get('current') if isinstance(temp_info, dict) else None
                if isinstance(node, dict):
                    temperature = self._bounded_temperature(node.get('value'))
                elif node is not None:
                    temperature = self._bounded_temperature(node)
                if temperature is None:
                    attribute_info = data.get('ata_smart_attributes')
                    attributes = attribute_info.get('table', []) if isinstance(attribute_info, dict) else []
                    for attribute in attributes:
                        if not isinstance(attribute, dict):
                            continue
                        if attribute.get('id') not in (190, 194):
                            continue
                        raw = attribute.get('raw', {})
                        raw_text = raw.get('string', '') if isinstance(raw, dict) else ''
                        match = re.match(r'\s*(-?\d+)', str(raw_text))
                        candidate = int(match.group(1)) if match else None
                        if candidate is None and isinstance(raw, dict) and isinstance(raw.get('value'), int):
                            candidate = raw['value']
                        temperature = self._bounded_temperature(candidate)
                        if temperature is not None:
                            break
                nvme_info = data.get('nvme_smart_health_information_log')
                nvme = nvme_info.get('temperature') if isinstance(nvme_info, dict) else None
                if temperature is None:
                    if isinstance(nvme, dict):
                        nvme = nvme.get('value')
                    if isinstance(nvme, (int, float)) and nvme > 150:
                        nvme -= 273.15
                    temperature = self._bounded_temperature(nvme)
            except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
                pass
            with self._smart_lock:
                self._smart_cache[name] = {'temperature': temperature, 'checked_at': time.monotonic()}

    @staticmethod
    def _bounded_temperature(value):
        if isinstance(value, str):
            match = re.match(r'\s*(-?\d+(?:\.\d+)?)', value)
            value = float(match.group(1)) if match else None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        result = float(value)
        return round(result, 1) if -20 <= result <= 150 else None

    def snapshot(self, cid):
        hw = self.scan()
        channel = next((c for c in hw['pwm_channels'] if c['id'] == cid), None)
        if (not channel or channel.get('ignored') or channel['pwm'] is None or channel['enable'] is None
                or not 0 <= channel['pwm'] <= 255 or not 0 <= channel['enable'] <= 5):
            raise HardwareError('通道不可用或无法读取原始状态')
        if not channel['writable']:
            raise HardwareError('通道不可写，请检查驱动和应用权限')
        return {'pwm': channel['pwm'], 'enable': channel['enable']}

    def write(self, cid, value=None, enable=None):
        # Re-scan every write to reject removed/replaced devices and arbitrary paths.
        if cid in self.ignored_pwm_ids:
            raise HardwareError('此 PWM 接口已忽略，不能读取或控制')
        self.scan()
        if self.demo:
            if cid not in self._sim:
                raise HardwareError('未知控制通道')
            if value is not None:
                self._sim[cid]['pwm'] = value
            if enable is not None:
                self._sim[cid]['enable'] = enable
            return
        paths = self._paths.get(cid)
        if not paths:
            raise HardwareError('控制设备已断开')
        try:
            if enable is not None:
                if not isinstance(enable, int) or not 0 <= enable <= 5:
                    raise HardwareError('无效 PWM 模式')
                paths[1].write_text(str(enable))
            if value is not None:
                if not isinstance(value, int) or not 0 <= value <= 255:
                    raise HardwareError('无效 PWM 数值')
                paths[0].write_text(str(value))
        except OSError as exc:
            raise HardwareError('写入风扇控制失败：' + str(exc)) from exc

    def set_percent(self, cid, percent):
        if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not 25 <= percent <= 100:
            raise HardwareError('风扇速度必须在 25% 至 100% 之间')
        self.snapshot(cid)  # Reject unknown/unwritable channels before attempting any mode write.
        self.write(cid, enable=1)
        target = round(percent * 255 / 100)
        self.write(cid, value=target)
        actual = self.snapshot(cid)
        # Some hwmon drivers report pwm_enable=0 when the duty is at the
        # driver's full-speed value, even after a manual write. Accept that
        # full-speed representation only when PWM itself reads back at the
        # requested maximum; all other mismatches still trigger rollback.
        full_speed_readback = target == 255 and actual['pwm'] == 255 and actual['enable'] == 0
        if (actual['enable'] != 1 and not full_speed_readback) or actual['pwm'] != target:
            raise HardwareError(
                '驱动读回不一致：请求 PWM {} / 手动模式 1，实际 PWM {} / 模式 {}'.format(
                    target, actual['pwm'], actual['enable']))

    def restore(self, cid, snapshot):
        # Restore the exact captured state, including a previously low manual value.
        self.write(cid, enable=1)
        self.write(cid, value=snapshot['pwm'])
        self.write(cid, enable=snapshot['enable'])
        actual = self.snapshot(cid)
        if actual['enable'] != snapshot['enable'] or (snapshot['enable'] == 1 and actual['pwm'] != snapshot['pwm']):
            raise HardwareError('驱动未恢复到原始状态，已保留恢复记录')
