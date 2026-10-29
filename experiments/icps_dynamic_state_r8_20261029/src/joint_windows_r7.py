"""Development-only global source-window search. Pure source/issue inputs.

Fixed width8 beam, max3 windows, actual rendered token costs. Scores are lexical
and syntactic heuristics, not calibrated relevance or proof of semantic utility.
"""
import ast
import collections
import copy
import math
from functools import lru_cache
from budget_ablation_r7 import clone_with_one_edit
from window_research_r7 import serialize as old_serialize
from window_serializer import resolve, query, terms, sha, digest
from dense_state import validate, proposals, render, overlap
from executable_windows import line_signals


@lru_cache(maxsize=1)
def budget_control():
    return clone_with_one_edit(old_serialize,'not budget == 256','budget not in (256,384)')


def close_range(a,b,entity,statements):
    """Expand only: close short intersecting statements, at most16 source lines."""
    while True:
        old=(a,b)
        for lo,hi in statements:
            if overlap((a,b),(lo,hi)) and (lo<a or hi>b):
                x,y=min(a,lo),max(b,hi)
                if y-x+1<=16:a,b=x,y
        if old==(a,b):return a,b


class Allocator:
    def __init__(self,candidates,snapshot,issue,tokenizer):
        validate(snapshot)
        self.candidates=candidates;self.snapshot=snapshot;self.issue=issue;self.tok=tokenizer
        self.entities={e['entity_id']:e for e in resolve(candidates,snapshot['files']) if e['available']}
        self.lines={p:t.splitlines(True) for p,t in snapshot['files'].items()}
        self.q,self.explicit=query(issue)
        self.scores={};self.statements={};df=collections.Counter()
        for eid,e in self.entities.items():
            scores,_,_=line_signals(e,self.lines[e['file']],issue,flow=True)
            self.scores[eid]=scores
            df.update(set().union(*(terms(self.lines[e['file']][i-1])&self.q for i in scores)))
            node=e.get('node');ss=[]
            if node:
                for n in ast.walk(node):
                    if not isinstance(n,ast.stmt) or isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):continue
                    if isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):continue
                    if n.end_lineno-n.lineno+1<=12:ss.append((n.lineno,n.end_lineno))
            self.statements[eid]=sorted(set(ss))
        self.weights={t:1+math.log((len(self.entities)+1)/(df[t]+1)) for t in self.q}
        self.props=proposals(candidates,snapshot,issue,variant='flow_expand')
        self.tokens={};self.bank_cache={};self.evidence_cache={}

    def text(self,ws):return render(ws,self.snapshot.get('limited',False))
    def cost(self,ws):
        text=self.text(ws)
        if text not in self.tokens:self.tokens[text]=len(self.tok.encode(text,add_special_tokens=False))
        return self.tokens[text]
    def canonical(self,ws):return sorted(ws,key=lambda w:(w['rank'],w['file'],w['start'],w['end']))
    def key(self,ws):return tuple((w['entity_id'],w['start'],w['end']) for w in self.canonical(ws))
    def update_window(self,w,a,b):
        e=self.entities[w['entity_id']];code=''.join(self.lines[w['file']][a-1:b])
        return dict(w,start=a,end=b,code=code,source_hash=sha(code),partial=a!=e['start_line'] or b!=e['end_line'])
    def evidence(self,w):
        key=(w['entity_id'],w['start'],w['end'],w['rank'])
        if key not in self.evidence_cache:
            scores=self.scores[w['entity_id']]
            inside=[i for i in scores if w['start']<=i<=w['end']]
            feature=set().union(*(terms(self.lines[w['file']][i-1])&self.q for i in inside))
            prior=.5+.5/math.sqrt(1+w['rank'])
            features={t:self.weights[t]*prior for t in feature}
            signal=max((scores[i] for i in inside),default=0)+sum(scores[i] for i in inside)/max(1,len(inside))
            self.evidence_cache[key]=(features,.25*signal/math.sqrt(1+w['rank']))
        return self.evidence_cache[key]
    def objective(self,ws):
        values=collections.defaultdict(list);local=0.;counts=collections.Counter()
        for w in self.canonical(ws):
            features,signal=self.evidence(w)
            for t,v in features.items():values[t].append(v)
            local+=signal/(1+counts[w['entity_id']]);counts[w['entity_id']]+=1
        return local+sum(max(v)+.25*(sum(v)-max(v)) for v in values.values())
    def bank(self,coherent):
        if coherent in self.bank_cache:return self.bank_cache[coherent]
        byid=collections.defaultdict(dict)
        for w in self.props:
            byid[w['entity_id']][(w['start'],w['end'])]=w
            if coherent:
                e=self.entities[w['entity_id']]
                a,b=close_range(w['start'],w['end'],e,self.statements[w['entity_id']])
                byid[w['entity_id']][(a,b)]=self.update_window(w,a,b)
                if e['end_line']-e['start_line']+1<=16:
                    a,b=e['start_line'],e['end_line'];byid[w['entity_id']][(a,b)]=self.update_window(w,a,b)
        out=[]
        for eid,choices in byid.items():
            ws=list(choices.values());costs={self.key([w]):self.cost([w]) for w in ws}
            value=lambda w:self.objective([w])
            key=lambda w:(-value(w),costs[self.key([w])],w['start'],w['end'])
            selected=[min(ws,key=key),min(ws,key=lambda w:(-value(w)/max(1,costs[self.key([w])])**.5,key(w)))]
            # Retain alternatives at different payload lengths instead of only
            # nearly-identical highest-scoring large windows. Four fixed bins.
            for ceiling in (48,96,160,384):
                opts=[w for w in ws if costs[self.key([w])]<=ceiling]
                if opts:selected.append(min(opts,key=key))
            if coherent:
                e=self.entities[eid]
                full=choices.get((e['start_line'],e['end_line']))
                if full is not None and e['end_line']-e['start_line']+1<=16:selected.append(full)
            seen=set()
            for w in selected:
                k=self.key([w])
                if k not in seen:out.append(w);seen.add(k)
        self.bank_cache[coherent]=self.canonical(out)
        return self.bank_cache[coherent]
    @staticmethod
    def admissible(ws,w):
        return not any(w['file']==x['file'] and overlap((w['start'],w['end']),(x['start'],x['end'])) for x in ws)
    def search(self,budget,coherent):
        bank=self.bank(coherent);beam=[[]];best=[]
        order=lambda ws:(-self.objective(ws),self.cost(ws),self.key(ws))
        for depth in range(3):
            trials={}
            for ws in beam:
                for w in bank:
                    if not self.admissible(ws,w):continue
                    candidate=self.canonical(ws+[w]);key=self.key(candidate)
                    if key not in trials and self.cost(candidate)<=budget:trials[key]=candidate
            if not trials:break
            beam=sorted(trials.values(),key=order)[:8]
            best=min([best]+beam,key=order)
        return copy.deepcopy(best)
    def expand(self,chosen,budget,coherent):
        while chosen:
            options=[];base=self.objective(chosen);oldcost=self.cost(chosen)
            for i,w in enumerate(chosen):
                e=self.entities[w['entity_id']]
                for a,b in [(w['start']-1,w['end']),(w['start'],w['end']+1)]:
                    if a<e['start_line'] or b>e['end_line']:continue
                    if coherent:a,b=close_range(a,b,e,self.statements[w['entity_id']])
                    nw=self.update_window(w,a,b)
                    others=chosen[:i]+chosen[i+1:]
                    if not self.admissible(others,nw):continue
                    trial=self.canonical(others+[nw]);cost=self.cost(trial)
                    if cost>budget:continue
                    gain=self.objective(trial)-base
                    options.append((-gain/max(1,cost-oldcost)**.5,cost-oldcost,self.key(trial),trial))
            if not options:break
            chosen=min(options,key=lambda x:x[:3])[-1]
        return chosen
    def serialize(self,*,budget=256,coherent=False):
        if budget not in (256,384):raise ValueError('declared budgets only')
        chosen=self.search(budget,coherent)
        if not chosen:return budget_control()(self.candidates,self.snapshot,self.issue,self.tok,budget=budget,variant='diverse6')
        chosen=self.expand(chosen,budget,coherent);payload=self.text(chosen)
        ids=self.tok.encode(payload,add_special_tokens=False);assert len(ids)<=budget
        maps=[]
        for w in chosen:
            lines=self.lines[w['file']];assert w['code']==''.join(lines[w['start']-1:w['end']])
            maps.append(dict(entity_id=w['entity_id'],file=w['file'],qualified=w['qualified'],path_only_visible=False,
                source_hash=sha(w['code']),file_sha=sha(self.snapshot['files'][w['file']]),
                pi_emitted_source_spans_W0=[dict(line=i,start_column=0,end_column=len(lines[i-1].rstrip('\r\n').encode()),line_complete=True) for i in range(w['start'],w['end']+1)]))
        return dict(pi_text=payload,pi_ids=ids,pi_raw_tokens=len(ids),token_cap=budget,pi_truncated=True,
            source_map=maps,windows=chosen,unknown=False,omitted=False,semantic_hash=digest([(w['file'],w['code']) for w in chosen]),
            source_lines=sum(w['end']-w['start']+1 for w in chosen),
            metadata_tokens_standalone=len(self.tok.encode(self.text([dict(w,code='') for w in chosen]),add_special_tokens=False)),
            source_tokens_standalone=len(self.tok.encode(''.join(w['code'] for w in chosen),add_special_tokens=False)))
