"""Run only the predeclared W0 R5 allocators; reuse frozen scoring interface."""
import pathlib
import sys
N=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'validation')]
assert sys.argv[2]=='r5'
import development as d
from guard_windows_r5 import serialize as guard
base=d.serialize
d.VARIANTS=['flow_expand','guard_expand','anchor_expand']
d.CONFIG=dict(d.CONFIG,version='icps_w0_r5',development_variants=d.VARIANTS,
              plan_SHA=d.sha(N/'R5_PLAN.md'),online_integrated=False)
def select(c,s,i,t,**kw):
    return guard(c,s,i,t,**kw) if kw.get('variant') in {'guard_expand','anchor_expand'} else base(c,s,i,t,**kw)
d.serialize=select
if sys.argv[1]=='control':
    a=d.read(N/'reports/development_r4/GENERATION_RECEIPT.json')
    b=d.read(N/'reports/development_r5/GENERATION_RECEIPT.json')
    assert {r['uid'] for r in a['rows']}=={r['uid'] for r in b['rows']}
    for row in a['rows']:
        uid=row['uid'];p=N/'.private_development_r4'/f'{uid}.json'
        assert d.sha(p)==row['SHA']
        old=d.read(p)['serialized']['flow_expand']
        new=d.read(N/'.private_development_r5'/f'{uid}.json')['serialized']['flow_expand']
        assert old==new,uid
    print('FROZEN_FLOW_CONTROL_EXACT',len(a['rows']))
else:
    {'generate':d.generate,'score':d.score}[sys.argv[1]]()
