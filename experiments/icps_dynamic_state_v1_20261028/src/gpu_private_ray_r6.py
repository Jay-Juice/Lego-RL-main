"""Probe-owned short Ray namespace and shared launch lease. Never global cleanup.

The probe starts Ray with address='local'; inspected Ray shutdown() terminates
only processes created by that local init. This module checks ownership and
leftovers, without sending any signal or removing directories/assets.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time

TAG = 'ICPS_R6_PROCESS_OWNER'


def check(condition, message):
    if not condition:
        raise RuntimeError('R6 private Ray: '+message)


def private_path(run, temp_root=Path('/tmp')):
    check(re.fullmatch(r'gpu-r6-[0-9a-f]{16}', run.name) is not None, 'invalid run name')
    return temp_root/('r6g-'+run.name.removeprefix('gpu-r6-'))


def validate_ray_namespace(config, run, temp_root=Path('/tmp')):
    value = config['ray_kwargs']['ray_init']
    expected = dict(address='local', namespace=run.name, _temp_dir=str(private_path(run, temp_root)),
                    include_dashboard=False, num_gpus=8)
    for key, wanted in expected.items():
        check(key in value and type(value[key]) is type(wanted) and value[key] == wanted,
              'wrong ray_init '+key)
    check(not value.get('ignore_reinit_error', False), 'reinitialization must fail')
    check(os.environ.get('RAY_ADDRESS') in (None, '', 'local'), 'external RAY_ADDRESS forbidden')


def process_start(pid):
    # Field22 is starttime; comm in parentheses can itself contain spaces.
    raw = (Path('/proc')/str(pid)/'stat').read_text()
    return int(raw.rsplit(')', 1)[1].split()[19])


def owned_processes(owner, proc_root=Path('/proc')):
    """Only output PID/start ticks/state for processes with our exact private tag."""
    found = []
    marker = (TAG+'='+owner['run']).encode()
    for process in proc_root.glob('[0-9]*'):
        try:
            pid = int(process.name)
            if pid == owner['pid'] or process.stat().st_uid != owner['uid']:
                continue
            raw = (process/'stat').read_text().rsplit(')', 1)[1].split()
            started = int(raw[19])
            # A process born before this owner cannot inherit this unique lease tag.
            # Do not inspect unrelated older environments; newer unreadable ones fail closed.
            if started < owner['start_ticks'] or raw[0] == 'Z':
                continue
            if marker not in (process/'environ').read_bytes().split(b'\0'):
                continue
            again = (process/'stat').read_text().rsplit(')', 1)[1].split()
            check(int(again[19]) == started, 'PID reused during ownership scan')
            raw = again
            if raw[0] != 'Z':
                found.append(dict(pid=pid, start_ticks=started, state=raw[0]))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return sorted(found, key=lambda row: row['pid'])


class PrivateRayLease:
    def __init__(self, run, *, temp_root=Path('/tmp'), lock_path=Path('/tmp/lego-ray-start.lock')):
        self.run = Path(run)
        self.temp = private_path(self.run, temp_root)
        self.lock_path = lock_path
        self.fd = None
        self.owner = None
        self.previous_tag = None

    def __enter__(self):
        check(self.run.is_dir() and self.run.resolve() == self.run, 'run directory missing or symlink')
        self.fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(self.fd)
            check(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(), 'foreign/nonregular launch lock')
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            check(self.temp.parent.resolve() == self.temp.parent, 'temporary parent symlink')
            self.temp.mkdir(mode=0o700)  # Existing directory/symlink is never reused.
            self.owner = dict(run=str(self.run), temporary_root=str(self.temp), uid=os.getuid(),
                pid=os.getpid(), start_ticks=process_start(os.getpid()),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), created_at=time.time())
            with (self.temp/'owner.json').open('x') as out:
                json.dump(self.owner, out, indent=2)
            with (self.run/'ray_owner.json').open('x') as out:
                json.dump(self.owner, out, indent=2)
            self.previous_tag = os.environ.get(TAG)
            check(self.previous_tag is None, 'nested/inherited ownership tag')
            os.environ[TAG] = str(self.run)
            return self
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise

    def verify_owner(self):
        check(self.temp.resolve() == self.temp, 'temporary namespace replaced')
        info = self.temp.stat()
        check(info.st_uid == self.owner['uid'] and stat.S_IMODE(info.st_mode) == 0o700, 'temporary owner/mode changed')
        check(json.loads((self.temp/'owner.json').read_text()) == self.owner, 'owner marker changed')
        check(json.loads((self.run/'ray_owner.json').read_text()) == self.owner, 'run owner marker changed')
        check(process_start(os.getpid()) == self.owner['start_ticks'], 'owner process identity changed')

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.verify_owner()
            remaining = owned_processes(self.owner)
            with (self.run/'ray_lifecycle_end.json').open('x') as out:
                json.dump(dict(owner=self.owner, ended_at=time.time(), body_failed=exc_type is not None,
                               owned_processes_remaining=remaining, global_cleanup=False,
                               directories_retained=True), out, indent=2)
            check(not remaining, 'owned processes remain after local Ray shutdown; manual diagnosis required')
        finally:
            if os.environ.get(TAG) == str(self.run):
                os.environ.pop(TAG)
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
        return False
