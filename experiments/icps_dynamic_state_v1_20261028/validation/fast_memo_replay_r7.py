"""Source-only exact replay/performance follow-up, no label/scorer import."""
import gzip,json,os,sys,time,statistics,math,hashlib
from pathlib import Path
N=Path(__file__).resolve().parents[1];sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
import fast_allocation_r7 as old
import fast_memo_r7 as new
V=N/'.private_fast_memo_r7';O=N/'reports/fast_memo_r7';BASE=N/'.private_fast_allocation_r7'
ARMS=('fast768_8','fast1024_12')
FILES=['src/fast_memo_r7.py','validation/fast_memo_replay_r7.py','validation/fast_memo_r7_contracts.py','R7_FAST_MEMO_PLAN.md']

def sources():return {f:d.sha(N/f) for f in FILES}

def generate(shard):
    assert shard in range(4) and V.is_dir() and O.is_dir()
    receipt=d.read(N/'reports/fast_allocation_r7/GENERATION_RECEIPT.json')
    assert receipt['count']==607 and receipt['baseline_exact']==607
    for p,h in receipt['source_SHA'].items():assert d.sha(N/p)==h
    rows=sorted(d.read(d.V11/'ISSUE_ONLY_INPUTS.json'),key=lambda r:r['uid'])
    assert len(rows)==607
    expected={r['uid']:r['SHA'] for r in receipt['rows']}
    subset={r['uid'] for r in rows[:64]};subset_sha=hashlib.sha256(json.dumps(sorted(subset)).encode()).hexdigest()
    own=sources();reference_sha=d.sha(N/'reports/fast_allocation_r7/GENERATION_RECEIPT.json')
    tok=d.tokenizer();rows=rows[shard::4]
    from landlock import sandbox
    sandbox(['/usr','/lib','/lib64','/etc',sys.base_prefix,d.B/'.venv',d.B/'Qwen3.5-9B',N/'src',N/'core',N/'validation',
        d.OLD/'captures',d.V11/'ISSUE_ONLY_INPUTS.json',*[BASE/f"{r['uid']}.json" for r in rows],'/proc/self','/dev/null'],[V,O])
    denied=0
    forbidden=[d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json',d.R/'.private_oracle_pi_20261022/ORACLE_DATA_MANIFEST_STRICT.json']
    forbidden += [N/(x+'/PRIVATE_SCORED_ROWS.json') for x in ['.private_development_r6','.private_capacity_allocation_r7','.private_window_research_r7',
        '.private_budget_ablation_r7_r2','.private_joint_windows_r7','.private_lookahead_windows_r7','.private_relevance_windows_r7',
        '.private_recall_windows_r7_r2','.private_protected_behavior_r7','.private_behavior_windows_r7','.private_entity_allocation_r7','.private_fast_allocation_r7']]
    for p in forbidden:
        try:p.read_bytes();raise AssertionError('label readable')
        except PermissionError:denied+=1
    benchmark=[];started=time.monotonic();count=0
    for i,row in enumerate(rows):
        p=BASE/f"{row['uid']}.json";assert d.sha(p)==expected[row['uid']];baseline=d.read(p)
        cap=d.OLD/'captures'/f"{row['uid']}.json.gz";assert d.sha(cap)==baseline['capture_SHA']
        snapshot=json.load(gzip.open(cap,'rt'))['snapshot'];c=baseline['selected']['passage24']
        measured=row['uid'] in subset
        for arm in ARMS:
            implementations=[('new',new)]
            if measured:
                implementations=[('old',old),('new',new)]
                if (shard+4*i)%2:implementations.reverse()
            record=dict(uid=row['uid'],arm=arm)
            for name,module in implementations:
                tokenizer=old.MeteredCache(tok);t=time.monotonic();cpu=time.process_time()
                result=module.serialize(c,snapshot,row['issue'],tokenizer,arm=arm)
                elapsed=time.monotonic()-t;cpu_elapsed=time.process_time()-cpu
                assert result==baseline['serialized'][arm],'full-output replay failed'
                assert len(result['pi_ids'])<=old.ARMS[arm][0]
                record[name]=dict(wall=elapsed,cpu=cpu_elapsed,**tokenizer.stats())
                del tokenizer,result
            if measured:benchmark.append(record)
        count+=1
        if count%20==0:print(json.dumps(dict(replayed=count,seconds=time.monotonic()-started)),flush=True)
    d.save(V/f'replay_{shard}.json',dict(count=count,arms=ARMS,benchmark=benchmark,source_SHA=own,baseline_source_SHA=receipt['source_SHA'],
        reference_receipt_SHA=reference_sha,benchmark_subset_SHA=subset_sha,label_denied=denied,wall_seconds=time.monotonic()-started))

def combine():
    parts=[d.read(V/f'replay_{i}.json') for i in range(4)]
    assert sum(p['count'] for p in parts)==607
    assert all(p['source_SHA']==sources() and p['label_denied']==14 for p in parts)
    for p,h in parts[0]['baseline_source_SHA'].items():assert d.sha(N/p)==h
    assert len({p['reference_receipt_SHA'] for p in parts})==len({p['benchmark_subset_SHA'] for p in parts})==1
    rows=[r for p in parts for r in p['benchmark']]
    assert len(rows)==128 and len({r['uid'] for r in rows})==64
    def q(values):
        v=sorted(values)
        return dict(n=len(v),mean=sum(v)/len(v),median=statistics.median(v),p95=v[math.ceil(.95*len(v))-1],max=max(v))
    stats={}
    for arm in ARMS:
        rr=[r for r in rows if r['arm']==arm];assert len(rr)==64
        stats[arm]={name:{field:q([r[name][field] for r in rr]) for field in ('wall','cpu','encode_requests','encode_misses','encoded_bytes')} for name in ('old','new')}
        stats[arm]['paired_wall_ratio']=q([r['new']['wall']/r['old']['wall'] for r in rr])
    out=dict(status='COMPLETE_SOURCE_ONLY_EXACT_REPLAY_NOT_NEW_QUALITY_EVIDENCE',UTC=d.utc(),exact_inputs_each_arm=607,arms=ARMS,
        benchmark_inputs_each_arm=64,benchmark_subset_SHA=parts[0]['benchmark_subset_SHA'],timing=stats,
        source_SHA=sources(),baseline_source_SHA=parts[0]['baseline_source_SHA'],reference_receipt_SHA=parts[0]['reference_receipt_SHA'],
        label_denials_per_shard=14,GPU_model_training=False,
        limitations=['All607full output dictionaries exact; quality inherited, not independently retested.',
        'Timing only first64metadata-sorted inputs, both implementations interleaved/rotated with fresh caches, four workers.',
        'P95 uses nearest-rank convention on64samples, not whole607or live training latency.'])
    d.save(O/'AGGREGATE.json',out);print(json.dumps(out,indent=2))

if __name__=='__main__':
    if sys.argv[1]=='generate':generate(int(sys.argv[2]))
    else:combine()
