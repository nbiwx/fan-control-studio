#!/usr/bin/env python3
"""风栖：标准库 FPK 服务，持久保存用户选择的 FAN 模式。"""
import argparse
import atexit
import hashlib
import hmac
import ipaddress
import json
import logging
import mimetypes
import os
from pathlib import Path
import secrets
import signal
import sys
import socket
import threading
import time
from collections import OrderedDict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit
from controller import Controller, atomic_json, load_json
from hardware import Hardware, HardwareError

COOKIE = 'fan_studio_session'
SESSION_AGE = 8 * 3600
MAX_BODY = 65536
try:
    APP_VERSION = (Path(__file__).with_name('version.txt')).read_text(encoding='ascii').strip()
except OSError:
    APP_VERSION = 'unknown'


class Auth:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.sessions = {}
        self.attempts = OrderedDict()
        self.record = load_json(self.path, None)
        if self.record is not None:
            if not isinstance(self.record, dict) or set(self.record) != {'salt', 'hash'}:
                raise ValueError('认证配置损坏；拒绝启动以保护控制接口')
            try:
                if len(bytes.fromhex(self.record['salt'])) != 16 or len(bytes.fromhex(self.record['hash'])) != 64:
                    raise ValueError('无效密码摘要')
            except (TypeError, ValueError) as exc:
                raise ValueError('认证配置损坏') from exc

    @staticmethod
    def digest(password, salt):
        return hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=64).hex()

    @staticmethod
    def validate_password(password):
        if not isinstance(password, str) or not 10 <= len(password) <= 128:
            raise ValueError('密码长度需要为 10 至 128 个字符')

    def rate_limit(self, address):
        now = time.monotonic()
        with self.lock:
            entries = self.attempts.setdefault(address, deque())
            while entries and entries[0] < now - 60:
                entries.popleft()
            if len(entries) >= 8:
                return False
            entries.append(now)
            self.attempts.move_to_end(address)
            while len(self.attempts) > 256:
                self.attempts.popitem(last=False)
            return True

    def setup(self, password):
        self.validate_password(password)
        with self.lock:
            if self.record is not None:
                raise ValueError('管理员密码已经设置')
            salt = secrets.token_hex(16)
            record = {'salt': salt, 'hash': self.digest(password, salt)}
            atomic_json(self.path, record)
            self.record = record

    def verify(self, password):
        if not isinstance(password, str) or len(password) > 128:
            return False
        with self.lock:
            if self.record is None:
                return False
            return hmac.compare_digest(self.digest(password, self.record['salt']), self.record['hash'])

    def create(self):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.lock:
            now = time.time()
            self.sessions = {k: v for k, v in self.sessions.items() if v['expires'] > now}
            if len(self.sessions) >= 32:
                oldest = min(self.sessions, key=lambda k: self.sessions[k]['expires'])
                del self.sessions[oldest]
            self.sessions[token] = {'csrf_token': csrf, 'expires': now + SESSION_AGE}
        return token, csrf

    def session(self, token):
        with self.lock:
            entry = self.sessions.get(token)
            if entry and entry['expires'] > time.time():
                return dict(entry)
            self.sessions.pop(token, None)
            return None

    def remove(self, token):
        with self.lock:
            self.sessions.pop(token, None)


class FanServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, controller, auth, static):
        self.controller, self.auth, self.static = controller, auth, Path(static).resolve()
        self.slots = threading.BoundedSemaphore(24)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = 'FanStudio/1.0'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, fmt, *args):
        # Neither passwords nor session identifiers are logged.
        logging.info('%s %s', self.client_address[0], fmt % args)

    def token(self):
        try:
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            return cookie[COOKIE].value if COOKIE in cookie else ''
        except Exception:
            return ''

    def host_allowed(self):
        host = self.headers.get('Host', '')
        try:
            parsed = urlsplit('http://' + host)
            hostname = parsed.hostname
            if not hostname or parsed.username or parsed.password or parsed.path:
                return False
            allowed = {'localhost', socket.gethostname().lower(), socket.getfqdn().lower()}
            allowed.update(x.strip().lower() for x in os.getenv('FAN_ALLOWED_HOSTS', '').split(',') if x.strip())
            if hostname.lower() in allowed:
                return True
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False

    def origin_allowed(self):
        origin = self.headers.get('Origin', '')
        try:
            parsed = urlsplit(origin)
            return (parsed.scheme in ('http', 'https') and parsed.netloc.lower() == self.headers.get('Host', '').lower()
                    and not parsed.path and not parsed.query and not parsed.fragment)
        except ValueError:
            return False

    def response(self, code, value, cookie=None):
        data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(code)
        self.security_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(data)

    def security_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")

    def error(self, status, message, code):
        self.response(status, {'ok': False, 'error': message, 'code': code})

    def json_body(self):
        if self.headers.get('Transfer-Encoding'):
            raise ValueError('不支持分块请求')
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            raise ValueError('请求类型必须为 application/json')
        try:
            length = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            raise ValueError('无效请求长度')
        if not 0 < length <= MAX_BODY:
            raise ValueError('请求内容为空或过大')
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValueError('请求不完整')
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError('请求内容必须为对象')
        return body

    def do_GET(self):
        if not self.host_allowed():
            return self.error(403, '请求主机不被允许', 'invalid_host')
        path = urlsplit(self.path).path
        auth = self.server.auth
        session = auth.session(self.token())
        if path == '/api/auth/status':
            result = {'ok': True, 'setup_required': auth.record is None, 'authenticated': bool(session),
                      'demo': self.server.controller.hardware.demo}
            if session:
                result['csrf_token'] = session['csrf_token']
            return self.response(200, result)
        if path.startswith('/api/'):
            if not session:
                return self.error(401, '请先设置密码或登录', 'unauthorized')
            controller = self.server.controller
            with controller.lock:
                if path == '/api/status':
                    result = controller.status()
                    result['version'] = APP_VERSION
                    return self.response(200, result)
                if path == '/api/hardware':
                    return self.response(200, controller.hardware.scan())
                if path == '/api/config':
                    return self.response(200, {'ok': True, 'config': controller.config})
                if path == '/api/history':
                    raw_minutes = parse_qs(urlsplit(self.path).query).get('minutes', ['30'])[-1]
                    try:
                        minutes = int(raw_minutes)
                    except (TypeError, ValueError):
                        return self.error(400, '历史范围只支持 5 或 30 分钟', 'invalid_history_range')
                    if minutes not in (5, 30):
                        return self.error(400, '历史范围只支持 5 或 30 分钟', 'invalid_history_range')
                    history = list(controller.history)
                    available_span_seconds = max(0, history[-1]['time'] - history[0]['time']) if len(history) > 1 else 0
                    cutoff = time.time() - minutes * 60
                    items = [item for item in history if item['time'] >= cutoff]
                    return self.response(200, {'ok': True, 'items': items,
                                               'available_span_seconds': available_span_seconds,
                                               'minutes': minutes})
                if path == '/api/logs':
                    return self.response(200, {'ok': True, 'items': list(controller.logs)})
            return self.error(404, '接口不存在', 'not_found')
        try:
            name = unquote(path).lstrip('/') or 'index.html'
            if name.startswith('static/'):
                name = name[len('static/'):]
            if not name:
                return self.error(404, '文件不存在', 'not_found')
            target = (self.server.static / name).resolve()
            if target != self.server.static and self.server.static not in target.parents:
                return self.error(404, '文件不存在', 'not_found')
            if not target.is_file():
                return self.error(404, '文件不存在', 'not_found')
            data = target.read_bytes()
            self.send_response(200)
            self.security_headers()
            self.send_header('Content-Type', (mimetypes.guess_type(str(target))[0] or 'application/octet-stream') + ('; charset=utf-8' if target.suffix in ('.html', '.css', '.js', '.svg') else ''))
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(data)
        except (OSError, ValueError):
            return self.error(404, '文件不存在', 'not_found')

    def do_POST(self):
        if not self.host_allowed() or not self.origin_allowed():
            return self.error(403, '请求来源不被允许', 'invalid_origin')
        path = urlsplit(self.path).path
        auth = self.server.auth
        token = self.token()
        session = auth.session(token)
        try:
            if path in ('/api/setup', '/api/login'):
                if not auth.rate_limit(self.client_address[0]):
                    return self.error(429, '尝试次数过多，请一分钟后重试', 'rate_limited')
                body = self.json_body()
                if set(body) != {'password'}:
                    raise ValueError('请求只能包含 password')
                if path == '/api/setup':
                    auth.setup(body['password'])
                elif not auth.verify(body['password']):
                    return self.error(401, '密码错误', 'invalid_credentials')
                token, csrf = auth.create()
                cookie = COOKIE + '=' + token + '; Path=/; HttpOnly; SameSite=Strict; Max-Age=' + str(SESSION_AGE)
                return self.response(200, {'ok': True, 'csrf_token': csrf}, cookie)
            if not session:
                return self.error(401, '请先登录', 'unauthorized')
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), session['csrf_token']):
                return self.error(403, '安全令牌不正确，请刷新页面', 'csrf_failed')
            if path == '/api/logout':
                auth.remove(token)
                return self.response(200, {'ok': True}, COOKIE + '=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0')
            body = self.json_body()
            if path == '/api/pwm-test':
                return self.response(200, self.server.controller.pwm_test_control(body))
            if path == '/api/control':
                return self.response(200, self.server.controller.control(body))
            if path == '/api/release':
                if not isinstance(body, dict) or set(body) not in (set(), {'id'}, {'pwm_id'}):
                    raise ValueError('无效释放请求')
                if 'pwm_id' in body:
                    result = self.server.controller.release_pending(body['pwm_id'])
                elif 'id' in body:
                    result = self.server.controller.release_fan(body['id'])
                else:
                    result = self.server.controller.release()
                return self.response(200, result)
            if path == '/api/config':
                return self.response(200, {'ok': True, 'config': self.server.controller.update_config(body)})
            return self.error(404, '接口不存在', 'not_found')
        except (ValueError, UnicodeError) as exc:
            self.error(400, str(exc), 'invalid_request')
        except HardwareError as exc:
            self.error(409, str(exc), 'hardware_error')
        except OSError as exc:
            logging.error('Persistent or hardware operation failed: %s', exc)
            self.error(500, '配置保存或硬件操作失败，请查看日志', 'operation_failed')

    def do_OPTIONS(self):
        self.error(405, '不允许跨域请求', 'method_not_allowed')


def main():
    parser = argparse.ArgumentParser(description='风栖风扇控制服务')
    parser.add_argument('--host', default=os.environ.get('FAN_HOST', '0.0.0.0'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('FAN_PORT', '18791')))
    parser.add_argument('--demo', action='store_true', default=os.getenv('FAN_DEMO') == '1')
    parser.add_argument('--init-auth-stdin', action='store_true', help='Initialize auth.json from stdin without starting hardware services')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    base = Path(__file__).resolve().parent.parent
    etc = Path(os.getenv('TRIM_PKGETC', str(base / 'etc')))
    state = Path(os.getenv('TRIM_PKGVAR', str(base / 'var')))
    etc.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.init_auth_stdin:
        auth = Auth(etc / 'auth.json')
        if auth.record is None:
            password = sys.stdin.read(1025)
            auth.setup(password)
            logging.info('Admin credentials initialized')
        else:
            logging.info('Existing admin credentials preserved')
        return
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Prevent two processes from owning and restoring the same physical channels.
    import fcntl
    lock_file = open(state / 'server.lock', 'a')
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('风栖已在运行，拒绝启动第二个控制进程')
    auth = Auth(etc / 'auth.json')
    controller = Controller(Hardware(os.getenv('FAN_HWMON_ROOT', '/sys/class/hwmon'), args.demo), etc, state)
    atexit.register(controller.shutdown)
    server = None
    try:
        server = FanServer((args.host, args.port), controller, auth, Path(__file__).resolve().parent / 'static')
        stopping = threading.Event()

        def stop(signum, frame):
            if stopping.is_set():
                return
            stopping.set()
            controller.shutdown()
            threading.Thread(target=server.shutdown, daemon=True).start()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        controller.start()
        logging.info('风栖服务监听 %s:%s；演示模式=%s；启动时恢复已保存的 FAN 设置', args.host, args.port, args.demo)
        server.serve_forever(poll_interval=0.3)
    finally:
        controller.shutdown()
        if server is not None:
            server.server_close()
        lock_file.close()


if __name__ == '__main__':
    main()
