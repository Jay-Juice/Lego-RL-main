"""Validation-only worker instrumentation; never used by formal training."""
import hashlib
import json
import os
from pathlib import Path

import hydra
import ray
import torch
from verl.single_controller.base.decorator import Dispatch, register
from verl.workers.engine_workers import TrainingWorker
from verl.trainer.main_ppo import TaskRunner, run_ppo
from verl.trainer.ppo.ray_trainer import RayPPOTrainer, Role
from verl_patch.pi_v2_acceptance import fixture, metrics, batch_digest


def summarize(value):
    if isinstance(value, torch.Tensor):
        t = value.detach()
        if hasattr(t, 'to_local'): t = t.to_local()
        t = t.contiguous().cpu()
        flat = t.reshape(-1)
        if flat.numel() > 1024:
            # Integer arithmetic avoids float32 rounding an endpoint up to numel
            # for large embedding matrices (>2**24 elements).
            flat = flat[torch.arange(1024, dtype=torch.int64) * (flat.numel()-1) // 1023]
        raw = flat.contiguous().view(torch.uint8).numpy().tobytes()
        return {'shape': list(t.shape), 'dtype': str(t.dtype), 'sample_sha256': hashlib.sha256(raw).hexdigest(),
                'scalar': t.item() if t.numel()==1 else None}
    if isinstance(value, dict): return {str(k): summarize(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [summarize(x) for x in value]
    if isinstance(value, (str,int,float,bool)) or value is None: return value
    return str(value)


class DiagnosticCritic(TrainingWorker):
    @register(dispatch_mode=Dispatch.ONE_TO_ALL)
    def audit_optimizer(self):
        torch.cuda.synchronize()
        e=self.engine
        names={id(p):n for n,p in e.module.named_parameters()}
        groups=[{k: ([names.get(id(p),'UNBOUND') for p in v] if k=='params' else summarize(v))
                 for k,v in g.items()} for g in e.optimizer.param_groups]
        return {'rank':self.rank,'optimizer_class':str(type(e.optimizer)),
            'model':{n:summarize(p) for n,p in e.module.named_parameters()},
            'optimizer':{names.get(id(p),'UNBOUND'):summarize(s) for p,s in e.optimizer.state.items()},
            'groups':groups,'scheduler':summarize(e.lr_scheduler.state_dict())}


class DiagnosticRunner(TaskRunner):
    def add_critic_worker(self, config):
        self.role_worker_mapping[Role.Critic]=ray.remote(DiagnosticCritic)
        self.mapping[Role.Critic]='global_pool'

    def run(self, config):
        original=RayPPOTrainer.fit
        def diagnostic(trainer):
            out=Path(os.environ['PI_DIAGNOSTIC_DIR']);out.mkdir(exist_ok=False)
            def save(name,value):
                with (out/(name+'.json')).open('x') as f:json.dump(value,f,indent=2)
            def stage(name):print('PI_RESUME_DIAGNOSTIC',name,flush=True)
            trainer.global_steps=0
            stage('load_A');trainer._load_checkpoint()
            batch=fixture(trainer.tokenizer)
            values=trainer._compute_values(batch);batch=batch.union(values)
            batch_before=batch_digest(dict(batch.batch))
            a=trainer.critic_wg.audit_optimizer();save('state_A',a)
            stage('update_A');ma=metrics(trainer._update_critic(batch));save('metrics_A',ma)
            assert batch_digest(dict(batch.batch))==batch_before
            va=trainer._compute_values(batch).batch['values'].clone()
            save('state_after_A',trainer.critic_wg.audit_optimizer())
            stage('load_B');trainer._load_checkpoint()
            vb0=trainer._compute_values(batch).batch['values'].clone()
            torch.testing.assert_close(values.batch['values'],vb0,atol=1e-5,rtol=1e-5)
            b=trainer.critic_wg.audit_optimizer();save('state_B',b)
            save('pre_update_state_comparison',{'sampled_state_equal':a==b})
            stage('update_B');mb=metrics(trainer._update_critic(batch));save('metrics_B',mb)
            assert batch_digest(dict(batch.batch))==batch_before
            vb=trainer._compute_values(batch).batch['values'].clone()
            save('state_after_B',trainer.critic_wg.audit_optimizer())
            save('comparison',{'max_abs_difference':float((va-vb).abs().max()),'metrics_A':ma,'metrics_B':mb,
                'pre_update_sampled_state_equal':a==b,'scope':'two loads of retained checkpoint; diagnostic only'})
            stage('finished');trainer._shutdown_dump_executor()
        RayPPOTrainer.fit=diagnostic
        try:return super().run(config)
        finally:RayPPOTrainer.fit=original


@hydra.main(config_path='config',config_name='ppo_trainer',version_base=None)
def main(config):run_ppo(config,task_runner_class=ray.remote(num_cpus=1)(DiagnosticRunner))


if __name__=='__main__':main()
