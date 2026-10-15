"""Baseline-recipe GPU acceptance without checkpoint writes or resume claims."""
import json, os
from pathlib import Path
import hydra, ray, torch
from verl.trainer.main_ppo import TaskRunner, run_ppo
from verl.trainer.ppo.ray_trainer import RayPPOTrainer
from verl_patch.pi_gpu_smoke import short_batch
from verl_patch.pi_v2_acceptance import fixture, metrics, batch_digest

class TrainingAcceptanceRunner(TaskRunner):
    def run(self, config):
        destination=Path(os.environ['PI_TRAINING_ACCEPTANCE_RESULT'])
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists(): raise FileExistsError(destination)
        assert not os.environ.get('PI_WARMUP_CHECKPOINT_STEPS')
        assert os.environ.get('FLASH_ATTENTION_DETERMINISTIC','0')=='0'
        original=RayPPOTrainer.fit
        def acceptance(trainer):
            def stage(s):print('PI_NO_SAVE_ACCEPTANCE',s,flush=True)
            trainer.global_steps=0;trainer._load_checkpoint()
            assert trainer.global_steps==0
            trainer.checkpoint_manager.sleep_replicas()
            stage('empty_PI_matches_baseline')
            baseline=trainer._compute_values(short_batch(trainer.tokenizer,pi=False)).batch['values'].clone()
            empty=trainer._compute_values(short_batch(trainer.tokenizer,empty=True)).batch['values'].clone()
            torch.testing.assert_close(baseline,empty,atol=1e-5,rtol=1e-5)
            batch=fixture(trainer.tokenizer)
            preserved={k:v.clone() for k,v in batch.batch.items()}
            pi_before=batch_digest(batch.non_tensor_batch['pi_call_records'])
            stage('v2_values')
            values=trainer._compute_values(batch)
            assert torch.isfinite(values.batch['values']).all()
            batch=batch.union(values)
            stage('critic_update')
            critic=metrics(trainer._update_critic(batch))
            stage('actor_update')
            actor=metrics(trainer._update_actor(batch))
            for k,v in preserved.items():torch.testing.assert_close(v,batch.batch[k],atol=0,rtol=0)
            assert pi_before==batch_digest(batch.non_tensor_batch['pi_call_records'])
            assert not Path(config.trainer.default_local_dir).exists(),'Unexpected checkpoint output'
            result={'status':'passed','scope':'baseline-recipe forward/backward/update without checkpoint writes',
                'model':config.actor_rollout_ref.model.path,'sp_size':8,'logical_batch':64,
                'synthetic_trajectories':True,'checkpoint_saved':False,'checkpoint_loaded':False,
                'production_updates':0,'warmup_checkpoint_steps':[],
                'empty_pi_value_max_abs_diff':float((baseline-empty).abs().max()),
                'actor_tensors_unchanged':True,'pi_records_unchanged':True,
                'critic':critic,'actor':actor,'source_revision':os.environ['PI_SOURCE_REVISION'],
                'limits':['No efficacy or maximum-length stress claim.','Numerical repeatability diagnosis is separate and remains unresolved; no bitwise resume claim.']}
            with destination.open('x') as f:json.dump(result,f,indent=2)
            stage('PASSED');trainer._shutdown_dump_executor()
        RayPPOTrainer.fit=acceptance
        try:return super().run(config)
        finally:RayPPOTrainer.fit=original

@hydra.main(config_path='config',config_name='ppo_trainer',version_base=None)
def main(config):run_ppo(config,task_runner_class=ray.remote(num_cpus=1)(TrainingAcceptanceRunner))
if __name__=='__main__':main()
