"""Formal telemetry acceptance: exact source-only delta to native-tested R8."""
import ast,hashlib,json,pathlib,sys,inspect
N=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'runtime'),str(N/'core')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=(N/'runtime/ray_trainer.py').read_text()
 changes=[('old_log_prob_mfu = tu.get(output, "metrics")["mfu"]','old_log_prob_mfu = tu.get(output, "metrics").get("mfu")'),('actor_output["perf/mfu/actor"] = actor_output.pop("actor/mfu")','if "actor/mfu" in actor_output: actor_output["perf/mfu/actor"] = actor_output.pop("actor/mfu")'),('output["perf/mfu/critic"] = output.pop("critic/mfu")','if "critic/mfu" in output: output["perf/mfu/critic"] = output.pop("critic/mfu")')]
 baseline=source
 extra='                            if old_log_prob_mfu is None:\n                                old_log_prob_metrics.pop("perf/mfu/actor_infer")\n'
 assert baseline.count(extra)==1;baseline=baseline.replace(extra,'')
 for before,after in changes:assert baseline.count(after)==1;baseline=baseline.replace(after,before)
 old=N/'archive/before_formal_launch/runtime/ray_trainer.py'
 assert ast.dump(ast.parse(baseline))==ast.dump(ast.parse(old.read_text()))
 assert sha(old)=='9331dbb86f82d984c090e5bad561a03f8151df349fe56897d99e8a696c9eb127'
 import ray,torch
 from verl.trainer.ppo.ray_trainer import RayPPOTrainer
 assert pathlib.Path(inspect.getfile(RayPPOTrainer)).resolve()==N/'runtime/ray_trainer.py'
 # Formal entry retains original fit and native TaskRunner; no short-probe fit injection.
 import formal_main,full_launch_r8,full_private_ray_r8,gpu_private_ray_r6
 assert 'run_ppo(config)' in inspect.getsource(formal_main.main)
 assert 'gpu_probe_r6' not in inspect.getsource(full_launch_r8)
 a=inspect.getsource(full_private_ray_r8).replace('full-r8-','gpu-r6-').replace('r8f-','r6g-').replace('ICPS_R8_FORMAL_PROCESS_OWNER','ICPS_R6_PROCESS_OWNER').replace('R8 formal private Ray','R6 private Ray')
 assert a==inspect.getsource(gpu_private_ray_r6)
 assert not ray.is_initialized() and not torch.cuda.is_initialized()
 report=dict(passed=True,scope='CPU native imports and exact telemetry-only transformation of previously GPU-tested runtime',runtime_SHA=sha(N/'runtime/ray_trainer.py'),original_native_GPU_runtime_SHA=sha(old),all_nontelemetry_AST_unchanged=True,lease_namespace_only_change=True,native_fit_not_replaced=True,actual_GPU_test_repeated=False,optimizer_steps=0)
 with (N/'reports/FULL_CONTROLLER_R8.json').open('x') as f:json.dump(report,f,indent=2)
 print(json.dumps(report))
if __name__=='__main__':main()
