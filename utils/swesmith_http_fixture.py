"""Reuse the existing AL recorded public response; never synthesize assertions."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import socket
import subprocess
import time

SHA = '633c5b6acb69cf38d6ca4da7ea9b87c09040636c10c100f3be3ace3a6c606216'
NODE = 'tests/test_pyquery.py::TestWebScrappingEncoding::test_get'
SERVER = '''from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote
import sys
body = Path(sys.argv[1]).read_bytes()
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if unquote(self.path) != '/wiki/Заглавная_страница':
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=UTF-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
HTTPServer(('127.0.0.1', 80), Handler).serve_forever()
'''


@contextmanager
def recorded_http(config, tests):
    if NODE not in config['FAIL_TO_PASS'] + config['PASS_TO_PASS']:
        yield
        return
    body = tests/'http_fixture/ru-wikipedia-main.html'
    if hashlib.sha256(body.read_bytes()).hexdigest() != SHA:
        raise ValueError('Recorded HTTP response SHA mismatch')
    # Only this disposable task container is changed. No host mounts here.
    with Path('/etc/hosts').open('a') as f:
        f.write('\n127.0.0.1 ru.wikipedia.org\n')
    proc = subprocess.Popen(['/opt/miniconda3/envs/testbed/bin/python', '-c', SERVER, str(body)])
    try:
        for _ in range(50):
            if proc.poll() is not None:
                raise RuntimeError('Recorded HTTP server exited')
            try:
                with socket.create_connection(('127.0.0.1', 80), timeout=.1):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Recorded HTTP server did not start')
        yield
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
