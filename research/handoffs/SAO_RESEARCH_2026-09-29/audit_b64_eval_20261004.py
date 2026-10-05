"""Strict independent result provenance audit; unresolved tasks stop the queue."""
from pathlib import Path
import collections
import hashlib
import json
import math
import sys

r = Path('/media/ubuntu/D1/zsj/Lego-RL-main')
run = sys.argv[1]
out = r / 'logs/eval-qwen35-9b-verified-full' / run
expected = {p.name for p in (r / 'data/swebench-verified').iterdir() if (p / 'task.toml').is_file()}
assert len(expected) == 500
rows = []
exits = []
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for shard in range(8):
    exits.append((out / f'shard_{shard}.exit_code').read_text().strip())
    job = r / 'harbor_trials' / f'eval-qwen35-9b-verified-full-{run}-s{shard}'
    for p in sorted(job.glob('*/result.json')):
        d = json.loads(p.read_text())
        value = (d.get('verifier_result') or {}).get('rewards', {}).get('reward')
        error = (d.get('exception_info') or {}).get('exception_type')
        reward_file = p.parent / 'verifier/reward.txt'
        try:
            file_value = float(reward_file.read_text().strip())
        except (OSError, ValueError):
            file_value = None
        valid = (isinstance(value, (int, float)) and math.isfinite(value) and value in (0, 1)
                 and file_value == value and bool((d.get('verifier') or {}).get('finished_at'))
                 and error in (None, 'AgentTimeoutError', 'NonZeroAgentExitCodeError'))
        patch = p.parent / 'artifacts/predict_patch.diff'
        rows.append(dict(task=d['task_name'], result=str(p), result_sha256=sha(p),
                         patch=str(patch) if patch.exists() else None,
                         patch_sha256=sha(patch) if patch.exists() else None,
                         reward=value if valid else None, exception=d.get('exception_info')))
counts = collections.Counter(x['task'] for x in rows)
duplicates = sorted(k for k,v in counts.items() if v != 1)
missing = sorted(expected - counts.keys())
unexpected = sorted(counts.keys() - expected)
unresolved = [x['task'] for x in rows if x['reward'] is None]
passed = sum(x['reward'] == 1 for x in rows)
ok = len(rows) == 500 and not (duplicates or missing or unexpected or unresolved) and exits == ['0']*8
report = dict(run_id=run, complete=ok, passed=passed, failed=sum(x['reward']==0 for x in rows),
              unresolved=unresolved, score=passed/500 if ok else None,
              duplicates=duplicates, missing=missing, unexpected=unexpected, exits=exits, rows=rows)
with (out/'summary_audited_verdict_v2.json').open('x') as f:
    json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
sys.exit(0 if ok else 3)
