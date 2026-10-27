"""CPU-only tests of the resource guard and statistics, not a GPU acceptance."""
import json,pathlib,tempfile,types,unittest
from unittest.mock import patch
import wait_and_run as queue
import summarize as report

class ResourceGuards(unittest.TestCase):
    def test_training_gate_never_queries_or_launches_gpu(self):
        with tempfile.TemporaryDirectory() as d, patch.object(queue,'PROTECTED',pathlib.Path(d)),patch.object(queue.subprocess,'check_output') as read,patch.object(queue.subprocess,'run') as launch:
            self.assertEqual(queue.idle_reason(),'protected_training_has_not_exited')
            read.assert_not_called();launch.assert_not_called()

    def test_failed_training_does_not_claim_gpu(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'exit').write_text('1')
            with patch.object(queue,'PROTECTED',root),patch.object(queue.subprocess,'check_output') as read:
                self.assertEqual(queue.idle_reason(),'protected_training_did_not_exit_successfully')
                read.assert_not_called()

    def check_idle(self,apps='',memory=None,ray=1,free=300*1024**3):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'exit').write_text('0')
            with patch.object(queue,'PROTECTED',root),patch.object(queue.subprocess,'check_output',side_effect=[apps,memory or '0\n'*8]),patch.object(queue.subprocess,'run',return_value=types.SimpleNamespace(returncode=ray)),patch.object(queue.shutil,'disk_usage',return_value=types.SimpleNamespace(free=free)):
                return queue.idle_reason()

    def test_external_gpu_blocks(self):self.assertEqual(self.check_idle(apps='1234'),'GPU_compute_process_present')
    def test_memory_blocks(self):self.assertEqual(self.check_idle(memory='2000\n'*8),'GPU_memory_not_idle')
    def test_ray_blocks(self):self.assertEqual(self.check_idle(ray=0),'Ray_present')
    def test_disk_blocks(self):self.assertEqual(self.check_idle(free=100*1024**3),'disk_below_200GiB')
    def test_all_idle_allows(self):self.assertIsNone(self.check_idle())

class Statistics(unittest.TestCase):
    def test_known_signal_repeat_and_observation_mask(self):
        import torch
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);out=root/'forward_step20';out.mkdir()
            (root/'CACHE_FULL_RECEIPT.json').write_text(json.dumps({'selected':2}))
            for rank in range(8):(out/f'complete_rank{rank}.json').write_text('{"passed":true}')
            for i in range(2):
                vals={}
                for condition in ['true','neutral','wrong','history']:
                    value=float(i) if condition=='true' else .5
                    for repeat in [0,1]:vals[f'{condition}_{repeat}']=torch.tensor([value,999.,value,value])
                torch.save(dict(selection_key=str(i),family=str(i),reward=i,response_mask=torch.tensor([1,0,1,1]),values=vals),out/f'row_{i:03d}.pt')
            with patch.object(report,'P',root):r=report.summarize_step(20)
            self.assertEqual(r['conditions']['true']['mse'],0.)
            self.assertEqual(r['conditions']['true']['task_AUC'],1.)
            self.assertEqual(r['conditions']['neutral']['task_AUC'],.5)
            self.assertEqual(r['conditions']['true']['repeat_MAE'],0.)
            self.assertEqual(r['contrasts']['wrong']['mse']['mean_control_minus_true'],.25)

if __name__=='__main__':unittest.main(verbosity=2)
