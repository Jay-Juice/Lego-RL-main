"""Formal native full-horizon SAO entrypoint. Only changes output namespace."""
import json,os,pathlib
import hydra
from omegaconf import OmegaConf,open_dict
from verl.trainer.main_ppo import run_ppo
@hydra.main(config_path=None,config_name='lego_rl_sync',version_base=None)
def main(config):
    assert os.environ.get('ICPS_V11_OVERLAY_ACTIVE')=='1'
    root=pathlib.Path(os.environ['ICPS_FORMAL_RUN_DIR'])
    with open_dict(config):config.trainer.default_local_dir=os.environ['ICPS_CHECKPOINT_ROOT']
    assert config.data.train_batch_size==64 and config.trainer.critic_warmup==20
    assert config.trainer.total_epochs==1 and config.trainer.total_training_steps is None
    assert config.trainer.resume_mode=='disable'
    assert config.actor_rollout_ref.actor.ppo_mini_batch_size==64 and config.critic.ppo_mini_batch_size==64
    assert config.critic.ppo_epochs==2 and config.actor_rollout_ref.actor.ppo_epochs==1
    assert config.trainer.save_freq==10 and config.trainer.test_freq==0
    cfg=OmegaConf.to_container(config,resolve=True)
    if os.environ.get('ICPS_CONFIG_ONLY')=='1':
        (root/'resolved_prelaunch.json').write_text(json.dumps(cfg,indent=2,default=str));return
    with (root/'resolved_actual.json').open('x') as f:json.dump(cfg,f,indent=2,default=str)
    run_ppo(config)
    # No artificial stop at20: a normal successful return must be full97.
    from formal_completion import verify_complete
    evidence=verify_complete(config)
    with (root/'DRIVER_COMPLETED.json').open('x') as f:json.dump(evidence,f,indent=2)
if __name__=='__main__':main()
