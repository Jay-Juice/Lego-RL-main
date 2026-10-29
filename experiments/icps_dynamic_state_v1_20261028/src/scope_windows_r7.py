"""Development-only scope-local proposals from the SAME retrieved candidates.

No IO, extra retrieval, labels, execution, neural model or persistent source cache.
Class candidates are partitioned into methods and remaining contiguous class
regions. This is syntactic ownership, not a semantic relevance guarantee.
"""
import ast
import functools
import inspect
import textwrap
import types
import entity_evidence_r7 as base
from executable_windows import line_signals
from window_serializer import sha

ARMS={m:(1024,8) for m in ('control1024_8','scope1024_8','balanced1024_8')}
MeteredCache=base.MeteredCache


def scope_key(w):
    return w.get('scope_id',w['entity_id'])


def bounded(entity,w):
    return dict(entity,start_line=w.get('scope_start',entity['start_line']),
                end_line=w.get('scope_end',entity['end_line']))


def units(entity):
    """Partition class-owned text, retaining class-level executable gaps."""
    def split(node,lo,hi,name):
        if not isinstance(node,ast.ClassDef):
            yield lo,hi,name,node
            return
        cursor=lo
        for child in node.body:
            if not isinstance(child,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):continue
            start=min([child.lineno]+[d.lineno for d in child.decorator_list])
            if cursor<start:yield cursor,start-1,name,None
            yield from split(child,start,child.end_lineno,name+'.'+child.name)
            cursor=child.end_lineno+1
        if cursor<=hi:yield cursor,hi,name,None
    yield from split(entity.get('node'),entity['start_line'],entity['end_line'],entity['qualified'])


def scope_proposals(entities,files,issue,balanced=False,signal_func=line_signals):
    out=[];lines_cache={}
    for rank,e in enumerate(entities):
        if not e['available']:continue
        if e['file'] not in lines_cache:lines_cache[e['file']]=files[e['file']].splitlines(True)
        lines=lines_cache[e['file']]
        groups=[]
        for lo,hi,name,node in units(e):
            unit=dict(e,start_line=lo,end_line=hi,node=node,qualified=name)
            scores,_,_=signal_func(unit,lines,issue,flow=True)
            positive=[i for i in scores if scores[i]>0]
            anchors=sorted(positive,key=lambda i:(-scores[i],i))[:12]
            if not anchors:
                executable=sorted(scores)
                anchors=[executable[0],executable[len(executable)//2]] if executable else [lo]
            rows=[];seen=set()
            for anchor in anchors:
                for size in (7,5,3):
                    a=max(lo,min(anchor-2,hi-size+1));b=min(hi,a+size-1)
                    if (a,b) in seen:continue
                    seen.add((a,b));code=''.join(lines[a-1:b]);strength=scores.get(anchor,0)
                    rows.append(dict(file=e['file'],qualified=e['qualified'],entity_id=e['entity_id'],rank=rank,
                        start=a,end=b,code=code,source_hash=sha(code),syntax=e.get('syntax','valid'),
                        partial=a!=lo or b!=hi,low_confidence=strength==0,
                        score=strength+sum(scores.get(i,0) for i in range(a,b+1))/(b-a+1),
                        unit='context',changed_lines=0,scope_start=lo,scope_end=hi,scope_qualified=name,
                        scope_id=(e['file'],name,lo,hi)))
            rows.sort(key=lambda w:(-w['score'],w['start'],-(w['end']-w['start'])))
            if rows:groups.append(rows)
        # Same upper bound as original 12 anchors x 3 lengths per candidate.
        key=lambda w:(-w['score'],w['start'],-(w['end']-w['start']))
        if balanced:
            pool=[]
            for depth in range(36):
                layer=sorted((g[depth] for g in groups if len(g)>depth),key=key)
                pool.extend(layer[:36-len(pool)])
                if len(pool)==36:break
        else:pool=sorted((w for g in groups for w in g),key=key)[:36]
        out.extend(pool)
    return sorted(out,key=lambda w:(-w['score'],w['rank'],w['file'],w['start'],-(w['end']-w['start'])))


@functools.lru_cache(maxsize=1)
def scoped_template():
    source=textwrap.dedent(inspect.getsource(base.template.__wrapped__))
    insertion="""    edits.update({
        "e = current[w['entity_id']]; lines = snapshot['files'][w['file']].splitlines(True)":
            "e = bounded(current[w['entity_id']],w); lines = snapshot['files'][w['file']].splitlines(True)",
        "utility /= 1+sum(x['entity_id']==w['entity_id'] for x in chosen)":
            "utility /= 1+sum(scope_key(x)==scope_key(w) for x in chosen)",
    })
"""
    # Existing template also replaces the splitlines clause. Apply ownership
    # after that replacement, avoiding overlapping edit keys.
    insertion=insertion.replace("snapshot['files'][w['file']].splitlines(True)","file_lines(w['file'])")
    source=source.replace('    for before,after in edits.items():',insertion+'    for before,after in edits.items():')
    source=source.replace('@functools.lru_cache(maxsize=1)\n','')
    ns=dict(base.__dict__);exec(compile(source,'<R7-scope-template>','exec'),ns)
    return ns['template']()


@functools.lru_cache(maxsize=1)
def implementation():
    source=textwrap.dedent(inspect.getsource(base.serialize))
    changes={
        "if arm not in ARMS:":"if arm not in ARMS:",
        "if arm=='control1024_8':":"if False:",
        " if arm!='cached1024_8' else ":" if False else ",
        "if arm=='cached1024_8':return 1":"if True:return 1",
        "rows=[dict(w,changed_lines=0,unit='context') for w in make_props(c,s['files'],i,flow=True)]":
            "rows=scope_proposals(entities,s['files'],i,balanced=arm=='balanced1024_8',signal_func=signals)",
        "order_ns=dict(candidate_order.__globals__,terms=cached_terms,factor=factor)":
            "order_source=order_source.replace(\"x['entity_id']==w['entity_id']\",\"scope_key(x)==scope_key(w)\")\n    order_ns=dict(candidate_order.__globals__,terms=cached_terms,factor=factor,scope_key=scope_key)",
        "e=current[w['entity_id']];lines=file_lines(w['file'])":
            "e=bounded(current[w['entity_id']],w);lines=file_lines(w['file'])",
        "prefetch_expansions=prefetch_expansions,experimental_serializer=lambda:old_fallback)":
            "prefetch_expansions=prefetch_expansions,experimental_serializer=lambda:old_fallback,scope_key=scope_key,bounded=bounded)",
        "exec(template(),ns)":"exec(scoped_template(),ns)",
    }
    for a,b in changes.items():
        assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
    ns=dict(base.__dict__,ARMS=ARMS,scope_proposals=scope_proposals,scope_key=scope_key,bounded=bounded,scoped_template=scoped_template)
    exec(compile(source,'<R7-scope-local-constructor>','exec'),ns)
    return ns['serialize']


def serialize(candidates,snapshot,issue,tokenizer,*,arm):
    if arm not in ARMS:raise ValueError('predeclared scope arm')
    if arm=='control1024_8':return base.serialize(candidates,snapshot,issue,tokenizer,arm='cached1024_8')
    return implementation()(candidates,snapshot,issue,tokenizer,arm=arm)
