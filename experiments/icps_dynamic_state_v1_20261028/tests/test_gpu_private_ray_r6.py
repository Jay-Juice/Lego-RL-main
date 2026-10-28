"""Linux CPU filesystem/process contracts; never starts Ray or allocates CUDA."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from gpu_private_ray_r6 import PrivateRayLease, TAG, private_path, validate_ray_namespace, owned_processes


class PrivateRayTests(unittest.TestCase):
    def setUp(self):
        self.area = tempfile.TemporaryDirectory()
        self.root = Path(self.area.name).resolve()
        self.run = self.root/'gpu-r6-0123456789abcdef'
        self.run.mkdir()
        self.temp_root = self.root/'tmp'
        self.temp_root.mkdir()
        self.lock = self.root/'shared.lock'

    def tearDown(self):
        self.area.cleanup()  # Only this test-created temporary fixture.

    def lease(self, run=None):
        return PrivateRayLease(run or self.run, temp_root=self.temp_root, lock_path=self.lock)

    def test_exclusive_lease_owner_and_retained_namespace(self):
        with self.lease() as first:
            first.verify_owner()
            other = self.root/'gpu-r6-fedcba9876543210'
            other.mkdir()
            with self.assertRaises(BlockingIOError):
                with self.lease(other):
                    self.fail('concurrent lease acquired')
        self.assertTrue(first.temp.is_dir())
        self.assertTrue(self.lock.is_file())
        self.assertNotIn(TAG, os.environ)
        end = json.loads((self.run/'ray_lifecycle_end.json').read_text())
        self.assertFalse(end['body_failed'])
        self.assertEqual(end['owned_processes_remaining'], [])
        with self.lease(other):
            pass

    def test_ray_shared_child_keeps_parent_private(self):
        with self.lease() as lease:
            child = lease.temp/'ray'
            child.mkdir()
            child.chmod(0o777)  # Actual Ray try_to_create_directory behavior.
            lease.verify_owner()
            self.assertEqual(lease.temp.stat().st_mode & 0o777, 0o700)
            self.assertEqual(child.stat().st_mode & 0o777, 0o777)

    def test_existing_tmp_and_symlink_refused(self):
        target = private_path(self.run, self.temp_root)
        target.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            with self.lease():
                pass
        self.assertTrue(target.is_symlink())

    def test_lock_symlink_refused(self):
        target = self.root/'unrelated.txt'
        target.write_text('preserve')
        self.lock.symlink_to(target)
        with self.assertRaises(OSError):
            with self.lease():
                pass
        self.assertEqual(target.read_text(), 'preserve')

    def test_body_failure_propagates_and_releases_lock(self):
        with self.assertRaisesRegex(ValueError, 'synthetic failure'):
            with self.lease():
                raise ValueError('synthetic failure')
        end = json.loads((self.run/'ray_lifecycle_end.json').read_text())
        self.assertTrue(end['body_failed'])
        self.assertNotIn(TAG, os.environ)
        other = self.root/'gpu-r6-fedcba9876543210'
        other.mkdir()
        with self.lease(other):
            pass

    def test_marker_tampering_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'owner marker changed'):
            with self.lease() as lease:
                (lease.temp/'owner.json').write_text('{}')
        self.assertNotIn(TAG, os.environ)

    def test_actual_owned_child_detection_without_signalling(self):
        with self.lease() as lease:
            env = dict(os.environ)
            child = subprocess.Popen([sys.executable, '-B', '-c',
                'import sys; print("ready",flush=True); sys.stdin.read()'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
            try:
                self.assertEqual(child.stdout.readline().strip(), 'ready')
                rows = owned_processes(lease.owner)
                self.assertEqual([r['pid'] for r in rows], [child.pid])
                self.assertIsNone(child.poll())
            finally:
                child.communicate('', timeout=10)  # EOF asks only our child to exit normally.
            self.assertEqual(child.returncode, 0)
            self.assertEqual(owned_processes(lease.owner), [])

    def test_old_process_environment_not_read_new_unknown_fails_closed(self):
        proc = self.root/'fake_proc'
        item = proc/'12345678'
        item.mkdir(parents=True)
        (item/'environ').mkdir()  # Unreadable as a byte stream, even for root.
        def stat_text(start):
            return '12345678 (fixture process) '+ ' '.join(['S']+['0']*18+[str(start)])
        (item/'stat').write_text(stat_text(99))
        owner = dict(run=str(self.run), pid=os.getpid(), uid=os.getuid(), start_ticks=100)
        self.assertEqual(owned_processes(owner, proc), [])
        (item/'stat').write_text(stat_text(100))
        with self.assertRaises(IsADirectoryError):
            owned_processes(owner, proc)

    def test_external_ray_and_wrong_namespace_rejected(self):
        cfg = {'ray_kwargs': {'ray_init': dict(address='local', namespace=self.run.name,
            _temp_dir=str(private_path(self.run, self.temp_root)/'ray'), include_dashboard=False, num_gpus=8)}}
        old = os.environ.pop('RAY_ADDRESS', None)
        try:
            validate_ray_namespace(cfg, self.run, self.temp_root)
            for key, value in [('address', 'auto'), ('namespace', 'other'), ('_temp_dir', '/tmp/ray'), ('_temp_dir', str(private_path(self.run, self.temp_root))),
                               ('num_gpus', 1), ('include_dashboard', True), ('ignore_reinit_error', True)]:
                changed = copy.deepcopy(cfg)
                changed['ray_kwargs']['ray_init'][key] = value
                with self.subTest(key=key), self.assertRaises(RuntimeError):
                    validate_ray_namespace(changed, self.run, self.temp_root)
            os.environ['RAY_ADDRESS'] = 'remote:6407'
            with self.assertRaises(RuntimeError):
                validate_ray_namespace(cfg, self.run, self.temp_root)
        finally:
            if old is None:
                os.environ.pop('RAY_ADDRESS', None)
            else:
                os.environ['RAY_ADDRESS'] = old


if __name__ == '__main__':
    unittest.main(verbosity=2)
