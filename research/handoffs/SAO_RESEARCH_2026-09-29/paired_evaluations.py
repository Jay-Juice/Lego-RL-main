"""Read-only paired evaluation audit; unresolved are failures by user's request."""
import json, math, collections, hashlib
from pathlib import Path
r=Path('/media/ubuntu/D1/zsj/Lego-RL-main')
root=r/'logs/eval-qwen35-9b-verified-full'
base_summary=root/'20260923-123439-missing362/combined_500_summary.json'
o=json.loads(base_summary.read_text());base={}
for run,files in o['result_files_by_run'].items():
    for f in files:
        j=json.loads((r/f).read_text())
        for ev in j['stats']['evals'].values():
            for reward,ids in ev['reward_stats']['reward'].items():
                for ident in ids:
                    key=ident.rsplit('__',1)[0]
                    assert key not in base,key
                    base[key]=int(float(reward))
single=root/'20260923-123439-missing362/single14710-verifier/verifier/reward.txt'
assert float(single.read_text())==1
assert 'scikit-learn__scikit-learn-14710' not in base
base['scikit-learn__scikit-learn-14710']=1
assert len(base)==500 and sum(base.values())==279
out=[]
for n in [80,100,110,120,130]:
    p=None
    for d in sorted(root.glob('sao-step%d-*'%n)):
        for f in ['summary_audited.json','summary_with_fixed_patch_reverification.json','summary_with_diagnosed_unresolved.json']:
            if (d/f).exists():p=d/f
    j=json.loads(p.read_text());m={v['task_name']:int(v['reward'] or 0) for v in j['rows']}
    for u in j.get('unresolved_tasks',[]):m[u['task_name']]=0
    assert set(m)==set(base)
    gain=sum(m[k]>base[k] for k in m);lost=sum(m[k]<base[k] for k in m);nd=gain+lost
    pv=min(1.,2*sum(math.comb(nd,i) for i in range(min(gain,lost)+1))/2**nd)
    cnt=collections.defaultdict(lambda:[0,0,0])
    for k,v in m.items():
        repo=k.rsplit('-',1)[0];cnt[repo][0]+=1;cnt[repo][1]+=base[k];cnt[repo][2]+=v
    out.append({'step':n,'pass':sum(m.values()),'gained':gain,'lost':lost,'exact_mcnemar_p_unadjusted':pv,
                'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'by_repo_n_base_checkpoint':dict(cnt)})
print(json.dumps({'base':str(base_summary),'base_fixed_patch_reward':str(single),'comparisons':out,
 'caveat':'Single stochastic run per checkpoint; different resource settings; unadjusted exploratory p-values, not controlled causal tests.'},indent=2))
