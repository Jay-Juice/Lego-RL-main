"""Read only: extract the successful checkpoint lineage, excluding discarded v2.

Run via stdin with remote system Python; writes JSON only to stdout.
"""
import hashlib
import json
import re
import statistics
from pathlib import Path

ROOT = Path('/media/ubuntu/D1/zsj/Lego-RL-main')
SOURCES = [
    ('logs/sao_64k_full_sp8_tokenpack_launcher.log', 1, 25),
    ('logs/sao_resume25_20260925b_launcher.log', 26, 30),
    ('logs/sao_resume30_20260925c_launcher.log', 31, 70),
    ('logs/sao_resume70_verdict_v2b_20260928_train.log', 71, 130),
]
KEYS = ['critic/vf_explained_var', 'critic/grad_norm', 'critic/vf_loss',
        'critic/vf_clipfrac', 'critic/lr', 'actor/lr', 'actor/grad_norm',
        'critic/score/mean', 'critic/rewards/mean', 'critic/returns/mean',
        'critic/returns/min', 'critic/returns/max', 'critic/values/mean',
        'response_length/clip_ratio', 'response_length/mean', 'num_turns/mean',
        'trajectory_filter/invalid_count', 'trajectory_filter/invalid_ratio',
        'actor/rollout_corr/rollout_is_eff_sample_size',
        'actor/rollout_corr/kl', 'actor/rollout_corr/log_ppl_abs_diff',
        'actor/rollout_corr/rollout_is_oob_ratio', 'prompt_length/clip_ratio']
pattern = re.compile(r'([\w/]+):(?:np\.\w+\()?([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)')
steps = {}
sources = []
for relative, lo, hi in SOURCES:
    p = ROOT / relative
    raw = p.read_bytes()
    sources.append({'path': str(p), 'sha256': hashlib.sha256(raw).hexdigest()})
    for line in raw.decode(errors='replace').splitlines():
        if 'training/global_step:' not in line:
            continue
        metrics = {k: float(v) for k, v in pattern.findall(line)}
        step = int(metrics['training/global_step'])
        if lo <= step <= hi:
            steps[step] = {k: metrics[k] for k in KEYS if k in metrics}
groups = []
for lo, hi in [(1,19),(20,30),(31,70),(71,90),(91,110),(111,130)]:
    rows = [v for k,v in sorted(steps.items()) if lo <= k <= hi]
    group = {'range': [lo,hi], 'n_logged':len(rows), 'metrics':{}}
    for key in KEYS:
        vs = [r[key] for r in rows if key in r]
        if vs:
            group['metrics'][key] = {'mean':statistics.mean(vs),
                                     'median':statistics.median(vs),
                                     'min':min(vs), 'max':max(vs)}
    gs = [r['critic/grad_norm'] for r in rows]
    ev = [r['critic/vf_explained_var'] for r in rows]
    group.update(critic_grad_over10=sum(x>10 for x in gs),
                 critic_grad_over30=sum(x>30 for x in gs),
                 ev_negative=sum(x<0 for x in ev),
                 ev_over_point4=sum(x>.4 for x in ev))
    groups.append(group)
print(json.dumps({'sources':sources,'steps':steps,'groups':groups,
                  'missing_steps':[i for i in range(1,131) if i not in steps]}, indent=2))
