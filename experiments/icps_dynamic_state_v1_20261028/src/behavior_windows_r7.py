"""Source-only issue anchors and bounded AST relations; development prototype.

No execution, labels, learned weights or claim of semantic dataflow. Preserve
original score scale, cost/diversity and source rendering; never mutate runtime.
"""
import ast
import collections
import inspect
import re
import textwrap
from dense_state import proposals, validate
from executable_windows import line_signals
from window_serializer import resolve, query, sha
from window_research_r7 import serialize as original


def issue_symbols(issue):
    # Explicit code identifiers, calls, named functions and traceback frames.
    snippets=re.findall(r'`([^`\n]{1,200})`',issue)
    names={s.rsplit('.',1)[-1] for snippet in snippets for s in re.findall(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',snippet)}
    names.update(s.rsplit('.',1)[-1] for s in re.findall(r'\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(',issue))
    names.update(re.findall(r'\b(?:function|method|class)\s+([A-Za-z_]\w*)',issue))
    names.update(re.findall(r'line\s+\d+,\s+in\s+([A-Za-z_]\w*)',issue))
    return names-{'self','cls','print','str','int','list','dict','len','set','tuple'}


def own_nodes(root):
    stack=[root]
    while stack:
        n=stack.pop()
        if n is not root and isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)):
            continue
        yield n
        stack.extend(reversed(list(ast.iter_child_nodes(n))))


def names_in(node):
    return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and n.id not in {'self','cls'}}


def call_name(call):
    f=call.func
    return f.id if isinstance(f,ast.Name) else f.attr if isinstance(f,ast.Attribute) else None


def signals(candidates,snapshot,issue):
    entities=[e for e in resolve(candidates,snapshot['files']) if e['available']]
    symbols=issue_symbols(issue)
    by_name=collections.defaultdict(list)
    for e in entities:by_name[e['qualified'].rsplit('.',1)[-1]].append(e)
    explicit={e['entity_id'] for e in entities if e['qualified'].rsplit('.',1)[-1] in symbols}
    neighbors=set()
    for e in entities:
        if e['entity_id'] not in explicit or e.get('node') is None:continue
        for call in own_nodes(e['node']):
            if not isinstance(call,ast.Call):continue
            f=call.func
            static=isinstance(f,ast.Name) or (isinstance(f,ast.Attribute) and isinstance(f.value,ast.Name) and f.value.id in {'self','cls'})
            targets=by_name.get(call_name(call),[])
            if static and len(targets)==1:neighbors.add(targets[0]['entity_id'])
    normalized_issue=' '.join(issue.split())
    result={};summaries={}
    for e in entities:
        root=e.get('node');cue=collections.defaultdict(float);types=collections.Counter()
        if root is None:
            result[e['entity_id']]={};summaries[e['entity_id']]={};continue
        nodes=list(own_nodes(root));perline=collections.defaultdict(set);stores=collections.defaultdict(set)
        for n in nodes:
            if isinstance(n,ast.Name) and n.id not in {'self','cls'}:
                perline[n.lineno].add(n.id)
                if isinstance(n.ctx,ast.Store):stores[n.id].add(n.lineno)
        seeds=set()
        for node in nodes:
            hit=False
            if isinstance(node,ast.Call):
                name=call_name(node)
                targets=by_name.get(name,[])
                if name in symbols:
                    hit=True;types['explicit_call']+=1
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                value=' '.join(node.value.split())
                # Literal error text only; do not use docstrings as error anchors.
                if len(value)>=12 and value in normalized_issue and any(isinstance(x,(ast.Raise,ast.Call)) and x.lineno<=node.lineno<=x.end_lineno for x in nodes):
                    hit=True;types['literal_message']+=1
            if hit:
                cue[node.lineno]=max(cue[node.lineno],1.5);seeds.add(node.lineno)
        # Issue-named entities remain identity evidence even if body vocabulary
        # differs. It is a weak uniform prior, not a target-line assertion.
        prior=.5 if e['entity_id'] in explicit else .35 if e['entity_id'] in neighbors else 0.0
        if e['entity_id'] in neighbors:types['one_hop_callee']+=1
        for line in sorted(seeds):
            for name in sorted(perline[line]):
                earlier=[i for i in stores[name] if i<line]
                if earlier:
                    cue[max(earlier)]=max(cue[max(earlier)],.75);types['nearest_store']+=1
            for node in nodes:
                if isinstance(node,ast.If) and node.lineno<=line<=node.end_lineno and names_in(node.test)&perline[line]:
                    cue[node.lineno]=max(cue[node.lineno],1.0);types['enclosing_guard']+=1
                if isinstance(node,ast.Return) and node.lineno>=line and names_in(node)&perline[line]:
                    cue[node.lineno]=max(cue[node.lineno],.5);types['linked_return']+=1
        result[e['entity_id']]=dict(lines=dict(cue),prior=prior)
        summaries[e['entity_id']]=dict(types)
    return entities,result,summaries


def prepare(candidates,snapshot,issue,extend=False):
    validate(snapshot)
    props=proposals(candidates,snapshot,issue,variant='flow_expand')
    entities,cues,summary=signals(candidates,snapshot,issue)
    if extend:
        seen={(w['entity_id'],w['start'],w['end']) for w in props}
        ranks={e['entity_id']:i for i,e in enumerate(resolve(candidates,snapshot['files']))}
        for e in entities:
            info=cues[e['entity_id']]
            if not info:continue
            lines=snapshot['files'][e['file']].splitlines(True)
            lexical,_,_=line_signals(e,lines,issue,flow=True)
            anchors=sorted(info['lines'],key=lambda i:(-info['lines'][i],i))[:6]
            for anchor in anchors:
                for size in (7,5,3):
                    a=max(e['start_line'],min(anchor-2,e['end_line']-size+1));b=min(e['end_line'],a+size-1)
                    key=(e['entity_id'],a,b)
                    if key in seen:continue
                    seen.add(key);code=''.join(lines[a-1:b])
                    props.append(dict(file=e['file'],qualified=e['qualified'],entity_id=e['entity_id'],rank=ranks[e['entity_id']],
                        start=a,end=b,code=code,source_hash=sha(code),syntax=e.get('syntax','valid'),partial=a!=e['start_line'] or b!=e['end_line'],
                        low_confidence=False,score=lexical.get(anchor,0)+sum(lexical.get(i,0) for i in range(a,b+1))/(b-a+1),unit='context',changed_lines=0))
    def adjusted(w):
        info=cues.get(w['entity_id'],{})
        if not info:return w['score']
        values=[info['lines'].get(i,0) for i in range(w['start'],w['end']+1)]
        bonus=min(2.0,info['prior']+max(values,default=0)+sum(values)/max(1,len(values)))
        return w['score']*(1+.35*bonus)+.5*bonus
    return props,adjusted,summary


def serialize(candidates,snapshot,issue,tokenizer,*,budget=256,variant='rank'):
    if budget not in (256,384) or variant not in ('rank','extend'):raise ValueError('predeclared behavior arms only')
    props,adjusted,_=prepare(candidates,snapshot,issue,extend=variant=='extend')
    source=textwrap.dedent(inspect.getsource(original))
    for before,after in {
        'not budget == 256':'budget not in (256,384)',
        "props = proposals(candidates, snapshot, issue, variant='flow_expand')":'props = fixed_props',
        "marginal_score(w['score'],features,seen,trial_cost-prior_cost,variant)":'marginal_score(adjusted(w),features,seen,trial_cost-prior_cost,variant)',
    }.items():
        assert source.count(before)==1;source=source.replace(before,after)
    ns=dict(original.__globals__,fixed_props=props,adjusted=adjusted)
    exec(compile(source,'<R7-behavior-only>','exec'),ns)
    return ns['serialize'](candidates,snapshot,issue,tokenizer,budget=budget,variant='diverse6')
