"""Final fail-closed admission. Creates a receipt, never starts Ray or training."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from prepare_full import resources

F=Path(__file__).resolve().parents[1]
B=Path('/media/ubuntu/D1/zsj/Lego-RL-main')
R=B/'experiments/pi_repair_state_v2_20261015'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ns=json.loads((F/'preflight/NAMESPACE.json').read_text())
    root=Path(ns['run']);checkpoint=Path(ns['checkpoint'])
    assert ns['source_root']==str(F) and not checkpoint.exists()
    assert not (root/'resolved_actual.json').exists(),'no launch may overwrite an attempt'
    res=resources()
    initial=json.loads((F/'preflight/RESOURCE_AND_SOURCE.json').read_text())
    assert res['free_bytes']>=initial['minimum_before_start_bytes']
    subprocess.run(['sha256sum','-c',str(F/'DEPLOYMENT.sha256')],cwd=F,check=True,stdout=subprocess.DEVNULL)
    for entry in json.loads((F/'runtime/SOURCE_DIFF_RECEIPT.json').read_text()).values():
        assert sha(R/entry['relative'])==entry['original_SHA'],'read-only production changed'
        assert sha(F/'runtime'/entry['file'])==entry['candidate_SHA']
    v11=R/'ops/icps_v11_window_20261023'
    assert sha(F/'src/window_serializer.py')==sha(v11/'src_r3/window_serializer.py')
    assert sha(F/'core/issue_program_state.py')=='4773d8aaefe99ad7ee37265fce05328d2d5f1c806ad012064fd5da5b0997493b'
    parity=json.loads((F/'preflight/FULL_BASELINE_PARITY_r3.json').read_text())
    assert parity['passed'] and not parity['unexpected_differences'] and not parity['phase21_97']['unexpected']
    config=parity['complete_actual_config'];trainer=config['trainer']
    assert trainer['total_training_steps'] is None and trainer['total_epochs']==1
    assert not trainer.get('val_only') and not trainer.get('val_before_train')
    assert trainer['resume_mode']=='disable' and trainer['critic_warmup']==20
    assert trainer['save_freq']==10 and trainer['test_freq']==0
    assert not trainer.get('remove_previous_ckpt_in_save',False)
    assert all(trainer.get(key) is None or trainer[key]>=9 for key in ['max_actor_ckpt_to_keep','max_critic_ckpt_to_keep'])
    env=(F/'ICPS_V11_FULL_LAUNCH_CONFIG.env').read_text()
    assert 'ICPS_PAUSE_AFTER_COMPLETED_STEP' not in env
    assert 'PI_WARMUP_CHECKPOINT_STEPS=\n' in env
    assert 'RAY_SCOPED_CLEANUP=1' in env
    assert not (F/'src/formal_pause.py').exists()
    unit=(F/'preflight/remote_full97_unit_r3.log').read_text()
    assert 'Ran 31 tests' in unit and unit.rstrip().endswith('OK')
    native=(F/'preflight/native_preflight_r3.log').read_text()
    assert 'all fatal checks passed' in native
    api=json.loads((F/'preflight/REAL_ENGINE_AUDIT_API_PROBE.json').read_text());assert api['passed'] and len(api['cases'])==12
    pool=json.loads((F/'preflight/REAL_FULL_POOL_CPU_PROBE.json').read_text())
    assert pool['passed'] and {x['mode'] for x in pool['rows']}=={'cached_prepared','native_local_build'}
    identity=json.loads((F/'preflight/FULL6248_DATA_IDENTITY.json').read_text())
    assert identity['rows']==6248 and sha(Path(identity['dataset']))==identity['SHA']
    model=Path(config['actor_rollout_ref']['model']['path'])
    weights=[p for p in model.glob('*.safetensors') if p.is_file()]
    assert weights and all(p.stat().st_size>0 for p in weights)
    source={p.relative_to(F).as_posix():sha(p) for d in ['src','runtime','core','tests'] for p in (F/d).rglob('*.py')}
    report=dict(status='PASSED_FULL97_CONTINUOUS',time=time.strftime('%Y-%m-%d %H:%M:%S %z'),namespace=ns,
        original_pause20_plan_superseded_by_explicit_user_full97_instruction=True,
        no_manual_pause=True,step20_native_full_save_then_automatic_step21=True,
        full_rows=6248,batches=97,batch_size=64,workers=32,SP=8,DP=1,critic_warmup=20,
        scheduler_horizon=97,native_optimizer_scheduler_unchanged=True,
        actual_packing=dict(steps1_20=dict(actor_train=14336,critic_train=20480),steps21_97=dict(actor_train=16384,critic_train=45056),
            all_steps=dict(critic_infer_native=32768,actor_logprob=14336,ref_logprob=14336)),
        save_steps=[20,30,40,50,60,70,80,90,97],native_ESI_emergency_save_retained=True,
        save_schema='8rank Actor and Critic each model/optim/extra_state plus data.pt, strict PI_COMPLETE and atomic latest marker',
        stopping='native final97 / native val_only disabled / exceptions; resource waits retained; no20 return or21 guard',
        PI=dict(method='frozen passed ICPSv1.1',initial_tokens=192,update_max_tokens=128,episode_tokens=4096,
            critic_only=True,actor_tokens_masks_logprob_routing_unchanged=True,no_Gold_or_new_verifier_or_reward=True,
            raw_workspace_RAM_only=True,normal_PI_log_code_text_and_ids=False),
        native_source_and_config_parity=parity['config_diff'],phase21_parity=parity['phase21_97'],
        data_manifest_SHA=sha(F/'preflight/FULL6248_DATA_IDENTITY.json'),dataset_SHA=identity['SHA'],
        images=dict(cached_prepared=identity['cached_prepared'],native_local_build=identity['native_local_build'],no_pull=True,manifest_SHA=sha(F/'preflight/FULL6248_PREPARED_IMAGES.json')),
        resources=res,minimum_before_start_bytes=initial['minimum_before_start_bytes'],
        disk_policy=dict(minimum_free_GiB=200,pre_save_bytes=189686470567+210*1024**3,no_deletion_or_partial_save=True,
            checkpoints_retained=9,estimated_checkpoint_total_GiB=9*189686470567/1024**3,
            completion_requires_user_managed_space=True),
        base_model=dict(path=str(model),small_metadata_SHA={p.name:sha(p) for p in model.glob('*.json') if p.stat().st_size<50*1024**2},
            weights_inventory={p.name:p.stat().st_size for p in weights},weights_full_hash_not_repeated=True),
        source_manifest_SHA=sha(F/'DEPLOYMENT.sha256'),source_SHA=source,env_SHA=sha(F/'ICPS_V11_FULL_LAUNCH_CONFIG.env'),
        native_launcher_SHA=sha(R/'scripts/train/train.sh'),
        backup=json.loads((F/'preflight/NEW_COPY_PROVENANCE.json').read_text()),
        unit_tests=31,real_engine_audit_API=api,real_pool_probe=pool,
        GPU_new_canary_repeated=False,prior_passed_v11_online_canary=str(v11/'CURRENT_RUNTIME.json'),
        scope_limit='CPU contract/preflight passed; actual long97 GPU success and bitwise restore are not yet demonstrated',
        no_step20_GPU_evaluation=True,training_started=False)
    with (F/'LAUNCH_PREFLIGHT.json').open('x') as h:json.dump(report,h,indent=2)
    md=f'''# ICPS v1.1 完整97步启动预检

状态：PASSED_FULL97_CONTINUOUS（尚未启动GPU训练）。

用户最新指令覆盖旧pause20计划。新独立源 `{F}`；原副本未修改，备份见 NEW_COPY_PROVENANCE.json。

完整6248数据、batch/mini64、workers32、SP8/DP1、1epoch97步，原生head/freeze/LR/优化器/GAE/reward不变。前19步Critic only，20首次Actor更新并完整保存，保存成功后自动21；正常30…90及97保存，无warmup10保存。total_training_steps不设20，原生optim horizon推导97。

历史实际packing：1–20 Actor14336/Critic20480；21–97 Actor16384/Critic45056。原生Critic inference实际32768，Actor/ref logprob14336均保持。通过原生TensorDict工程参数传递训练预算，未改loss或scheduler。全部真实展开配置与两阶段历史launcher逐字段比较通过，差异仅隔离路径/实验名/freshbase。

ICPS v1.1初始192、更新128、episode4096，仅Critic；selector SHA与已通过线上canary完全一致。31实际CPU测试及真实cached/local-build Harbor+Qwen tokenizer探针通过；未调用任务verifier、未重复GPU canary。失败的早期预检日志保留，最终使用r3。

现场free {res['free_bytes']/1024**3:.2f}GiB，初次启动门槛{initial['minimum_before_start_bytes']/1024**3:.2f}GiB。保存前保留单checkpoint估算加200GiB底线及10GiB余量；不足时等待用户释放空间，不删资产、不改保存频率。完整9份checkpoint估算{9*189686470567/1024**3:.2f}GiB，现有空间不够一次保留全程9份，后续需要用户继续管理空间。该磁盘等待并非Step20人工暂停。

运行命名空间：`{root}`；checkpoint：`{checkpoint}`。训练结束必须正常97完整checkpoint才能写成功标记；不自动重启失败。详细源码/数据/模型/备份SHA、退出与保存条件审计见同名JSON。Step20不做占卡评估，以保持连续训练。
'''
    (F/'LAUNCH_PREFLIGHT.md').write_text(md)
    print(json.dumps(dict(status=report['status'],source_manifest_SHA=report['source_manifest_SHA'],run=str(root),free_GiB=res['free_bytes']/1024**3)))

if __name__=='__main__':main()
