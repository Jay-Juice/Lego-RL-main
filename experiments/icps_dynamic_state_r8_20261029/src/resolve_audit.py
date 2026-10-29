"""Compare every real expanded Hydra argument and compose both full configs."""
import ast,hashlib,json,os,pathlib,shlex,subprocess,sys
from hydra import compose,initialize_config_dir
from omegaconf import OmegaConf
F=pathlib.Path(__file__).resolve().parents[1];B=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main');R=B/'experiments/pi_repair_state_v2_20261015'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tokens(path):
    lines=path.read_text().splitlines();cmd=next(x for x in lines if x.startswith(str(B/'.venv/bin/python')) and ' -m ' in x)
    args=shlex.split(cmd);return args,[x for x in args if '=' in x and not x.startswith('--')]
def norm(x):
    if isinstance(x,str) and x.startswith('/'):
        p=pathlib.Path(x)
        return str(p.resolve()) if p.exists() else x
    if isinstance(x,dict):return {k:norm(v) for k,v in x.items()}
    if isinstance(x,list):return [norm(v) for v in x]
    return x
def flat(d,p=''):
    if not isinstance(d,dict):return {p:d}
    out={}
    for k,v in d.items():out.update(flat(v,p+'.'+k if p else k))
    return out
def main():
    actual,overrides=tokens(F/('preflight/dryrun'+os.environ.get('ICPS_PREFLIGHT_SUFFIX','')+'.log'))
    historical,baseoverrides=tokens(B/'logs/sao_b64_w32_v6_20260930d_launcher.log')
    # Use each actual deployed config tree, not a hand-made list of expected defaults.
    with initialize_config_dir(config_dir=str(R/'src/verl_patch/config'),version_base=None):cfg=compose(config_name='lego_rl_sync.yaml',overrides=overrides)
    with initialize_config_dir(config_dir=str(B/'src/verl_patch/config'),version_base=None):bcfg=compose(config_name='lego_rl_sync.yaml',overrides=baseoverrides)
    a=OmegaConf.to_container(cfg,resolve=True);b=OmegaConf.to_container(bcfg,resolve=True)
    original_a=flat(a);original_b=flat(b);aa=flat(norm(a));bb=flat(norm(b))
    allow={'trainer.experiment_name','trainer.default_local_dir','trainer.resume_mode','actor_rollout_ref.rollout.agent.agent_loop_config_path',
           'trainer.episode_log_dir','actor_rollout_ref.rollout.trace.experiment_name'}
    diffs=[];unexpected=[]
    for key in sorted(set(aa)|set(bb)):
        if aa.get(key)!=bb.get(key):
            diff=dict(key=key,baseline=original_b.get(key),formal=original_a.get(key));diffs.append(diff)
            if key not in allow:unexpected.append(diff)
    # Agent YAML must be functionally identical (paths may differ, hashes may not).
    pa=pathlib.Path(a['actor_rollout_ref']['rollout']['agent']['agent_loop_config_path']);pb=pathlib.Path(b['actor_rollout_ref']['rollout']['agent']['agent_loop_config_path'])
    assert sha(pa)==sha(pb),'agent/scaffold YAML changed from historical baseline'
    assert not unexpected,json.dumps(unexpected)
    assert a['data']['train_batch_size']==64 and a['trainer']['total_epochs']==1 and a['trainer']['total_training_steps'] is None
    assert a['trainer']['critic_warmup']==20 and a['trainer']['save_freq']==10 and a['trainer']['test_freq']==0
    assert a['actor_rollout_ref']['actor']['ppo_max_token_len_per_gpu']==14336
    assert a['critic']['ppo_max_token_len_per_gpu']==20480
    assert a['actor_rollout_ref']['actor']['optim']['lr']==1e-6 and a['critic']['optim']['lr']==5e-6
    assert a['actor_rollout_ref']['actor']['ppo_epochs']==1 and a['critic']['ppo_epochs']==2
    assert a['actor_rollout_ref']['actor']['veomni']['ulysses_parallel_size']==8 and a['critic']['veomni']['ulysses_parallel_size']==8
    assert a['critic']['veomni']['freeze_param_patterns']==['self_attn.','linear_attn.','visual.']
    # Audit the historical ACTUAL resume20 command separately. Only packing
    # budgets switch at21; compare every other resolved configuration field.
    resume_cmd,resume_args=tokens(B/'logs/sao_b64_resume20_tokens_20261001_launcher.log')
    with initialize_config_dir(config_dir=str(B/'src/verl_patch/config'),version_base=None):rcfg=compose(config_name='lego_rl_sync.yaml',overrides=resume_args)
    resumed=OmegaConf.to_container(rcfg,resolve=True)
    phase2=OmegaConf.create(a)
    phase2.actor_rollout_ref.actor.ppo_max_token_len_per_gpu=16384
    phase2.critic.ppo_max_token_len_per_gpu=45056
    # The deprecated forward field interpolates training; actual unified engine
    # uses CriticConfig.ppo_infer_max_token_len_per_gpu (native default32768).
    resolved_phase2=OmegaConf.to_container(phase2,resolve=True)
    assert resumed['actor_rollout_ref']['actor']['ppo_max_token_len_per_gpu']==16384
    assert resumed['critic']['ppo_max_token_len_per_gpu']==45056
    for expanded in [a,resumed]:
        assert expanded['critic']['forward_max_token_len_per_gpu']==expanded['critic']['ppo_max_token_len_per_gpu']
        assert expanded['actor_rollout_ref']['rollout']['log_prob_max_token_len_per_gpu']==14336
        assert expanded['actor_rollout_ref']['ref']['log_prob_max_token_len_per_gpu']==14336
    from verl.utils.config import omega_conf_to_dataclass
    for c in [cfg.critic,rcfg.critic]:
        assert omega_conf_to_dataclass(c).ppo_infer_max_token_len_per_gpu==32768
    # resolved a has flattened interpolations: explicitly set the equivalent
    # native inference budget alongside training packing for phase2 comparison.
    resolved_phase2['critic']['forward_max_token_len_per_gpu']=45056
    laterdiff=[];laterbad=[]
    f2=flat(norm(resolved_phase2));fr=flat(norm(resumed))
    for key in sorted(set(f2)|set(fr)):
        if f2.get(key)!=fr.get(key):
            d=dict(key=key,formal=f2.get(key),historical_resume=fr.get(key));laterdiff.append(d)
            if key not in allow:laterbad.append(d)
    assert not laterbad,json.dumps(laterbad)
    # Full native checkpoint schema remains unchanged.

    for role in [a['actor_rollout_ref']['actor'],a['critic']]:
        assert set(role['checkpoint']['save_contents'])>={'model','optimizer','extra'}
        assert not role['checkpoint'].get('async_save',False)
    out=dict(passed=True,baseline='actual fresh v6d launcher 20260930d, steps1-20',baseline_command=historical,formal_command=actual,
        config_diff=diffs,unexpected_differences=unexpected,baseline_YAML_SHA=sha(pb),formal_YAML_SHA=sha(pa),full_horizon=97,epoch=1,train_rows=6248,
        phase21_97=dict(historical_command=resume_cmd,config_diff=laterdiff,unexpected=laterbad,actor_train=16384,critic_train=45056,critic_infer=32768,actor_logprob=14336,ref_logprob=14336),complete_actual_config=a,complete_baseline_config=b)
    with (F/('preflight/FULL_BASELINE_PARITY'+os.environ.get('ICPS_PREFLIGHT_SUFFIX','')+'.json')).open('x') as f:json.dump(out,f,indent=2,default=str)
    print(json.dumps(dict(passed=True,differences=diffs,full_horizon=97,actor_budget_first20=14336,critic_budget_first20=20480,phase21_97_differences=laterdiff)))
if __name__=='__main__':main()
