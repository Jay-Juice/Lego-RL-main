"""Issue-only contiguous source windows. No filesystem, label, model or scorer access.

Config frozen before evaluating any split. R0 candidate input is never reranked.
All retained code is whole original file lines, with explicit partial-window flags.
"""
import ast, collections, hashlib, json, math, re, time

CONFIG = dict(version='icps_window_v11', lengths=[7,5,3], max_windows=3,
              exact_weight=3, split_weight=1, anchor_radius=2,
              initial_budget=192, update_budget=128, episode_budget=4096,
              selection='best issue overlap per line, then candidate rank, coordinate',
              control='same allocator; candidate midpoint, then head; no issue read',
              frozen_before_any_labels=True, tuning_rounds=0)
STOP=set('a an the and or of in on for to with from is are be by this that it its as at not all any can should must you your we our code python repository issue fix bug task file function method class test tests use using please working work change implement return returns none true false def self cls when if then else also has have was were would could does do into than but'.split())
def sha(x):return hashlib.sha256(x.encode()).hexdigest()
def digest(x):return sha(json.dumps(x,sort_keys=True,ensure_ascii=True))
def terms(x):
    return {w.lower() for w in re.findall(r'[A-Za-z][A-Za-z0-9]*',re.sub(r'([a-z])([A-Z])',r'\1 \2',x)) if len(w)>1 and w.lower() not in STOP and not re.fullmatch('[a-fA-F0-9]{8,}',w)}
def query(issue):
    explicit=set(re.findall(r'`([A-Za-z_][\w.]*)`',issue))|set(re.findall(r'\b(?:function|method|class)\s+([A-Za-z_][\w.]*)',issue))
    explicit|={x.split('.')[-1] for x in explicit}
    return terms(issue),{x.lower() for x in explicit if x.lower() not in STOP}

def resolve(candidates,files):
    """Resolve fixed qualified identities in CURRENT files, never old line fallback."""
    trees={};out=[]
    for old in candidates:
        e=dict(old);path=e['file'];s=files.get(path)
        if s is None:e.update(status='missing',available=False);out.append(e);continue
        if path not in trees:
            try:
                tree=ast.parse(s);nodes={};scope=[]
                class Visitor(ast.NodeVisitor):
                    def item(self,n):
                        name='.'.join(scope+[n.name]);nodes.setdefault(name,[]).append(n);scope.append(n.name);self.generic_visit(n);scope.pop()
                    visit_FunctionDef=item;visit_AsyncFunctionDef=item;visit_ClassDef=item
                Visitor().visit(tree);trees[path]=(tree,nodes)
            except (SyntaxError,ValueError,RecursionError):trees[path]=(None,{})
        tree,nodes=trees[path];nn=nodes.get(e['qualified'],[])
        if tree is None:
            # Lexical fallback is explicitly current-file and parse-unavailable.
            e.update(status='parse_unavailable',syntax='parse_unavailable',available=True,
                     start_line=1,end_line=len(s.splitlines()),node=None)
        elif len(nn)!=1:e.update(status='identity_unresolved',available=False)
        else:
            n=nn[0];e.update(status='available',available=True,start_line=n.lineno,end_line=n.end_lineno,node=n)
        out.append(e)
    return out

def proposals(candidates,files,issue,control=False):
    q,explicit=(set(),set()) if control else query(issue)
    out=[]
    for rank,e in enumerate(resolve(candidates,files)):
        if not e['available']:continue
        lines=files[e['file']].splitlines(keepends=True);lo=e['start_line'];hi=e['end_line']
        if hi<lo:continue
        node=e.get('node');statement_ends={}
        if node:
            for n in ast.walk(node):
                if isinstance(n,ast.stmt) and lo<=n.lineno<=hi:
                    statement_ends[n.lineno]=max(statement_ends.get(n.lineno,n.lineno),n.end_lineno)
        df=collections.Counter(w for line in lines[lo-1:hi] for w in terms(line))
        def score(n):
            line=lines[n-1];ts=terms(line)
            ids={v.lower() for v in re.findall(r'[A-Za-z_]\w*',line)}
            exact=len(ids&explicit)
            overlap=sum(1/math.sqrt(df[t]) for t in ts&q)
            return CONFIG['exact_weight']*exact+overlap
        if control:anchors=[((lo+hi)//2,1), (lo,.5)]
        else:
            scored=[(n,score(n)) for n in range(lo,hi+1)]
            positive=[x for x in scored if x[1]>0]
            anchors=sorted(positive,key=lambda x:(-x[1],x[0]))[:12] if positive else [(lo,0),((lo+hi)//2,0)]
        seen=set()
        for anchor,strength in anchors:
            for size in CONFIG['lengths']:
                a=max(lo,min(anchor-CONFIG['anchor_radius'],hi-size+1));b=min(hi,a+size-1)
                # Do not expand a giant block. Explicit partial status is carried.
                end=statement_ends.get(anchor,anchor)
                if end>b and end-a<7:b=end
                if (a,b) in seen:continue
                seen.add((a,b));code=''.join(lines[a-1:b]);coverage=sum(score(n) for n in range(a,b+1)) if not control else 0
                out.append(dict(file=e['file'],qualified=e['qualified'],entity_id=e['entity_id'],rank=rank,
                    start=a,end=b,code=code,score=strength+coverage/max(1,b-a+1),
                    low_confidence=strength==0 and not control,partial=a!=lo or b!=hi,
                    syntax=e.get('syntax','valid'),file_sha=sha(files[e['file']]),
                    source_hash=sha(code),statement_partial=bool(end>b),control=control))
    # R0 pool unchanged. Within-pool windows are ordered by overlap, rank and source.
    return sorted(out,key=lambda w:((w['rank'] if control else -w['score']),w['rank'],w['file'],w['start'],-(w['end']-w['start'])))

def serialize(candidates,snapshot,issue,tokenizer,*,budget=192,control=False,status='initial'):
    started=time.perf_counter();cpu=time.process_time()
    assert budget>=0 and budget<=256
    header='[ICPS1.1 '+status+(' limited' if snapshot.get('limited') else '')+']\n'
    selected=[];windows=[]
    def render(ws):
        return header+''.join('WINDOW '+w['file']+':'+str(w['start'])+'-'+str(w['end'])+(' partial' if w['partial'] else '')+(' low' if w['low_confidence'] else '')+(' parse?' if w['syntax']!='valid' else '')+'\n'+w['code']+('' if w['code'].endswith('\n') else '\n') for w in ws)
    if not snapshot.get('stable'):
        text='[ICPS1.1 unknown unstable_source]';ids=tokenizer.encode(text,add_special_tokens=False)
        return dict(pi_text=text if len(ids)<=budget else '',pi_ids=ids if len(ids)<=budget else [],source_map=[],windows=[],unknown=True,token_cap=budget,pi_truncated=True,omitted=True)
    props=proposals(candidates,snapshot['files'],issue,control)
    for w in props:
        if len(windows)>=CONFIG['max_windows']:break
        if any(w['file']==old['file'] and max(w['start'],old['start'])<=min(w['end'],old['end']) for old in windows):continue
        trial=render(windows+[w]);ids=tokenizer.encode(trial,add_special_tokens=False)
        if len(ids)<=budget:windows.append(w)
    # Minimal contiguous fallback only after all 3/5/7-line windows failed to fit.
    if not windows:
        for p in props:
            lines=p['code'].splitlines(keepends=True)
            if not lines:continue
            w=dict(p,end=p['start'],code=lines[0],partial=True,statement_partial=True)
            if len(tokenizer.encode(render([w]),add_special_tokens=False))<=budget:windows=[w];break
    text=render(windows) if windows else '[ICPS1.1 unknown no_window_fits_or_no_candidate]'
    ids=tokenizer.encode(text,add_special_tokens=False)
    if len(ids)>budget:text='';ids=[]
    maps=[]
    for w in windows:
        original=snapshot['files'][w['file']].splitlines(keepends=True)
        assert w['code']==''.join(original[w['start']-1:w['end']])
        maps.append(dict(entity_id=w['entity_id'],file=w['file'],qualified=w['qualified'],path_only_visible=False,
            file_sha=w['file_sha'],source_hash=w['source_hash'],pi_emitted_source_spans_W0=[dict(line=n,start_column=0,end_column=len(original[n-1].rstrip('\r\n').encode()),line_complete=True) for n in range(w['start'],w['end']+1)]))
    code=''.join(w['code'] for w in windows)
    metadata=header+''.join('WINDOW '+w['file']+':'+str(w['start'])+'-'+str(w['end'])+(' partial' if w['partial'] else '')+(' low' if w['low_confidence'] else '')+(' parse?' if w['syntax']!='valid' else '')+'\n' for w in windows)
    return dict(pi_text=text,pi_ids=ids,source_map=maps,windows=windows,token_cap=budget,
        pi_raw_tokens=len(ids),pi_truncated=any(w['partial'] for w in windows) or len(windows)<len(candidates),omitted=not windows,
        source_tokens_standalone=len(tokenizer.encode(code,add_special_tokens=False)),metadata_tokens_standalone=len(tokenizer.encode(metadata,add_special_tokens=False)),
        source_lines=sum(w['end']-w['start']+1 for w in windows),files_visible=len({w['file'] for w in windows}),
        wall_seconds=time.perf_counter()-started,CPU_seconds=time.process_time()-cpu,unknown=not windows)

class WindowSession:
    """Bounded per-session state; caller owns current pre-action snapshot only."""
    def __init__(self,candidates,issue,tokenizer,task_uid,session_id,initial_budget=192):
        self.candidates=candidates;self.issue=issue;self.tokenizer=tokenizer;self.identity=(task_uid,session_id)
        self.previous=None;self.remaining=4096;self.last=-1;self.retries={};self.initial_budget=initial_budget
        self.exhausted=False
        self.seen=set()
    def capture(self,snapshot,*,task_uid,session_id,logical_call_id,seq):
        if (task_uid,session_id)!=self.identity:raise ValueError('cross-session')
        if seq<self.last:raise ValueError('nonmonotonic call')
        files=snapshot['files'];resolved=resolve(self.candidates,files)
        facts=[]
        for e in resolved:
            code=''.join(files[e['file']].splitlines(True)[e['start_line']-1:e['end_line']]) if e['available'] else None
            facts.append((e['entity_id'],e['status'],e.get('start_line'),e.get('end_line'),sha(code) if code is not None else None))
        h=digest([facts,snapshot.get('stable'),snapshot.get('limited')])
        if logical_call_id in self.retries:
            old=self.retries[logical_call_id]
            if old['state_hash']!=h:raise ValueError('retry pre-state changed')
            return old
        if logical_call_id in self.seen:raise ValueError('late retry outside current payload cache')
        if len(self.seen)>=512:raise ValueError('bounded logical-call identity ledger exhausted')
        first=self.previous is None
        unchanged=h==self.previous and snapshot.get('stable')
        if unchanged or self.exhausted:r=dict(pi_text='',pi_ids=[],source_map=[],windows=[],unknown=self.exhausted or snapshot.get('limited',False),omitted=self.exhausted,pi_truncated=self.exhausted,token_cap=0,pi_raw_tokens=0)
        elif not first and self.remaining<=64:
            text='[ICPS1.1 exhausted later_state=unknown]';ids=self.tokenizer.encode(text,add_special_tokens=False)
            if len(ids)>self.remaining:raise ValueError('cannot fit explicit exhaustion marker')
            r=dict(pi_text=text,pi_ids=ids,source_map=[],windows=[],unknown=True,omitted=True,pi_truncated=True,token_cap=64,pi_raw_tokens=len(ids));self.exhausted=True
        else:
            budget=min(self.initial_budget if first else 128,max(0,self.remaining-64))
            r=serialize(self.candidates,snapshot,self.issue,self.tokenizer,budget=budget,status='initial' if first else 'current_changed_or_unknown')
        self.remaining-=len(r['pi_ids']);self.previous=h;self.last=seq
        insertion=digest([h,'budget_exhausted_marker']) if r['pi_text']=='[ICPS1.1 exhausted later_state=unknown]' else h
        r.update(state_hash=h,session_id=session_id,task_uid=task_uid,logical_call_id=logical_call_id,state_seq=seq,
                 pi_format='icps_window_v11',pi_insertion_key=insertion,pre_action=True,valid=True)
        # Bounded metadata cache; token payload lifetime is caller/batch controlled.
        self.retries={logical_call_id:r}
        self.seen.add(logical_call_id)
        return r
    def release(self):
        self.retries.clear();self.candidates=[];self.issue='';self.previous=None
        self.seen.clear()
