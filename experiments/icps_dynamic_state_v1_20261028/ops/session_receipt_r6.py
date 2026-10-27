"""Compose two disjoint validation scopes; never relabel a failed queue as passed."""
import hashlib
import json
import pathlib
import re
import sys

N = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = 'reports/R6_SESSION_COMPOSITE_RECEIPT.json'
MANIFESTS = ['validation/SESSION_R6_R2.sha256', 'validation/SESSION_R6_DYNAMIC_R3.sha256']
EVIDENCE = ['reports/session_r6_r2/INITIAL_COMPARISON.json',
            'reports/session_r6_dynamic_r3/AGGREGATE.json',
            'logs/session_r6_r2/exit', 'logs/session_r6_r2/validation.log',
            'logs/session_r6_r2/contracts.log', 'logs/session_r6_dynamic_r3/exit',
            'logs/session_r6_dynamic_r3/contracts.log']

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def validate(initial, dynamic, original_exit, corrected_exit, failure):
    c = initial['counts']
    assert c['cases'] == c['candidate_identity_exact'] == c['initial_payload_exact'] == 607
    assert c['status_path_cases'] == 0
    assert initial['actual_Landlock'] and initial['label_paths_denied'] == 2
    assert original_exit == 1 and corrected_exit == 0
    # Only the proven assertion omission is accepted as superseded test evidence.
    tail = failure.split('Traceback (most recent call last):')
    assert len(tail) == 2
    assert 'validation/session_r6_r2.py' in tail[1]
    assert "deleted=call(sess,s,5);assert 'missing' in deleted['pi_text'] or 'unknown' in deleted['pi_text']" in tail[1]
    assert tail[1].rstrip().endswith('AssertionError')
    assert dynamic['status'] == 'DYNAMIC_CONTRACTS_PASS_AWAIT_INITIAL607'
    assert dynamic['cases'] == 24 and dynamic['budgets'] == [192,128,4096]
    for k in ['addition','retry','noop','edit_rollback','deletion','late_rejected',
              'retry_change_rejected','identity_rejected']:
        assert dynamic['constructed'][k] == 24, k
    assert dynamic['constructed']['initial_update_semantic_boundary_nocharge'] == 1
    assert dynamic['initial']['cases'] == dynamic['initial']['initial_payload_exact'] == dynamic['initial']['candidate_identity_exact'] == 25
    assert dynamic['initial']['capacity_excluded'] == 1
    assert dynamic['max_update_tokens'] <= 128
    assert dynamic['spent'] + dynamic['remaining'] == 4096
    assert dynamic['natural_exhaustion_calls'] > 0
    assert dynamic['actual_Landlock'] and dynamic['label_paths_denied'] == 2
    assert dynamic['GPU_jobs'] == dynamic['optimizer_steps'] == 0

def collect(n):
    sources = {}
    for name in MANIFESTS:
        for line in (n/name).read_text().splitlines():
            want, rel = line.split(None,1)
            assert sha(n/rel) == want, rel
            if rel in sources: assert sources[rel] == want
            sources[rel] = want
    assert sources['src/dynamic_session_r6_r2.py'] == '2fc155b3be81e0311f274040a08582fa9b182688e313eb36c73dae30ded62d93'
    initial = json.loads((n/EVIDENCE[0]).read_text())
    dynamic = json.loads((n/EVIDENCE[1]).read_text())
    validate(initial, dynamic, int((n/EVIDENCE[2]).read_text()),
             int((n/EVIDENCE[5]).read_text()), (n/EVIDENCE[3]).read_text())
    for name in [EVIDENCE[4], EVIDENCE[6]]:
        log = (n/name).read_text()
        assert re.search(r'Ran 22 tests in .*\n\s*\nOK\s*$',log), name
    return dict(status='COMPOSITE_SESSION_CONTRACTS_PASS_NOT_ONLINE_ADMISSION',
                initial_exact=607, dynamic_cases=24, original_queue_exit=1,
                corrected_dynamic_queue_exit=0, source_SHA=sources,
                evidence_SHA={p:sha(n/p) for p in EVIDENCE+MANIFESTS},
                explanation='Original complete607 phase accepted. Its later known deletion assertion omission is superseded only by same-source corrected24 dynamic tests. Original exit1 retained; no whole-queue exit0 claim.',
                training_allowed=False, independent_pass=False, online_pass=False)

def verify_receipt(n=N):
    recorded = json.loads((n/RECEIPT).read_text())
    assert recorded == collect(n), 'Evidence or source drift'
    return recorded

if __name__ == '__main__':
    if sys.argv[1:] == ['build']:
        data=collect(N)
        with (N/RECEIPT).open('x') as f: json.dump(data,f,indent=2)
    elif sys.argv[1:] == ['check']:
        data=verify_receipt()
    else: raise SystemExit('build|check required')
    print(data['status'])
