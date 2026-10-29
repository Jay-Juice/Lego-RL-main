"""Development-only loss decomposition; never imported by the PI generator.

Reads already scored 607 development outputs. Coordinates only categorize
losses after generation; no confirmation cohort or new PI is generated.
"""
import collections
import gzip
import hashlib
import json
import pathlib
import sys

N = pathlib.Path(__file__).resolve().parents[1]
B = N.parents[1]
R = B / 'experiments/pi_repair_state_v2_20261015'
OLD = R / '.private_icps_bug_coverage_20261023'
V11 = R / '.private_icps_v11_window_20261023'
V = N / '.private_development_r4'
sys.path[:0] = [str(N / 'src'), str(N / 'core')]
from dense_state import proposals, render
from executable_windows import line_signals
from window_serializer import resolve

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def visible(z):
    return {(m['file'], p['line']) for m in z['source_map']
            for p in m['pi_emitted_source_spans_W0'] if p['line_complete']}

def main():
    frozen = read(N / 'CANDIDATE_FREEZE_R4.json')
    for f, h in frozen['source_SHA'].items():
        assert sha(N / f) == h
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(B / 'Qwen3.5-9B', local_files_only=True)
    receipt = read(N / 'reports/development_r4/GENERATION_RECEIPT.json')
    scored = {r['uid']: r for r in read(V / 'PRIVATE_SCORED_ROWS.json')}
    audit = {r['uid']: r for r in read(OLD / 'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    inputs = {r['uid']: r for r in read(V11 / 'ISSUE_ONLY_INPUTS.json')}
    groups = collections.defaultdict(collections.Counter)
    private = []
    key = 'changed_visible_intersect_any'
    for ref in receipt['rows']:
        uid = ref['uid']; row = scored[uid]
        old = row['metrics']['S1']['192'].get(key)
        new = row['metrics']['flow_expand']['192'].get(key)
        if old is None or new is None:
            continue
        p = V / (uid + '.json'); assert sha(p) == ref['SHA']
        d = read(p); cap = OLD / 'captures' / (uid + '.json.gz')
        assert sha(cap) == d['capture_SHA']
        s = json.load(gzip.open(cap, 'rt'))['snapshot']
        c = d['selected']; issue = inputs[uid]['issue']
        target = {(h['file'], i) for h in audit[uid]['label_hunks'] for i in h['changed_lines']}
        assert bool(target & visible(d['serialized']['S1'])) == bool(old)
        assert bool(target & visible(d['serialized']['flow_expand'])) == bool(new)
        candidate = bool(row['metrics']['S1']['192']['changed_selected_intersect_any'])
        group = 'lost' if old and not new else 'gained' if new and not old else 'both_hit' if old else 'both_miss_candidate' if candidate else 'outside_candidate'
        out = groups[group]; out['cases'] += 1
        props = proposals(c, s, issue, variant='flow_expand')
        hits = [(i, w) for i, w in enumerate(props) if any(w['file'] == f and w['start'] <= n <= w['end'] for f, n in target)]
        fitting = [(i, w) for i, w in hits if len(tok.encode(render([w]), add_special_tokens=False)) <= 192]
        out['target_proposal_exists'] += bool(hits)
        out['target_proposal_fits_alone'] += bool(fitting)
        if fitting:
            rank = fitting[0][0] + 1
            out['first_target_rank_' + ('1' if rank == 1 else '2to5' if rank <= 5 else '6to20' if rank <= 20 else 'over20')] += 1
        excluded = set(); executable = set(); linked = set()
        for e in resolve(c, s['files']):
            if not e['available']: continue
            scores, skip, relations = line_signals(e, s['files'][e['file']].splitlines(True), issue, True)
            excluded |= {(e['file'], i) for i in skip}
            executable |= {(e['file'], i) for i in scores}
            linked |= {(e['file'], i) for i in relations}
        out['target_in_excluded_declaration_or_docstring'] += bool(target & excluded)
        out['target_in_executable'] += bool(target & executable)
        out['target_in_name_linked'] += bool(target & linked)
        z = d['serialized']['flow_expand']; ws = z['windows']
        out['one_window_only'] += len(ws) == 1
        out['one_entity_only'] += len({w['entity_id'] for w in ws}) == 1
        out['used_at_least180tokens'] += len(z['pi_ids']) >= 180
        old_visible = visible(d['serialized']['S1'])
        out['old_target_within_new_selected_entity'] += any(w['file'] == f and e['start_line'] <= n <= e['end_line'] for f, n in target & old_visible for w in ws for e in c if e['entity_id'] == w['entity_id'])
        private.append(dict(uid=uid, group=group, first_fitting_target_proposal_rank=fitting[0][0]+1 if fitting else None))
    assert groups['lost']['cases'] == 16 and groups['gained']['cases'] == 56
    assert sum(x['cases'] for x in groups.values()) == 366
    output = dict(status='DEVELOPMENT_DIAGNOSTIC_ONLY',groups=dict(groups),
                  original607_only=True,confirmation_read=False,selector_changed=False,
                  source_SHA=frozen['source_SHA'],script_SHA=sha(pathlib.Path(__file__)),
                  source_receipt_SHA=sha(N/'reports/development_r4/GENERATION_RECEIPT.json'),
                  limitations=['Overlapping categories, not additive causes.',
                  'Proposal rank and oracle coordinates are scorer-only; forbidden as generator inputs.',
                  'A fitting target proposal does not identify which proposal to choose without labels.'])
    with (N/'reports/R4_DEVELOPMENT_LOSS_AUDIT.json').open('x') as f:
        json.dump(output,f,indent=2)
    with (V/'LOSS_AUDIT_PRIVATE.json').open('x') as f:
        json.dump(private,f,indent=2)
    print(json.dumps(output,indent=2))

if __name__ == '__main__': main()
