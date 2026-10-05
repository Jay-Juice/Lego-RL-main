#!/usr/bin/env python3
"""Sequential original-base recheck after completed step20; no training or cleanup."""
import json, pathlib, subprocess, time, shutil, hashlib, fcntl
R=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
Q=R/'logs/base0_recheck_20261005'
P=R/'logs/b64_verified_continue20_20261005'
RUN='base0-recheck-20261005-v1-n32-threads'
OUT=R/'logs/eval-qwen35-9b-verified-full'/RUN
Q.mkdir(exist_ok=True)
lock=(Q/'gate.lock').open('w'); fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
def state(s): (Q/'state.txt').write_text(s+'\n')
state('waiting_for_step20_exit_and_audit')
report=R/'logs/eval-qwen35-9b-verified-full/b64-v6d-step20-20261004-v2-n32-threads/summary_audited_verdict_v2.json'
while not (P/'exit_code').exists(): time.sleep(60)
try:
    d=json.loads(report.read_text())
    assert (P/'exit_code').read_text().strip() in ('0','3')
    assert len(d['rows'])==500 and len({x['task'] for x in d['rows']})==500
    assert not (d['duplicates'] or d['missing'] or d['unexpected']) and d['exits']==['0']*8
    assert not OUT.exists(), 'Refuse existing run'
    assert shutil.disk_usage(R).free>45*2**30, 'Insufficient D1 space'
    for _ in range(30):
        if not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(): break
        time.sleep(60)
    else: raise RuntimeError('GPUs still occupied; no cleanup attempted')
    (Q/'prerequisite.json').write_text(json.dumps({'step20_report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),'step20_passed':d['passed'],'step20_unresolved':d['unresolved'],'free_GiB':shutil.disk_usage(R).free/2**30},indent=2))
    state('base0_eval_running')
    command='''set -euo pipefail
export TMPDIR=/media/ubuntu/D1/zsj/tmp-e64
export LEGO_EVAL_SUBNET_POOL=172.16.240.0/20 LEGO_EVAL_SUBNET_PREFIX=29 N_CONCURRENT_PER_GPU=32
unset VERIFIED_INCLUDE_FILE
export FULL_RUN_ID=base0-recheck-20261005-v1-n32-threads
export VERIFIED_MODEL_PATH=/media/ubuntu/D1/zsj/Lego-RL-main/Qwen3.5-9B
export VERIFIED_SHARDS_ROOT=/media/ubuntu/D1/zsj/Lego-RL-main/data/verified-base0-recheck-20261005
bash scripts/eval/run_qwen35_verified_threads_8gpu.sh
'''
    with (Q/'eval.log').open('x') as f: code=subprocess.call(['bash','-c',command],cwd=R,stdout=f,stderr=subprocess.STDOUT)
    (Q/'eval_exit_code').write_text(str(code)+'\n')
    with (Q/'audit.log').open('x') as f: audit=subprocess.call(['python3',str(Q/'audit.py'),RUN],cwd=R,stdout=f,stderr=subprocess.STDOUT)
    state('complete' if code==0 and audit==0 else 'needs_audit_review')
    (Q/'exit_code').write_text(str(code or audit)+'\n')
except Exception as e:
    state('blocked: '+repr(e)); (Q/'exit_code').write_text('1\n'); raise
