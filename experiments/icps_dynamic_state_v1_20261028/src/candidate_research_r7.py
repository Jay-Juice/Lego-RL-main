"""Issue/source-only candidate experiments; no runtime changes or target labels."""
import ast
import collections
import copy
import math
import posixpath
import re
import issue_program_state as index
from budget_ablation_r7 import clone_with_one_edit

ARMS = ('base6', 'pool12', 'files12', 'symbols12', 'links12')


def header_order(entities, issue):
    """Independent short-document BM25 channel; no source bodies in this channel."""
    docs = [collections.Counter(index.words(e['file']+' '+e['qualified']+' '+e['signature'])) for e in entities]
    df = collections.Counter(t for doc in docs for t in doc)
    query = set(index.words(issue)); n = len(docs)
    average = sum(sum(doc.values()) for doc in docs)/max(1,n)
    scored = []
    for e, doc in zip(entities, docs):
        score = 0.0
        for term in query:
            tf = doc.get(term,0)
            if tf:
                score += math.log(1+(n-df[term]+.5)/(df[term]+.5))*tf*2.2/(tf+1.2*(.25+.75*sum(doc.values())/max(1,average)))
        if score > 0: scored.append((-score,index.digest([e['file'],e['qualified']]),e))
    return [e for _,_,e in sorted(scored,key=lambda x:x[:2])]


def static_edges(entities, files):
    """Syntactic candidates, never claims about actual Python runtime dispatch.

    Resolve unique module paths, explicit imports, bare same-module functions,
    self/cls member calls and imported module attributes. Ambiguity is omitted.
    """
    byid = {e['entity_id']:e for e in entities if not e.get('ambiguous')}
    defs = collections.defaultdict(list)
    modules = collections.defaultdict(list)
    for e in byid.values(): defs[e['file'],e['qualified']].append(e['entity_id'])
    for path in files:
        module = path[:-3].replace('/','.')
        if module.endswith('.__init__'): module=module[:-9]
        modules[module].append(path)
    def locate(module):
        exact=modules.get(module,[])
        matches=exact or [p for name,ps in modules.items() if name.endswith('.'+module) for p in ps]
        return matches[0] if len(matches)==1 else None
    imports={}
    for path,source in files.items():
        try: tree=ast.parse(source)
        except (SyntaxError,ValueError,RecursionError): continue
        names=collections.defaultdict(list)
        package=posixpath.dirname(path).split('/')
        for node in tree.body:
            if isinstance(node,ast.ImportFrom):
                parts=(package[:len(package)-node.level+1] if node.level else [])
                module='.'.join(parts+([node.module] if node.module else []))
                target=locate(module)
                if target:
                    for alias in node.names:
                        if alias.name!='*': names[alias.asname or alias.name].append((target,alias.name))
            elif isinstance(node,ast.Import):
                for alias in node.names:
                    target=locate(alias.name)
                    if target: names[alias.asname or alias.name].append((target,''))
        imports[path]={k:v[0] for k,v in names.items() if len(v)==1}
    edges=set()
    for e in byid.values():
        features=e.get('features') or {}; path=e['file']
        for call in features.get('calls',[]):
            target=None
            if re.fullmatch(r'[A-Za-z_]\w*',call) and call not in features.get('bound',[]):
                target=(path,call)
                if call in imports.get(path,{}): target=imports[path][call]
            elif call.startswith(('self.','cls.')) and e['qualified'].count('.')>=1 and call.count('.')==1:
                target=(path,e['qualified'].rsplit('.',1)[0]+'.'+call.split('.')[1])
            else:
                for alias,(target_path,symbol) in imports.get(path,{}).items():
                    if call.startswith(alias+'.'):
                        target=(target_path,'.'.join(x for x in [symbol,call[len(alias)+1:]] if x))
                        break
            ids=defs.get(target,[])
            if len(ids)==1 and ids[0]!=e['entity_id']: edges.add((e['entity_id'],ids[0]))
    return sorted(edges)


def build(snapshot, issue, *, task_uid, session_id):
    parsed={}
    def parse(path,source):
        if path not in parsed: parsed[path]=index.parse_file(path,source)
        return parsed[path]
    # Identical original ranking with no truncation; omit unused dynamic-state work.
    builder=clone_with_one_edit(index.build_initial_index,'selected=ranked[:3]',
                               'selected=ranked',{'parse_file':parse,'extract_current_impact':lambda *a,**k:{}})
    original=builder(snapshot,issue,task_uid=task_uid,session_id=session_id)
    ranked=original['focus']; all_entities=[e for es in parsed.values() for e in es if not e.get('ambiguous')]
    lexical_rank={e['entity_id']:i for i,e in enumerate(ranked)}
    byid={e['entity_id']:e for e in all_entities}
    chosen={'base6':ranked[:6],'pool12':ranked[:12]}
    # Keep top three original anchors; subsequent choices spread file exposure.
    picked=list(ranked[:3]); remaining=list(ranked[3:])
    while remaining and len(picked)<12:
        counts=collections.Counter(e['file'] for e in picked)
        e=min(remaining,key=lambda e:(-e['tier'],-e['retrieval_score']/(1+counts[e['file']]),lexical_rank[e['entity_id']]))
        picked.append(e);remaining.remove(e)
    chosen['files12']=picked
    headers=header_order(all_entities,issue)
    header_rank={e['entity_id']:i for i,e in enumerate(headers)}
    fusion={eid:1/(60+i+1) for eid,i in lexical_rank.items()}
    for eid,i in header_rank.items(): fusion[eid]=fusion.get(eid,0)+1/(60+i+1)
    picked=list(ranked[:3]); used={e['entity_id'] for e in picked}
    fused=sorted(fusion,key=lambda eid:(-fusion[eid],index.digest([byid[eid]['file'],byid[eid]['qualified']])))
    picked.extend(byid[eid] for eid in fused if eid not in used)
    chosen['symbols12']=picked[:12]
    edges=static_edges(all_entities,snapshot['files'])
    seeds={e['entity_id']:i for i,e in enumerate(ranked[:6])}; neighbors={}
    for caller,callee in edges:
        for seed,other in ((caller,callee),(callee,caller)):
            if seed in seeds and other not in seeds:
                neighbors[other]=min(neighbors.get(other,99),seeds[seed])
    ordered=sorted(neighbors,key=lambda eid:(neighbors[eid],lexical_rank.get(eid,len(ranked)),eid))
    picked=list(ranked[:6]);picked.extend(byid[eid] for eid in ordered[:6])
    used={e['entity_id'] for e in picked}
    picked.extend(e for e in ranked if e['entity_id'] not in used)
    chosen['links12']=picked[:12]
    assert all(len(v)<=12 and len({e['entity_id'] for e in v})==len(v) for v in chosen.values())
    return copy.deepcopy(chosen),dict(indexed_entities=len(all_entities),ranked_entities=len(ranked),
        static_edges=len(edges),seed_neighbors=len(neighbors),source_files=len(snapshot['files']))
