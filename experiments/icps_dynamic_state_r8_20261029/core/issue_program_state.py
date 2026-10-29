"""ICPS v1: deterministic issue-conditioned static facts, no execution/oracle.

All source is untrusted data. This module never imports target code or runs tests.
An index is session-bound and fixed at W0. Partial scans remain explicitly partial.
"""
import ast,collections,copy,hashlib,json,math,pathlib,re,time
VERSION='issue_program_state_v1.0'
SKIP={'.git','.hg','.svn','.venv','venv','env','site-packages','node_modules','__pycache__','tests','test','testing','fixtures','verifier','oracle','gold','reference','private','artifacts','logs','checkpoints','build','dist','.tox','.mypy_cache','.pytest_cache','docs','examples','benchmarks'}
STOP=set('a an the and or of in on for to with from is are be by this that it its as at not all any can should must you your we our code python repository issue fix bug task file function method class test tests use using please working work change implement return returns none true false'.split())
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()
def text_sha(x):return hashlib.sha256(x.encode()).hexdigest()
def allowed(path):
    p=pathlib.PurePosixPath(path)
    if not path or p.is_absolute() or '..' in p.parts or '\\' in path or '\x00' in path:return False
    parts=[s.lower() for s in p.parts]
    if any(s in SKIP or s.startswith('.') or any(w in s for w in ['oracle','gold_patch','reference_patch','fail_to_pass','pass_to_pass','injection','mutation']) for s in parts):return False
    return p.suffix=='.py' and not p.name.startswith('test_') and not p.name.endswith('_test.py')
def words(x):
    x=re.sub(r'([a-z])([A-Z])',r'\1 \2',x)
    return [w.lower() for w in re.findall('[A-Za-z][A-Za-z0-9]*',x) if len(w)>1 and len(w)<40 and w.lower() not in STOP and not re.fullmatch('[a-fA-F0-9]{8,}',w)]
def brief(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
        return ('async ' if isinstance(node,ast.AsyncFunctionDef) else '')+'def '+node.name+'('+ast.unparse(node.args)+')'+(' -> '+ast.unparse(node.returns) if node.returns else '')+':'
    if isinstance(node,ast.ClassDef):return 'class '+node.name+'('+', '.join(ast.unparse(b) for b in node.bases)+'):'
    return '<module:parse_unavailable>'
def module_imports(tree):
    return sorted(ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)))
def own_nodes(node):
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and child is not node:continue
        yield from own_nodes(child)
def features(node,imports):
    ns=list(own_nodes(node));calls=sorted(ast.unparse(n.func) for n in ns if isinstance(n,ast.Call))
    args=sorted(set(a.arg for n in ns if isinstance(n,ast.arguments) for a in [*n.posonlyargs,*n.args,*n.kwonlyargs,*([n.vararg] if n.vararg else []),*([n.kwarg] if n.kwarg else [])]))
    bound=set(args)
    for n in ns:
        if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store):bound.add(n.id)
        if isinstance(n,(ast.Import,ast.ImportFrom)):bound.update(a.asname or a.name.split('.')[0] for a in n.names)
    return dict(signature=brief(node),returns=sorted(ast.dump(n.value,include_attributes=False) if n.value else 'None' for n in ns if isinstance(n,ast.Return)),calls=calls,
        imports=imports,literals_conditions=sorted(ast.dump(n,include_attributes=False) for n in ns if isinstance(n,(ast.Constant,ast.Compare,ast.BoolOp)) or isinstance(n,ast.IfExp)),bound=sorted(bound))
def parse_file(path,source):
    if not allowed(path):raise ValueError('forbidden source path')
    try:tree=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError):
        e=dict(file=path,qualified='<parse_unavailable>',kind='lexical_fallback',source=source[:1600],signature='<parse_unavailable>',source_hash=text_sha(source),features=None,syntax='parse_unavailable',start_line=1,end_line=min(16,len(source.splitlines())),insert_line=None)
        e['entity_id']=digest([path,e['qualified'],e['kind']])[:12];return [e]
    found=[];imports=module_imports(tree);source_lines=source.splitlines(keepends=True)
    def segment(node):
        # ast.get_source_segment splits the entire file for EVERY entity.
        # Cache lines once, retaining the exact UTF-8 offset semantics.
        a=node.lineno-1;b=node.end_lineno-1
        if a==b:return source_lines[a].encode()[node.col_offset:node.end_col_offset].decode()
        return source_lines[a].encode()[node.col_offset:].decode()+''.join(source_lines[a+1:b])+source_lines[b].encode()[:node.end_col_offset].decode()
    class Visitor(ast.NodeVisitor):
        def __init__(self):self.scope=[]
        def item(self,node):
            qualified='.'.join(self.scope+[node.name]);body_source=segment(node)
            e=dict(file=path,qualified=qualified,kind='class' if isinstance(node,ast.ClassDef) else 'function',source=body_source,signature=brief(node),features=features(node,imports),source_hash=text_sha(body_source),syntax='valid',start_line=node.lineno,end_line=node.end_lineno)
            first=node.body[0] if node.body else None;line=min([first.lineno]+[d.lineno for d in getattr(first,'decorator_list',[])]) if first else None
            e.update(insert_line=line if line and line>node.lineno else None,insert_indent=first.col_offset if first else None)
            e['entity_id']=digest([path,qualified,e['kind']])[:12];found.append(e);self.scope.append(node.name);self.generic_visit(node);self.scope.pop()
        visit_FunctionDef=item;visit_AsyncFunctionDef=item;visit_ClassDef=item
    Visitor().visit(tree)
    # Repeated definitions of the same qualified symbol are not safely attributable.
    counts=collections.Counter(e['entity_id'] for e in found)
    for e in found:e['ambiguous']=counts[e['entity_id']]>1
    return found

def build_initial_index(snapshot,issue,*,task_uid,session_id):
    started=time.monotonic();files=snapshot['files'];entities=[]
    for path in sorted(files):
        if not allowed(path):raise ValueError('source allowlist violated')
        entities.extend(parse_file(path,files[path]))
        if len(entities)>30000:raise ValueError('entity budget')
    if not snapshot.get('stable'):raise ValueError('unstable pre-action workspace read')
    initial_digest=digest({p:text_sha(t) for p,t in sorted(files.items())});identity=digest([task_uid,session_id,initial_digest,text_sha(issue),VERSION])
    n=len(entities);docs=[];df=collections.Counter()
    for e in entities:
        terms=collections.Counter(words(e['file']+' '+e['qualified']+' '+e['signature']+' '+e['source'][:8192]));docs.append(terms);df.update(terms.keys())
    query=collections.Counter(words(issue));average=sum(sum(t.values()) for t in docs)/max(1,n)
    explicit=set(re.findall(r'`([A-Za-z_][\w.]*)`',issue))|set(re.findall(r'\b(?:function|method|class)\s+([A-Za-z_][\w.]*)',issue))
    mentioned_paths=set(re.findall(r'[A-Za-z_0-9./-]+\.py',issue))
    ranked=[]
    for e,t in zip(entities,docs):
        if e.get('ambiguous'):continue
        path_match=any(e['file']==p or e['file'].endswith('/'+p) for p in mentioned_paths if allowed(p))
        symbol_match=e['qualified'] in explicit or e['qualified'].split('.')[-1] in explicit
        score=0.0
        for term in query:
            tf=t.get(term,0)
            if tf:score+=math.log(1+(n-df[term]+.5)/(df[term]+.5))*tf*2.2/(tf+1.2*(.25+.75*sum(t.values())/max(1,average)))
        tier=2 if path_match else (1 if symbol_match else 0)
        if tier or score>0:
            z=copy.deepcopy(e);z.update(selection='explicit_path' if path_match else ('explicit_symbol' if symbol_match else 'issue_lexical'),retrieval_score=score,tier=tier);ranked.append(z)
    ranked.sort(key=lambda e:(-e['tier'],-e['retrieval_score'],digest([e['file'],e['qualified']])))
    selected=ranked[:3];byid={e['entity_id']:e for e in entities if not e.get('ambiguous')}
    global_defs=collections.defaultdict(list)
    for e in byid.values():
        if e['kind']=='function' and '.' not in e['qualified']:global_defs[(e['file'],e['qualified'])].append(e)
    edges=[]
    for e in byid.values():
        f=e.get('features')
        if not f:continue
        for name in f['calls']:
            targets=global_defs.get((e['file'],name),[])
            if re.fullmatch(r'[A-Za-z_]\w*',name) and name not in f['bound'] and len(targets)==1:
                edges.append(dict(caller=e['entity_id'],callee=targets[0]['entity_id'],kind='static_same_module_name_reference; runtime dispatch unproven'))
    chosen={e['entity_id'] for e in selected};related=[e for e in edges if e['caller'] in chosen or e['callee'] in chosen]
    neighbor_ids=sorted({e[k] for e in related for k in ['caller','callee']}-chosen)[:6]
    index=dict(version=VERSION,task_uid=task_uid,session_id=session_id,issue_digest=text_sha(issue),initial_workspace_digest=initial_digest,identity=identity,scope='bounded allowlisted Python source only, not full filesystem',source_limited=snapshot.get('limited',False),focus=selected,neighbors=[copy.deepcopy(byid[x]) for x in neighbor_ids],relations=[e for e in related if e['caller'] in chosen|set(neighbor_ids) and e['callee'] in chosen|set(neighbor_ids)],candidate_status='matched' if selected else 'no_candidate',ranking_candidates=len(ranked),ranked_omitted=max(0,len(ranked)-3),indexed_entities=n,source_files=len(files),source_bytes=sum(len(t.encode()) for t in files.values()),parse_unavailable_files=len({e['file'] for e in entities if e['syntax']!='valid'}),index_wall_seconds=time.monotonic()-started)
    index['initial_state']=extract_current_impact(index,snapshot,task_uid=task_uid,session_id=session_id,call_index=0)
    return index

def extract_current_impact(index,snapshot,*,task_uid,session_id,call_index):
    start=time.monotonic()
    if (index['task_uid'],index['session_id'])!=(task_uid,session_id):raise ValueError('wrong task/session cache')
    if call_index<0:raise ValueError('negative generation call')
    files=snapshot['files'];focused=[];neighbors=[];parsed={}
    for old,dest in [(e,focused) for e in index['focus']]+[(e,neighbors) for e in index['neighbors']]:
        path=old['file'];item=dict(entity_id=old['entity_id'],file=path,qualified=old['qualified'],status='unavailable',syntax='unknown',signature_changed=None,return_expr_changed=None,call_names_changed=None,import_edges_changed=None,literal_or_condition_changed=None,current_excerpt=None)
        if not snapshot.get('stable'):item['reason']='unstable_read'
        elif path not in files:
            item.update(status='unavailable' if snapshot.get('limited') else 'deleted',reason='file_missing_from_bounded_capture' if snapshot.get('limited') else 'file_absent')
        else:
            if path not in parsed:parsed[path]=parse_file(path,files[path])
            entities=parsed[path]
            if any(e['syntax']!='valid' for e in entities):item.update(status='parse_error',syntax='parse_unavailable',current_excerpt=files[path][:1600])
            else:
                matches=[e for e in entities if e['entity_id']==old['entity_id'] and not e.get('ambiguous')]
                if len(matches)!=1:item.update(status='moved_unresolved',syntax='valid',reason='qualified_entity_missing_or_ambiguous; no line-number fallback')
                else:
                    now=matches[0];item.update(status='unchanged' if now['source_hash']==old['source_hash'] else 'modified',syntax='valid',current_excerpt=now['source'][:1600],current_source_hash=now['source_hash'])
                    if old.get('features'):
                        for field,name in [('signature_changed','signature'),('return_expr_changed','returns'),('call_names_changed','calls'),('import_edges_changed','imports'),('literal_or_condition_changed','literals_conditions')]:item[field]=now['features'][name]!=old['features'][name]
        dest.append(item)
    relevant=sorted({x['file'] for x in focused+neighbors if x['status']!='unchanged' or x['import_edges_changed'] is True})
    facts=[{k:v for k,v in x.items() if k not in {'file','qualified','current_excerpt','reason'}} for x in focused+neighbors]
    return dict(task_uid=task_uid,session_id=session_id,index_identity=index['identity'],call_index=call_index,pre_action=True,focus=focused,neighbors=neighbors,relevant_files_changed=relevant,changed_neighbor_entities=sum(e['status']=='modified' or e['import_edges_changed'] is True for e in neighbors),state_hash=digest([index['identity'],facts]),source_scope_limited=snapshot.get('limited',False),capture_stable=snapshot.get('stable',False),update_wall_seconds=time.monotonic()-start)

def serialize_icps(index,state,tokenizer,*,initial,remaining=4096):
    if (state['task_uid'],state['session_id'],state['index_identity'])!=(index['task_uid'],index['session_id'],index['identity']) or not state['pre_action']:raise ValueError('PI identity/timing')
    cap=min(256 if initial else 128,remaining)
    if not index['focus']:
        body=dict(source='buggy_workspace',candidate_status='no_candidate',truncated=False)
    elif initial:
        body=dict(source='buggy_workspace',index_limited=index['source_limited'],candidates=[dict(id=e['entity_id'],focus=e['file']+'::'+e['qualified'],selection=e['selection'],signature=e['signature'],excerpt='\n'.join(e['source'].splitlines()[:8])[:500]) for e in index['focus']],neighbors=[dict(id=e['entity_id'],symbol=e['qualified'],kind='static_same_module_reference') for e in index['neighbors'][:2]],state='unchanged',truncated=False)
    else:
        body=dict(source='current_pre_action',states=[dict(id=e['entity_id'],status=e['status'],syntax=e['syntax'],changed=[k.replace('_changed','') for k in ['signature_changed','return_expr_changed','call_names_changed','import_edges_changed','literal_or_condition_changed'] if e[k] is True],unknown=e['status'] not in {'unchanged','modified'},excerpt=e['current_excerpt'][:400] if e['current_excerpt'] and e['status']=='modified' else '') for e in state['focus']],related_changed=state['changed_neighbor_entities'],truncated=False)
    def encode(b):
        t='[ICPS v1]\n'+json.dumps(b,ensure_ascii=True,separators=(',',':'))+'\n[/ICPS]';return t,tokenizer.encode(t,add_special_tokens=False)
    text,ids=encode(body);raw=len(ids)
    if len(ids)>cap and initial and body.get('candidates'):
        # Keep source for the top candidate before spending tokens on metadata
        # for lower candidates. All omissions are explicit; no token slicing.
        body['truncated']=True;body.pop('neighbors',None)
        original_candidates=body['candidates'];body['candidates']=original_candidates[:1]
        body['omitted_candidate_ids']=[e['id'] for e in original_candidates[1:]]
        entity=index['focus'][0];lines=entity['source'].splitlines()
        selected=[(0,lines[0])] if lines else []
        for n,line in enumerate(lines[1:],1):
            if re.match(r'\s*(return\b|if\b|raise\b|while\b|for\b)',line):selected.append((n,line));break
        if len(selected)<2 and len(lines)>1:selected.append((1,lines[1]))
        body['candidates'][0]['excerpt_lines']=[dict(relative_line=n+1,text=line[:180]) for n,line in selected]
        body['candidates'][0].pop('excerpt',None);text,ids=encode(body)
    if len(ids)>cap and initial and body.get('candidates'):
        body['candidates'][0].pop('signature',None);text,ids=encode(body)
    if len(ids)>cap and not initial:
        body['truncated']=True
        unchanged=[e for e in body.get('states',[]) if e['status']=='unchanged' and not e['changed']]
        if unchanged:body['unchanged_ids']=[e['id'] for e in unchanged]
        body['states']=[e for e in body.get('states',[]) if e not in unchanged]
        text,ids=encode(body)
    if len(ids)>cap:
        body['truncated']=True
        for e in body.get('candidates',[])+body.get('states',[]):e.pop('excerpt',None);e.pop('excerpt_lines',None)
        text,ids=encode(body)
    if len(ids)>cap and initial:
        body.pop('neighbors',None)
        for e in body.get('candidates',[]):e.pop('signature',None)
        text,ids=encode(body)
    if len(ids)>cap:
        body=dict(omitted=True,truncated=True,states=[dict(id=e['entity_id'],status='unchanged' if initial else next(x['status'] for x in state['focus'] if x['entity_id']==e['entity_id'])) for e in index['focus']])
        text,ids=encode(body)
    if len(ids)>cap:
        # No tokenizer slicing, no Actor truncation. Failure is explicit metadata.
        return dict(pi_text='',pi_ids=[],pi_raw_tokens=raw,pi_truncated=True,omitted=True,omission_reason='minimal_atomic_status_cannot_fit',token_cap=cap)
    return dict(pi_text=text,pi_ids=ids,pi_raw_tokens=raw,pi_truncated=body.get('truncated',False),omitted=body.get('omitted',False),token_cap=cap)
