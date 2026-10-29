"""Current changed-unit windows. Source-only, bounded, no retrieval/model IO."""
import ast
import heapq
from dense_state import validate, render, digest, sha, query, terms

MAX_UNITS = 128
MAX_WINDOWS = 3


def units(snapshot, delta, issue):
    result=[]
    q,_=query(issue)
    for path,change in sorted(delta.items()):
        if path not in snapshot['files']:continue
        source=snapshot['files'][path];lines=source.splitlines(True)
        if not lines:continue
        candidates=[];parse_failed=False
        try:
            tree=ast.parse(source)
            def add(node,name):
                start=min([node.lineno]+[d.lineno for d in getattr(node,'decorator_list',[])])
                candidates.append((start,node.end_lineno,name,'valid'))
            def walk(node,scope=''):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                        name=scope+'.'+child.name if scope else child.name
                        add(child,name);walk(child,name)
                    else:walk(child,scope)
            walk(tree)
            for i,node in enumerate(tree.body):
                if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                    add(node,'<module:'+str(i)+'>')
        except (SyntaxError,ValueError,RecursionError):
            candidates=[];parse_failed=True
        # Sweep source intervals. Each changed span can own several distinct
        # units; decorators belong to their definition, nested methods beat class.
        events={};points=set()
        for i,(a,b,_,_) in enumerate(candidates):
            events.setdefault(a,[]).append(i);points.update((a,b+1))
        ranges=[(max(1,a),min(len(lines),b)) for a,b in change['ranges'] if a<=len(lines)]
        for a,b in ranges:points.update((a,b+1))
        boundaries=sorted(points);active=[];owned={};ri=0
        for a,bound in zip(boundaries,boundaries[1:]):
            for i in events.get(a,[]):
                lo,hi,_,_=candidates[i];heapq.heappush(active,(hi-lo,lo,i,hi))
            while active and active[0][3]<a:heapq.heappop(active)
            while ri<len(ranges) and ranges[ri][1]<a:ri+=1
            if ri>=len(ranges) or not(ranges[ri][0]<=a<=ranges[ri][1]):continue
            b=min(bound-1,ranges[ri][1])
            key=active[0][2] if active else ('raw',a,b)
            owned.setdefault(key,[]).append((a,b))
        for key,spans in owned.items():
            if isinstance(key,int):lo,hi,name,syntax=candidates[key]
            else:
                lo,hi=spans[0][0],spans[-1][1];name='<changed-source>';syntax='parse_unavailable' if parse_failed else 'valid'
                if not ''.join(lines[lo-1:hi]).strip():continue
            result.append(dict(file=path,qualified=name,start_line=lo,end_line=hi,
                entity_id=digest([path,name,lo,hi])[:16],syntax=syntax,spans=spans,
                relevance=len(terms(''.join(lines[lo-1:hi]))&q)))
    result.sort(key=lambda e:(-e['relevance'],e['file'],e['start_line'],e['end_line']))
    return result[:MAX_UNITS],len(result)>MAX_UNITS


def serialize(snapshot,delta,issue,tokenizer,*,budget,facts=()):
    validate(snapshot)
    if not 0<=budget<=128:raise ValueError('R8 update cap')
    candidates,capped=units(snapshot,delta,issue)
    chosen=[];kept=[];q,_=query(issue)
    # Reserve explicit disclosure rather than silently claiming complete state.
    status='current_change partial_observation'
    def text(ws):return render(ws,snapshot.get('limited',False),kept,status)
    def fits(ws):return len(tokenizer.encode(text(ws),add_special_tokens=False))<=budget
    for f in facts:
        kept.append(f)
        if len(tokenizer.encode(text([]),add_special_tokens=False))>min(48,budget//2):kept.pop()
    def window(e,a,b):
        code=''.join(snapshot['files'][e['file']].splitlines(True)[a-1:b])
        return dict(file=e['file'],qualified=e['qualified'],entity_id=e['entity_id'],
            start=a,end=b,code=code,source_hash=sha(code),syntax=e['syntax'],
            unit='changed_source',partial=(a,b)!=(e['start_line'],e['end_line']))
    # Give distinct changed owners a seed before growing any context. Seeds are
    # complete physical lines, not token slices; long lines may be omitted.
    for e in candidates:
        if len(chosen)>=MAX_WINDOWS:break
        a=e['spans'][0][0];w=window(e,a,a)
        if any(w['file']==x['file'] and x['start']<=a<=x['end'] for x in chosen):continue
        if fits(chosen+[w]):chosen.append(w)
    current={e['entity_id']:e for e in candidates}
    while chosen:
        options=[]
        for i,w in enumerate(chosen):
            e=current[w['entity_id']]
            for a,b in [(w['start']-1,w['end']),(w['start'],w['end']+1)]:
                if a<e['start_line'] or b>e['end_line']:continue
                if any(i!=j and w['file']==x['file'] and max(a,x['start'])<=min(b,x['end']) for j,x in enumerate(chosen)):continue
                nw=window(e,a,b);trial=chosen[:i]+[nw]+chosen[i+1:]
                if not fits(trial):continue
                line=a if a<w['start'] else b
                changed=any(lo<=line<=hi for lo,hi in e['spans'])
                options.append((-int(changed),-len(terms(nw['code'])&q),len(tokenizer.encode(text(trial),add_special_tokens=False)),i,a,nw))
        if not options:break
        *_,i,a,w=min(options,key=lambda x:x[:-1]);chosen[i]=w
    represented={w['entity_id'] for w in chosen}
    omitted=capped or len(represented)<len(candidates) or len(kept)<len(facts)
    payload=text(chosen)
    if not chosen and not kept:payload='[PI D1 unknown changed_source_omitted]\n'
    ids=tokenizer.encode(payload,add_special_tokens=False)
    if len(ids)>budget:raise ValueError('cannot fit current-state disclosure')
    maps=[]
    for w in chosen:
        lines=snapshot['files'][w['file']].splitlines(True)
        maps.append(dict(entity_id=w['entity_id'],file=w['file'],qualified=w['qualified'],
            source_hash=sha(w['code']),file_sha=sha(snapshot['files'][w['file']]),path_only_visible=False,
            pi_emitted_source_spans_W0=[dict(line=n,start_column=0,end_column=len(lines[n-1].rstrip('\r\n').encode()),line_complete=True) for n in range(w['start'],w['end']+1)]))
    return dict(pi_text=payload,pi_ids=ids,pi_raw_tokens=len(ids),token_cap=budget,
        source_map=maps,windows=chosen,unknown=omitted or not chosen or bool(facts),omitted=omitted or not chosen,
        pi_truncated=True,semantic_hash=digest([chosen,kept,omitted,snapshot.get('limited',False)]),
        source_lines=sum(w['end']-w['start']+1 for w in chosen))
