"""Label-blind dynamic source observation. No IO, rewards, tests or model calls.

Inputs are only issue and bounded, already observed workspace snapshots.
Coordinates always refer to the CURRENT source. No claim that a change is a fix.
"""
import ast
import copy
import difflib
import math
import re
from issue_program_state import build_initial_index, parse_file
from workspace_read import allowed
from window_serializer import resolve, terms, query, sha, digest, proposals as contiguous_proposals

CONFIG = dict(version='icps_dynamic_r2', initial=192, update=128, episode=4096,
              max_candidates=3, max_windows=3, max_statement_lines=8,
              variants=['compact', 'diverse', 'expand'], labels_used=False)

def validate(snapshot):
    if not snapshot.get('stable'):
        raise ValueError('unstable current source; no stale fallback')
    files=snapshot.get('files')
    if not isinstance(files,dict) or len(files)>1500:
        raise ValueError('invalid bounded source')
    if sum(len(v.encode()) for v in files.values())>8388608:
        raise ValueError('source budget')
    for path,code in files.items():
        if not allowed(path) or not isinstance(code,str) or len(code.encode())>262144:
            raise ValueError('source outside allowlist/bounds')

def changes(before,after):
    """Current-line ranges; removed spans become explicit current anchors."""
    out={}
    for path in sorted(set(before)|set(after)):
        a,b=before.get(path),after.get(path)
        if a==b:continue
        if a is None:
            out[path]=dict(kind='added',ranges=[(1,max(1,len(b.splitlines())))],removed_lines=0)
        elif b is None:
            out[path]=dict(kind='missing',ranges=[],removed_lines=len(a.splitlines()))
        else:
            aa,bb=a.splitlines(),b.splitlines();ranges=[];removed=0
            for tag,i,j,k,l in difflib.SequenceMatcher(None,aa,bb,autojunk=False).get_opcodes():
                if tag=='equal':continue
                if l>k:ranges.append((k+1,l))
                else:ranges.append((max(1,min(k+1,len(bb))),max(1,min(k+1,len(bb)))))
                removed+=max(0,(j-i)-(l-k))
            out[path]=dict(kind='modified',ranges=ranges,removed_lines=removed)
    return out

def overlap(a,b):return max(a[0],b[0])<=min(a[1],b[1])

def dynamic_candidates(initial,snapshot,delta,issue):
    """One issue anchor plus smallest current entities at actual changed lines."""
    files=snapshot['files'];q,_=query(issue);found={}
    # The existing issue anchor does not depend on edit outcomes or labels.
    anchor=next((x for x in resolve(initial,files) if x['available']),None)
    for path,change in sorted(delta.items()):
        if path not in files:continue
        entities=[e for e in parse_file(path,files[path]) if not e.get('ambiguous')]
        for interval in change['ranges']:
            matches=[e for e in entities if overlap((e['start_line'],e['end_line']),interval)]
            if not matches:continue
            # A changed line inside a method should not select its entire class.
            smallest=sorted(matches,key=lambda e:(e['end_line']-e['start_line'],e['start_line'],e['qualified']))[0]
            key=smallest['entity_id'];score=len(terms(smallest.get('source',''))&q)
            found[key]=(smallest,found.get(key,(None,0,score))[1]+1,score)
    ranked=sorted(found.values(),key=lambda z:(-z[1],-z[2],z[0]['end_line']-z[0]['start_line'],z[0]['file'],z[0]['qualified']))
    selected=[]
    # Two dynamic slots first; unused slots can be filled by old focus.
    for e,_,_ in ranked[:2]:selected.append(dict(e,selection='observed_change'))
    if anchor and all(x['entity_id']!=anchor['entity_id'] for x in selected):selected.append(anchor)
    for e,_,_ in ranked[2:]:
        if len(selected)>=3:break
        if all(x['entity_id']!=e['entity_id'] for x in selected):selected.append(dict(e,selection='observed_change'))
    for e in resolve(initial,files):
        if len(selected)>=3:break
        if e['available'] and all(x['entity_id']!=e['entity_id'] for x in selected):selected.append(e)
    return [{k:v for k,v in e.items() if k not in {'node','source','features'}} for e in selected[:3]]

def status_facts(initial,snapshot,delta):
    facts=[]
    for e in resolve(initial,snapshot['files']):
        if not e['available'] or e.get('syntax')=='parse_unavailable':
            facts.append((e['file'],e['qualified'],'unobserved' if snapshot.get('limited') and e.get('status')=='missing' else e.get('status','unknown')))
    # No assertion of deletion when an incomplete scan might omit a file.
    for path,d in sorted(delta.items()):
        if d['kind']=='missing':facts.append((path,'','unobserved' if snapshot.get('limited') else 'missing'))
    return sorted(set(facts))

def proposals(candidates,snapshot,issue,delta=None,variant='compact'):
    if variant not in CONFIG['variants']:raise ValueError('unknown frozen variant')
    delta=delta or {};out=[]
    # Preserve old lexical anchors and coherent 3/5/7-line context. R1 tiny
    # fragments spent more metadata and lost surrounding target evidence.
    for w in contiguous_proposals(candidates,snapshot['files'],issue):
        w=dict(w);changed=delta.get(w['file'],{}).get('ranges',[])
        w['changed_lines']=sum(max(0,min(w['end'],y)-max(w['start'],x)+1) for x,y in changed)
        w['score']+=8*min(w['changed_lines'],3);w['unit']='context'
        out.append(w)
    # New changes must be representable even far from the issue anchor.
    for rank,e in enumerate(resolve(candidates,snapshot['files'])):
        if not e['available']:continue
        lines=snapshot['files'][e['file']].splitlines(True);lo=e['start_line'];hi=e['end_line']
        for x,y in delta.get(e['file'],{}).get('ranges',[]):
            if not overlap((lo,hi),(x,y)):continue
            for size in [7,5,3,1]:
                a=max(lo,min(max(lo,x)-1,hi-size+1));b=min(hi,a+size-1)
                code=''.join(lines[a-1:b]);n=max(0,min(b,y)-max(a,x)+1)
                out.append(dict(file=e['file'],qualified=e['qualified'],entity_id=e['entity_id'],rank=rank,start=a,end=b,code=code,source_hash=sha(code),syntax=e.get('syntax','valid'),unit='context',score=8*min(n,3),changed_lines=n,partial=a!=lo or b!=hi,low_confidence=False))
    return sorted(out,key=lambda w:(-w['score'],w['rank'],w['file'],w['start'],-(w['end']-w['start'])))

def render(windows,limited=False,facts=(),status='initial'):
    # One global partial-window disclosure. Keep full paths, omit redundant end
    # coordinates and aliases; exact end/identity remain in verified source maps.
    parts=['[PI D2 '+status+' partial'+(' limited' if limited else '')+']\n'];lastpath=None
    for path,qualified,state in facts:
        parts.append('state '+path+('::'+qualified if qualified else '')+' '+state+'\n')
    for w in windows:
        path=w['file'];prefix=path if path!=lastpath else ''
        flags=' parse?' if w.get('syntax')=='parse_unavailable' else ''
        parts.append(prefix+':'+str(w['start'])+flags+'\n'+w['code']+('' if w['code'].endswith('\n') else '\n'))
        lastpath=path
    return ''.join(parts)

def serialize(candidates,snapshot,issue,tokenizer,*,budget=192,delta=None,variant='compact',facts=(),status='initial'):
    validate(snapshot)
    if budget<0 or budget>192:raise ValueError('per-state budget')
    # Status facts are bounded; never silently label omitted facts as known.
    kept_facts=[]
    for fact in facts:
        if len(tokenizer.encode(render([],snapshot.get('limited'),kept_facts+[fact],status),add_special_tokens=False))<=min(budget,max(48,budget//2)):kept_facts.append(fact)
    omitted_facts=len(kept_facts)<len(facts)
    effective_status=status+(' unknown_omitted' if omitted_facts else '')
    def text(ws):return render(ws,snapshot.get('limited'),kept_facts,effective_status)
    def cost(ws):return len(tokenizer.encode(text(ws),add_special_tokens=False))
    props=proposals(candidates,snapshot,issue,delta,variant);chosen=[]
    def admissible(w):return not any(w['file']==x['file'] and overlap((w['start'],w['end']),(x['start'],x['end'])) for x in chosen)
    # Equal candidate access before densifying; compare focused rule independently.
    if variant=='diverse':
        for entity in dict.fromkeys(e['entity_id'] for e in candidates):
            opts=[w for w in props if w['entity_id']==entity and admissible(w) and cost(chosen+[w])<=budget]
            if opts:
                opts.sort(key=lambda w:(-w['score']/max(1,cost(chosen+[w])-cost(chosen))**.5,w['start'],w['end']))
                chosen.append(opts[0])
    for w in props:
        if len(chosen)>=CONFIG['max_windows']:break
        if admissible(w) and cost(chosen+[w])<=budget:chosen.append(w)
    if not chosen:
        for w in props:
            code=w['code'].splitlines(True)[0]
            short=dict(w,end=w['start'],code=code,source_hash=sha(code),unit='line_fragment',partial=True)
            if cost([short])<=budget:chosen=[short];break
    if variant=='expand' and chosen:
        # Spend residual capacity on contiguous CURRENT source, never another
        # label-driven location. Lexical overlap prioritizes sides, then position.
        current={e['entity_id']:e for e in resolve(candidates,snapshot['files'])}
        q,_=query(issue)
        while True:
            options=[]
            for i,w in enumerate(chosen):
                e=current[w['entity_id']];lines=snapshot['files'][w['file']].splitlines(True)
                for a,b in [(w['start']-1,w['end']),(w['start'],w['end']+1)]:
                    if a<e['start_line'] or b>e['end_line']:continue
                    if any(j!=i and x['file']==w['file'] and overlap((a,b),(x['start'],x['end'])) for j,x in enumerate(chosen)):continue
                    code=''.join(lines[a-1:b]);nw=dict(w,start=a,end=b,code=code,source_hash=sha(code),partial=a!=e['start_line'] or b!=e['end_line'])
                    trial=chosen[:i]+[nw]+chosen[i+1:]
                    if cost(trial)>budget:continue
                    line=lines[a-1] if a<w['start'] else lines[b-1]
                    options.append((-len(terms(line)&q),cost(trial)-cost(chosen),w['rank'],a,i,nw))
            if not options:break
            _,_,_,_,i,nw=min(options,key=lambda z:z[:-1]);chosen[i]=nw
    payload=text(chosen)
    if not chosen and not facts:payload='[PI D1 unknown no_window_fits]\n'
    ids=tokenizer.encode(payload,add_special_tokens=False)
    if len(ids)>budget:raise ValueError('cannot fit explicit PI status')
    maps=[]
    for w in chosen:
        source=snapshot['files'][w['file']].splitlines(True)
        assert ''.join(source[w['start']-1:w['end']])==w['code']
        maps.append(dict(entity_id=w['entity_id'],file=w['file'],qualified=w['qualified'],path_only_visible=False,
            source_hash=sha(w['code']),file_sha=sha(snapshot['files'][w['file']]),
            pi_emitted_source_spans_W0=[dict(line=n,start_column=0,end_column=len(source[n-1].rstrip('\r\n').encode()),line_complete=True) for n in range(w['start'],w['end']+1)]))
    semantic=digest([[(w['file'],w['qualified'],w['code'],w['unit'],w['syntax']) for w in chosen],kept_facts,omitted_facts,snapshot.get('limited',False)])
    return dict(pi_text=payload,pi_ids=ids,pi_raw_tokens=len(ids),token_cap=budget,pi_truncated=True,
        source_map=maps,windows=chosen,unknown=not chosen or bool(facts) or omitted_facts,omitted=not chosen,
        semantic_hash=semantic,source_lines=sum(w['end']-w['start']+1 for w in chosen),
        metadata_tokens_standalone=len(tokenizer.encode(text([dict(w,code='') for w in chosen]),add_special_tokens=False)),
        source_tokens_standalone=len(tokenizer.encode(''.join(w['code'] for w in chosen),add_special_tokens=False)))

class DynamicSession:
    """Bounded private pre-action cache. Never serialized into training records."""
    def __init__(self,issue,tokenizer,task_uid,session_id,variant='compact'):
        self.issue=issue;self.tokenizer=tokenizer;self.identity=(task_uid,session_id);self.variant=variant
        self.initial=None;self.previous=None;self.remaining=4096;self.last=-1;self.seen=set();self.retry=None
        self.last_visible=None;self.exhausted=False
    def capture(self,snapshot,*,task_uid,session_id,logical_call_id,seq):
        validate(snapshot)
        if self.identity!=(task_uid,session_id):raise ValueError('cross-session')
        workspace=digest([snapshot['files'],snapshot.get('limited',False)])
        if self.retry and logical_call_id==self.retry[0]:
            if workspace!=self.retry[1]:raise ValueError('retry state changed')
            return copy.deepcopy(self.retry[2])
        if logical_call_id in self.seen or seq<=self.last:raise ValueError('nonmonotonic or late call')
        if len(self.seen)>=512:raise ValueError('logical call bound')
        first=self.initial is None
        if first:self.initial=build_initial_index(snapshot,self.issue,task_uid=task_uid,session_id=session_id)['focus']
        delta={} if first else changes(self.previous,snapshot['files'])
        candidates=self.initial if first else dynamic_candidates(self.initial,snapshot,delta,self.issue)
        facts=status_facts(self.initial,snapshot,delta)
        empty=dict(pi_text='',pi_ids=[],pi_raw_tokens=0,token_cap=0,source_map=[],windows=[],unknown=self.exhausted,omitted=self.exhausted,pi_truncated=self.exhausted)
        if self.exhausted or (not first and not delta and facts==getattr(self,'last_facts',None)):
            out=empty
        else:
            marker='[PI D1 exhausted current_state=unknown]\n';mids=self.tokenizer.encode(marker,add_special_tokens=False)
            if self.remaining<len(mids):raise ValueError('exhaustion reserve violated')
            budget=min(192 if first else 128,self.remaining-len(mids))
            minimum=len(self.tokenizer.encode('[PI D1 unknown no_window_fits]\n',add_special_tokens=False))
            if budget<minimum:
                out=dict(empty,pi_text=marker,pi_ids=mids,pi_raw_tokens=len(mids),unknown=True,omitted=True,pi_truncated=True)
                self.exhausted=True
            else:
                out=serialize(candidates,snapshot,self.issue,self.tokenizer,budget=budget,delta=delta,
                              variant=self.variant,facts=facts,status='initial' if first else 'current_change')
                if out['semantic_hash']==self.last_visible:out=empty
                else:self.last_visible=out['semantic_hash']
            self.remaining-=len(out['pi_ids'])
        self.previous=dict(snapshot['files']);self.last_facts=facts;self.last=seq;self.seen.add(logical_call_id)
        key=digest([self.last_visible,self.exhausted])
        out.update(session_id=session_id,state_seq=seq,state_hash=key,pi_insertion_key=key,
                   pre_action=True,valid=True,pi_format='icps_dynamic_v1',logical_call_id=logical_call_id)
        self.retry=(logical_call_id,workspace,copy.deepcopy(out))
        return out
