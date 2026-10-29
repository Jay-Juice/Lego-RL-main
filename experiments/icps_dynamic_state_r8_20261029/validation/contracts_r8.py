import copy
import json
import sys
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core')]
from transformers import AutoTokenizer
from dynamic_session_r8 import R8DynamicSession
from changed_units_r8 import units
from dense_state import changes


def main():
    tok=AutoTokenizer.from_pretrained(N.parents[1]/'Qwen3.5-9B',local_files_only=True)
    count=0
    def snap(files,limited=False):return dict(files=files,stable=True,limited=limited)
    def call(s,files,i,limited=False):return s.capture(snap(files,limited),task_uid='x',session_id='x',logical_call_id=str(i),seq=i)
    # Distinct definitions, module units, decorators, nested methods, async and
    # multiline decorators are all source-derived and individually observable.
    fixtures=[('def a(x):\n return x+1\n\ndef b(x):\n return x+2\n',[2,5]),
        ('VALUE=20\n',[1]),
        ('VALUE=20\n\ndef a():\n return 1\n\n@decorate\ndef b():\n return 2\n',[1,4,6,8]),
        ('@decorate(\n  1,\n)\ndef a():\n return 1\n',[1,2,3]),
        ('class A:\n def a(self):\n  return 1\n def b(self):\n  return 2\n',[3,5]),
        ('async def a():\n return 1\n\nasync def b():\n return 2\n',[2,5])]
    for source,required in fixtures:
        s=R8DynamicSession('function anchor returns wrong value',tok,'x','x')
        base={'anchor.py':'def anchor():\n return 0\n'}
        call(s,base,0);out=call(s,dict(base,**{'new.py':source}),1)
        seen={i for w in out['windows'] if w['file']=='new.py' for i in range(w['start'],w['end']+1)}
        assert set(required)<=seen,(required,seen)
        assert len(out['pi_ids'])<=128
        count+=1
    # Retry must be byte-equivalent and free; wrong retry must not consume budget.
    s=R8DynamicSession('anchor',tok,'x','x');base={'a.py':'def anchor():\n return 1\n'}
    first=call(s,base,0);remaining=s.remaining
    assert call(s,base,0)==first and s.remaining==remaining;count+=1
    try:call(s,{'a.py':'def anchor():\n return 2\n'},0);raise AssertionError('bad retry accepted')
    except ValueError:pass
    assert s.remaining==remaining;count+=1
    edited={'a.py':'def anchor():\n return 2\n'}
    assert call(s,edited,1)['pi_ids'];assert call(s,base,2)['pi_ids'];count+=1
    assert not call(s,base,3)['pi_ids'];count+=1
    removed=call(s,{},4,limited=True);assert 'unobserved' in removed['pi_text'];count+=1
    parsed=call(s,{'a.py':'def broken(:\n pass\n'},5)
    assert parsed['windows'] and all(w['syntax']=='parse_unavailable' for w in parsed['windows']);count+=1
    # Current-source slices stay exact under rename and parse recovery.
    out=call(s,{'b.py':'def anchor():\n return 3\n'},6)
    assert any(w['file']=='b.py' for w in out['windows']);count+=1
    for w in out['windows']:assert w['code']==''.join('def anchor():\n return 3\n'.splitlines(True)[w['start']-1:w['end']])
    # Natural budget exhaustion uses no hidden reset, never exceeds4096.
    used=4096-s.remaining
    for i in range(7,200):
        out=call(s,{'b.py':f'def anchor():\n return {i}\n'},i);used+=len(out['pi_ids'])
        assert used+s.remaining==4096 and used<=4096
        if s.exhausted:break
    assert s.exhausted;assert not call(s,{'b.py':'def anchor():\n return 900\n'},201)['pi_ids'];count+=1
    # Large additions are explicitly partial and bounded, not claimed complete.
    files={'big.py':'\n'.join(f'def f{i}():\n return {i}\n' for i in range(200))}
    uu,capped=units(snap(files),changes({},files),'');assert len(uu)==128 and capped;count+=1
    report=dict(passed=count,actual_Qwen=True,model=False,GPU=False,budget=[1024,128,4096])
    (N/'reports/CONTRACTS_R8.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
