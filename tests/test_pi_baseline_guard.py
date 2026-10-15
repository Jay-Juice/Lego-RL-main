import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from harbor_patch.privileged_state.container_capture import collect
from harbor_patch.privileged_state.structural_lift import build_snapshot


class BaselineGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.git('init', '-q')
        (self.root / 'f.py').write_text('def f():\n    return 1\n')
        (self.root / '.gitignore').write_text('ignored.txt\n')
        (self.root / 'removed.txt').write_text('baseline\n')
        self.git('add', '-A')
        self.git('-c', 'user.name=test', '-c', 'user.email=t@local', 'commit', '-qm', 'base')
        self.base = collect(str(self.root), preserve=True)
        self.observer = pathlib.Path(self.base['baseline_observer'])
        self.addCleanup(shutil.rmtree, self.observer)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE)

    def current(self):
        return collect(str(self.root), self.base['baseline_sha'], str(self.observer))

    def edits(self):
        (self.root / 'f.py').write_text('def f():\n    return 2\n')
        (self.root / 'new.py').write_text('new = 1\n')
        (self.root / 'ignored.txt').write_text('ignored\n')
        (self.root / 'removed.txt').unlink()

    def test_healthy_path_identical_and_no_actor_metadata_writes(self):
        self.edits()
        before = (self.root / '.git/index').read_bytes()
        original = collect(str(self.root), self.base['baseline_sha'])
        guarded = self.current()
        self.assertEqual(original['files'], guarded['files'])
        self.assertNotIn('baseline_observer_used', guarded)
        self.assertEqual(before, (self.root / '.git/index').read_bytes())

    def test_exact_actor_delete_and_reinit_preserves_net_delta(self):
        self.edits()
        expected = self.current()
        shutil.rmtree(self.root / '.git')
        self.git('init', '-q')
        config = (self.root / '.git/config').read_bytes()
        actual = self.current()
        self.assertTrue(actual['baseline_observer_used'])
        self.assertEqual(actual['baseline_sha'], self.base['baseline_sha'])
        self.assertEqual(expected['files'], actual['files'])
        self.assertEqual(build_snapshot(expected)['state_hash'], build_snapshot(actual)['state_hash'])
        self.assertEqual(config, (self.root / '.git/config').read_bytes())
        self.assertFalse((self.root / '.git/index').exists())

    def test_deleted_git_and_restore_still_empty(self):
        shutil.rmtree(self.root / '.git')
        self.assertEqual(self.current()['files'], [])
        self.assertFalse((self.root / '.git').exists())

    def test_identity_mismatch_fails_closed(self):
        shutil.rmtree(self.root / '.git')
        p = self.observer / 'pi_baseline.json'
        j = json.loads(p.read_text()); j['baseline_sha'] = '0' * 40
        p.write_text(json.dumps(j))
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
            self.current()

    def test_corrupt_observer_fails_closed(self):
        shutil.rmtree(self.root / '.git')
        for p in (self.observer / 'objects/pack').glob('*'):
            p.unlink()
        with self.assertRaises(RuntimeError):
            self.current()

    def test_unrelated_live_git_error_not_suppressed(self):
        (self.root / '.git/config').write_text('broken config [')
        with self.assertRaises(RuntimeError):
            self.current()
