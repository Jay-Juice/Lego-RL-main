"""Synthetic changed-source visibility, not gold-answer or live-model scoring."""
import json
import time
import sys
from pathlib import Path
N = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(N/'src'), str(N/'core')]
from transformers import AutoTokenizer
from dynamic_session_r8 import R8DynamicSession as R7DynamicProbe



def snapshot(files):
    return dict(files=files, stable=True, limited=False)


def main():
    tok = AutoTokenizer.from_pretrained(N.parents[1]/'Qwen3.5-9B', local_files_only=True)
    base = {'anchor.py': 'def compute_total(x):\n    return x+1\n'}
    cases = [
        ('function_edit', base, {'anchor.py':'def compute_total(x):\n    return x+2\n'}, [('anchor.py',2)]),
        ('added_two_functions', base, dict(base, **{'added.py':'def first(x):\n    return x+3\n\ndef second(x):\n    return x+4\n'}), [('added.py',2),('added.py',5)]),
        ('module_constant', dict(base, **{'config.py':'LIMIT = 10\n\ndef limit(x):\n    return min(x, LIMIT)\n'}), dict(base, **{'config.py':'LIMIT = 20\n\ndef limit(x):\n    return min(x, LIMIT)\n'}), [('config.py',1)]),
        ('decorator', {'anchor.py':'@cache_one\ndef compute_total(x):\n    return x+1\n'}, {'anchor.py':'@cache_two\ndef compute_total(x):\n    return x+1\n'}, [('anchor.py',1)]),
    ]
    rows=[]
    for label, before, after, changed in cases:
        s=R7DynamicProbe('compute_total returns an incorrect integer',tok,label,label)
        initial=s.capture(snapshot(before),task_uid=label,session_id=label,logical_call_id='0',seq=0)
        assert not s.capture(snapshot(before),task_uid=label,session_id=label,logical_call_id='1',seq=1)['pi_ids']
        t=time.monotonic()
        out=s.capture(snapshot(after),task_uid=label,session_id=label,logical_call_id='2',seq=2)
        elapsed=time.monotonic()-t
        assert s.capture(snapshot(after),task_uid=label,session_id=label,logical_call_id='2',seq=2)==out
        for w in out['windows']:
            assert w['code']==''.join(after[w['file']].splitlines(True)[w['start']-1:w['end']])
        visible={(w['file'],line) for w in out['windows'] for line in range(w['start'],w['end']+1)}
        rollback=s.capture(snapshot(before),task_uid=label,session_id=label,logical_call_id='3',seq=3)
        rows.append(dict(event=label,initial_tokens=len(initial['pi_ids']),update_tokens=len(out['pi_ids']),
            changed_units=len(changed),visible_changed_units=sum(x in visible for x in changed),
            all_changed_units_visible=all(x in visible for x in changed),
            update_seconds=elapsed,rollback_tokens=len(rollback['pi_ids']),
            rollback_unknown=rollback.get('unknown',False),remaining=s.remaining,
            current_source_exact=True,retry_exact=True))
    result=dict(status='passed' if all(r['all_changed_units_visible'] for r in rows) else 'dynamic_visibility_gap',
        budgets=[1024,128,4096],synthetic_source_events=True,actual_Qwen_tokenizer=True,
        model_rollout=False,training_admission=False,events=rows)
    (N/'reports/DYNAMIC_QUALITY_R8.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
