"""Read-only status; pipe from the Windows authoritative copy to A800 python3."""
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT=Path('/media/ubuntu/D1/zsj/Lego-RL-main')
EXP='sao-qwen35-9b-swesmith-b64-w32-v6d-20260930'
PREFIX='sao_b64_w32_v6_20260930d'
LOG=ROOT/'logs'/f'{PREFIX}_launcher.log'
raw=LOG.read_text(errors='replace') if LOG.exists() else ''
clean=re.sub(r'\x1b\[[0-9;]*m','',raw)
lines=clean.splitlines()
formal=[x for x in lines if 'training/global_step:' in x]
metrics={}
if formal:
    metrics={k:float(v) for k,v in re.findall(r'([\w/]+):(?:np\.\w+\()?([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?|nan|inf)',formal[-1])}
keys=['training/global_step','training/epoch','critic/vf_loss','critic/grad_norm','critic/vf_explained_var','critic/lr','actor/grad_norm','actor/lr','critic/rewards/mean','trajectory_filter/invalid_count','trajectory_filter/invalid_ratio','timing_s/step','timing_s/gen','timing_s/update_critic','response_length/clip_ratio']
checkpoint=ROOT/'checkpoints/sao-qwen35-9b-swesmith'/EXP
saved=[]
if checkpoint.exists():
    for step in sorted(checkpoint.glob('global_step_*'),key=lambda p:int(p.name.split('_')[-1])):
        entry={'step':int(step.name.split('_')[-1]),'data_pt':(step/'data.pt').is_file() and (step/'data.pt').stat().st_size>0}
        for kind in ('actor','critic'):
            shards=list((step/kind).glob('*.pt'))
            entry[kind]={'nonempty_pt':sum(p.stat().st_size>0 for p in shards),'pt_count':len(shards)}
        saved.append(entry)
marker=checkpoint/'latest_checkpointed_iteration.txt'
screen=subprocess.run(['screen','-ls'],capture_output=True,text=True).stdout
gpu=subprocess.run(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout
trials=ROOT/'harbor_trials/sao-qwen35-9b-swesmith'/EXP
result_files=list(trials.rglob('result.json')) if trials.exists() else []
errors=[x[-1200:] for x in lines if any(t in x for t in ('Traceback (most recent call last)','OutOfMemoryError','NCCL error','DataProto.concat','Address already in use','No space left on device'))]
trial_errors=[]
rewards=[]
for p in result_files:
    try:
        d=json.loads(p.read_text())
        if d.get('exception_info'): trial_errors.append({'path':str(p),'exception':{k:d['exception_info'].get(k) for k in ('exception_type','exception_message')}})
        rewards.append((d.get('verifier_result') or {}).get('rewards'))
    except (OSError,ValueError) as e:
        trial_errors.append({'path':str(p),'read_error':str(e)})
print(json.dumps({'time':time.strftime('%Y-%m-%d %H:%M:%S'),'screen':[s.strip() for s in screen.splitlines() if 'lego_sao_b64_w32_v6_' in s],
 'log_age_seconds':round(time.time()-LOG.stat().st_mtime,1) if LOG.exists() else None,'formal_steps':len(formal),
 'metrics':{k:metrics[k] for k in keys if k in metrics},'all_logged_metrics_finite':all(math.isfinite(v) for v in metrics.values()) if metrics else None,
 'completed_trial_results':len(result_files),'log_error_candidates_require_context':errors[-8:],'actual_trial_exceptions':trial_errors[-8:],'reward_counts':{str(v):sum((x or {}).get('reward')==v for x in rewards) for v in (0,1)},'gpu':gpu.strip().splitlines(),
 'free_GiB':round(shutil.disk_usage(ROOT).free/1024**3,2),'marker':marker.read_text().strip() if marker.exists() else None,'checkpoints':saved,
 'log_tail':[s[-600:] for s in lines[-10:]]},ensure_ascii=False,indent=2))
