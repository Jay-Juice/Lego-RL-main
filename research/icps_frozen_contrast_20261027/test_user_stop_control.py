import json,pathlib,tempfile,types,unittest
from unittest.mock import patch
import run_after_user_stop as q

class UserStopGuard(unittest.TestCase):
    def exercise(self,exit_code='1',proof=True,wrong_run=False,apps='',free=300*1024**3):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d);run=p/'run';run.mkdir()
            if exit_code is not None:(run/'exit').write_text(exit_code)
            if proof:(p/'USER_STOP_CONFIRMED.json').write_text(json.dumps(dict(user_authorized_stop=True,run='wrong' if wrong_run else str(run),training_exit='1',stopped_pids=[])))
            with patch.object(q,'P',p),patch.object(q,'PROTECTED',run),patch.object(q.subprocess,'check_output',side_effect=[apps,'0\n'*8]),patch.object(q.subprocess,'run',return_value=types.SimpleNamespace(returncode=1)),patch.object(q.shutil,'disk_usage',return_value=types.SimpleNamespace(free=free)):
                return q.idle_reason()
    def test_running_training_blocks(self):self.assertEqual(self.exercise(exit_code=None),'protected_training_has_not_exited')
    def test_missing_stop_proof_rejects(self):
        with self.assertRaises(FileNotFoundError):self.exercise(proof=False)
    def test_wrong_run_rejects(self):
        with self.assertRaises(AssertionError):self.exercise(wrong_run=True)
    def test_wrong_exit_rejects(self):
        with self.assertRaises(AssertionError):self.exercise(exit_code='130')
    def test_authorized_stop_allows_idle(self):self.assertIsNone(self.exercise())
    def test_other_GPU_still_blocks(self):self.assertEqual(self.exercise(apps='12345'),'GPU_compute_process_present')
    def test_low_disk_still_blocks(self):self.assertEqual(self.exercise(free=100*1024**3),'disk_below_200GiB')

if __name__=='__main__':unittest.main(verbosity=2)
