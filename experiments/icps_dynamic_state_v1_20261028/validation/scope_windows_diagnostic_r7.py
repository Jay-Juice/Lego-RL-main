"""Post-freeze label-informed availability; aggregate only, never constructor."""
import ast,collections,gzip,importlib.util,json,sys
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
from window_serializer import resolve
from dense_state import render
from executable_windows import proposals
from scope_windows_r7 import scope_proposals
spec=importlib.util.spec_from_file_location('scope_driver',N/'validation/scope_windows_r7.py')
run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)

def main():
    receipt=d.read(run.O/'GENERATION_RECEIPT.json');agg=d.read(run.O/'AGGREGATE.json')
    assert receipt['source_SHA']==run.sources() and receipt['count']==607
    audit={r['uid']:r for r in d.read(d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    prior={r['uid']:r for r in d.read(d.O11/'ICPS_V11_CPU_COVERAGE_RESULTS.json')['rows']}
    issues={r['uid']:r['issue'] for r in d.read(d.V11/'ISSUE_ONLY_INPUTS.json')}
    counts={m:collections.Counter() for m in run.ARMS};strata={m:collections.defaultdict(collections.Counter) for m in run.ARMS}
    tok=d.tokenizer()
    for row in receipt['rows']:
        uid=row['uid'];p=run.V/f'{uid}.json';assert d.sha(p)==row['SHA']
        meta=prior[uid]
        if meta['grade']!='exact_hunk' or meta['hunk_map_status']!='mapped':continue
        v=d.read(p);target={(h['file'],i) for h in audit[uid]['label_hunks'] for i in h['changed_lines']}
        cap=d.OLD/'captures'/f'{uid}.json.gz';assert d.sha(cap)==v['capture_SHA']
        snapshot=json.load(gzip.open(cap,'rt'))['snapshot'];c=v['selected']['passage24'];entities=resolve(c,snapshot['files'])
        candidate_hit=any(e['available'] and any(e['file']==f and e['start_line']<=i<=e['end_line'] for f,i in target) for e in entities)
        stratum='has_class_candidate' if any(isinstance(e.get('node'),ast.ClassDef) for e in entities) else 'no_class_candidate'
        for mode in run.ARMS:
            props=proposals(c,snapshot['files'],issues[uid],flow=True) if mode=='control1024_8' else scope_proposals(entities,snapshot['files'],issues[uid],balanced=mode=='balanced1024_8')
            hit_seeds=[w for w in props if any(w['file']==f and w['start']<=i<=w['end'] for f,i in target)]
            affordable=any(len(tok.encode(render([w],snapshot.get('limited',False)),add_special_tokens=False))<=1024 for w in hit_seeds)
            z=v['serialized'][mode];visible={(e['file'],s['line']) for e in z['source_map'] for s in e['pi_emitted_source_spans_W0'] if s['line_complete']}
            hit=bool(visible&target)
            category='visible' if hit else 'candidate_absent' if not candidate_hit else 'no_target_seed' if not hit_seeds else 'target_seed_overbudget' if not affordable else 'feasible_target_seed_not_emitted'
            for counter in (counts[mode],strata[mode][stratum]):
                counter.update(tasks=1,candidate_available=int(candidate_hit),proposal_target_available=int(bool(hit_seeds)),affordable_target_seed_available=int(affordable))
                counter[category]+=1
    for m,b in counts.items():
        assert b['tasks']==366 and b['candidate_available']==343
        assert b['visible']==agg['results'][m]['changed_visible_intersect_any']['hits']
    result=dict(status='POST_FREEZE_ORACLE_AVAILABILITY_NOT_ACHIEVABLE_COVERAGE',counts=counts,strata=strata,
        aggregate_SHA=d.sha(run.O/'AGGREGATE.json'),generation_receipt_SHA=d.sha(run.O/'GENERATION_RECEIPT.json'),source_SHA=d.sha(Path(__file__)),
        limitations=['Target-informed post-freeze diagnostic, never used by selector.','Individually affordable seeds need not jointly fit; context growth can reach lines absent from seed union.','Same reused development, not independent/RL evidence. No per-case exports.'])
    d.save(run.O/'LOSS_DECOMPOSITION.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
