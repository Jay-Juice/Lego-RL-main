"""CPU-only, read-only inventory; never prints source or trajectory contents."""
import collections, hashlib, json, pathlib

B = pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
R = B/'experiments/pi_repair_state_v2_20261015'
F = B/'experiments/icps_v11_full97_sao_20261024_r2'
P = pathlib.Path(__file__).resolve().parent

def main():
    index = json.loads((R/'.private_icps_bug_coverage_20261023/RETRIEVAL_INPUTS.json').read_text())['rows']
    by_task = {r['task_id']: r for r in index}
    counts = collections.Counter(); rows = []
    root = F/'runs/full_20261023T180705Z_3600076/trials'
    for step in range(1, 41):
        for trial in sorted((root/f'step_{step:04d}').iterdir()):
            if not (trial/'pi_calls.json').is_file(): continue
            counts['attempts'] += 1
            cfg = json.loads((trial/'config.json').read_text())
            task = pathlib.Path(cfg['task']['path']).name
            task = task.removeprefix('ohsdk-')
            if task not in by_task: continue
            counts['has_W0_snapshot'] += 1
            audit = json.loads((trial/'pi_calls.json').read_text())
            recs = audit['records']
            if audit.get('error') or not recs or not recs[0]['tokens']: continue
            if any(r['state_hash'] != recs[0]['state_hash'] for r in recs): continue
            if any(r['tokens'] for r in recs[1:]): continue
            if not (trial/'proxy_trajectory.json').is_file(): continue
            counts['constant_state_initial_PI_only'] += 1
            rows.append(dict(task_id=task, uid=by_task[task]['uid'], trial=str(trial),
                             source_step=step, selection_key=hashlib.sha256(str(trial.relative_to(root)).encode()).hexdigest()))
    rows.sort(key=lambda r:r['selection_key'])
    out=dict(scope='Eligibility only; no model, tokenizer, reward-based selection or training access', counts=dict(counts), rows=rows)
    path=P/'private_inventory.json'
    with path.open('x') as f: json.dump(out,f,indent=2)
    print(json.dumps(dict(counts=dict(counts), unique_tasks=len({r['task_id'] for r in rows}),families=len({r['task_id'].split('.')[0] for r in rows}))))

if __name__=='__main__': main()
