#!/usr/bin/env python3
"""Temporary Linux monitor-only integration check; a Python audit hook blocks sysfs writes."""
import argparse
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


def physical_state():
    result = {}
    for device in Path('/sys/class/hwmon').glob('hwmon*'):
        for pwm in device.glob('pwm*'):
            if not re.fullmatch(r'pwm\d+', pwm.name):
                continue
            try:
                result[str(pwm.resolve())] = {
                    'pwm': int(pwm.read_text()),
                    'enable': int(pwm.with_name(pwm.name + '_enable').read_text()),
                }
            except (OSError, ValueError):
                pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', type=Path, required=True)
    parser.add_argument('--require-pwm', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('This read-only check targets the Linux NAS.')
    entry = (args.app_dir / 'bin/server.py').resolve()
    before = physical_state()
    with tempfile.TemporaryDirectory(prefix='fan-studio-monitor-check-') as temporary:
        temp = Path(temporary)
        env = dict(os.environ, TRIM_PKGETC=str(temp / 'etc'), TRIM_PKGVAR=str(temp / 'var'),
                   FAN_DEMO='0', PYTHONDONTWRITEBYTECODE='1')
        wrapper = temp / 'audit-runner.py'
        wrapper.write_text('''import os, sys, runpy
def protect(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = os.fsdecode(args[0])
        if path.startswith('/sys/') and args[2] & (os.O_WRONLY | os.O_RDWR):
            print('SYSFS_WRITE_BLOCKED', path, file=sys.stderr, flush=True)
            raise PermissionError('Monitor check forbids sysfs writes')
sys.addaudithook(protect)
entry = ENTRY
sys.path.insert(0, os.path.dirname(entry))
sys.argv = [entry] + sys.argv[1:]
runpy.run_path(entry, run_name='__main__')
'''.replace('ENTRY', repr(str(entry))))
        password = secrets.token_urlsafe(24)
        with (temp / 'service.log').open('w+') as log:
            subprocess.run([sys.executable, str(wrapper), '--init-auth-stdin'], input=password,
                           text=True, env=env, stdout=log, stderr=log, check=True, timeout=15)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            base = 'http://127.0.0.1:' + str(port)
            process = subprocess.Popen([sys.executable, str(wrapper), '--host', '127.0.0.1',
                                        '--port', str(port)], env=env, stdout=log, stderr=log)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

            def request(path, body=None):
                data = None if body is None else json.dumps(body).encode()
                req = urllib.request.Request(base + path, data=data,
                    headers={'Content-Type': 'application/json', 'Origin': base})
                with opener.open(req, timeout=3) as response:
                    return json.load(response)

            try:
                deadline = time.monotonic() + 12
                while True:
                    try:
                        auth = request('/api/auth/status')
                        break
                    except OSError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            raise RuntimeError('Monitor service failed to start')
                        time.sleep(.1)
                assert not auth['setup_required'] and not auth['authenticated']
                request('/api/login', {'password': password})
                status = request('/api/status')
                hardware = request('/api/hardware')
                assert status['mode_summary'] == 'monitor'
                assert not status['demo']
                assert all(not c['owned'] and c['mode'] == 'monitor' for c in status['channels'])
                if args.require_pwm:
                    assert status['driver_available'] and status['channels'], 'No PWM outputs discovered'
                journal = json.loads((temp / 'var/owned-channels.json').read_text())
                assert journal['channels'] == {}
            finally:
                process.terminate()
                try:
                    process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                    raise RuntimeError('Monitor service did not stop gracefully')
            assert process.returncode == 0
            log.flush()
            log.seek(0)
            assert 'SYSFS_WRITE_BLOCKED' not in log.read(), 'A sysfs write was attempted'
        after = physical_state()
        assert set(before) == set(after), 'Hardware changed during the check'
        for cid, prior in before.items():
            assert after[cid]['enable'] == prior['enable'], 'PWM mode changed'
            if prior['enable'] == 1:
                assert after[cid]['pwm'] == prior['pwm'], 'Manual PWM value changed'
        print(json.dumps({
            'passed': True, 'kernel': os.uname().release,
            'mode': status['mode_summary'], 'pwm_channels': len(status['channels']),
            'fan_sensors': len(hardware['fans']),
            'temperature_sensors': len(hardware['temperature_sensors']),
            'system': status['system'], 'zero_sysfs_write_attempts': True,
            'pwm_modes_unchanged': True, 'manual_pwm_values_unchanged': True,
            'graceful_stop': True,
        }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
