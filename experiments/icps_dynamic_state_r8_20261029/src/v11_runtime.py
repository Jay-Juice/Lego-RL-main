"""Host-only pre-generation provider. All raw snapshots are ephemeral CPU data."""
import base64,copy,json,os,pathlib,shlex,time
from window_serializer import WindowSession,digest
from issue_program_state import build_initial_index
def pin_prepared_image(environment):
    """Full6248 local prepared identity; missing tags use original local build."""
    import subprocess,hashlib
    manifest=json.loads(pathlib.Path(os.environ['ICPS_V11_CACHED_IMAGES']).read_text())
    directory=str(pathlib.Path(environment.environment_dir).resolve())
    entry=manifest[directory]
    if hashlib.sha256((pathlib.Path(directory)/'Dockerfile').read_bytes()).hexdigest()!=entry['Dockerfile_SHA']:raise ValueError('prepared Dockerfile changed')
    if environment._uses_compose:raise ValueError('unreviewed task compose/build services')
    if entry['mode']=='cached_prepared':
        image=json.loads(subprocess.check_output(['docker','image','inspect',entry['tag']],text=True,timeout=30))[0]
        if image['Id']!=entry['image_id']:raise ValueError('cached prepared image changed')
        environment.task_env_config=environment.task_env_config.model_copy(update={'docker_image':entry['tag']})
        environment._env_vars.prebuilt_image_name=entry['tag']
    else:
        for parent in entry['local_build_parents']:
            image=json.loads(subprocess.check_output(['docker','image','inspect',parent['tag']],text=True,timeout=30))[0]
            if image['Id']!=parent['image_id']:raise ValueError('local build base changed')
        # Native Harbor will build this exact prepared Dockerfile from cached FROM.
        environment.task_env_config=environment.task_env_config.model_copy(update={'docker_image':None})
        environment._env_vars.prebuilt_image_name=None
class Capture:
    def __init__(self,issue,task,session,scanner):
        self.issue=issue;self.task=task;self.session=session;self.scanner=scanner;self.candidates=None;self.seq=0
    async def capture(self):
        start=time.time_ns();s=await self.scanner()
        if not s.get('stable'):raise RuntimeError('unstable ICPS pre-action source; no fallback')
        if self.candidates is None:
            idx=build_initial_index(s,self.issue,task_uid=self.task,session_id=self.session)
            self.candidates=[{k:v for k,v in e.items() if k in {'file','qualified','entity_id','kind','start_line','end_line','syntax','selection','tier','retrieval_score'}} for e in idx['focus']]
        paths={e['file'] for e in self.candidates}
        # No persistent full workspace/index. Only current selected files cross host registry.
        small=dict(files={p:t for p,t in s['files'].items() if p in paths},stable=s['stable'],limited=s.get('limited',False))
        seq=self.seq;self.seq+=1
        return dict(session_id=self.session,state_seq=seq,state_hash=digest([self.session,seq]),
            captured_at_start_ns=start,captured_at_end_ns=time.time_ns(),changed_files=[],parse_failure_count=0,
            v11_context=dict(candidates=self.candidates,issue=self.issue,snapshot=small,task_uid=self.task),pre_action=True)
async def install_provider(environment,registry):
    if os.environ.get('PI_FORMAT')!='icps_window_v11':return False
    path=pathlib.Path(environment.environment_dir).resolve().parent/'instruction.md'
    if not path.is_file() or path.is_symlink() or path.stat().st_size>262144:raise ValueError('instruction identity')
    script=(pathlib.Path(os.environ['ICPS_V11_ORIGINAL_SOURCE'])/'workspace_read.py').read_bytes()
    command='"${HARBOR_VERIFIER_PYTHON:-python3}" -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(script).decode())+'))')
    async def scanner():
        result=await environment.exec(command=command,timeout_sec=45)
        if result.return_code:raise RuntimeError('source reader failed '+(result.stderr or '')[-400:])
        if len(result.stdout.encode())>16*1024**2:raise ValueError('reader output limit')
        return json.loads(result.stdout)
    capture=Capture(path.read_text(),digest(['icps_task',path.parent.name]),environment.session_id,scanner)
    environment._icps_v11_capture=capture;registry.register(environment.session_id,capture.capture);return True
def proxy_fields(snapshot,tokenizer,sess,*,logical_call_id):
    c=snapshot['v11_context'];identity=(c['task_uid'],snapshot['session_id'])
    a=WindowSession(c['candidates'],c['issue'],tokenizer,*identity)
    cache=sess.get('v11_runtime_cache')
    if cache:
        if tuple(cache['identity'])!=identity:raise ValueError('cross-task cache')
        for k in ['previous','remaining','last','retries','exhausted','seen']:setattr(a,k,copy.deepcopy(cache[k]))
    prior=a.previous
    fields=a.capture(c['snapshot'],task_uid=identity[0],session_id=identity[1],logical_call_id=logical_call_id,seq=snapshot['state_seq'])
    sess['v11_runtime_cache']=dict(identity=identity,**{k:copy.deepcopy(getattr(a,k)) for k in ['previous','remaining','last','retries','exhausted','seen']})
    fields.update(changed_files=sorted({w['file'] for w in fields['windows']}) if prior and fields['state_hash']!=prior else [],
        parse_failure_count=sum(w['syntax']!='valid' for w in fields['windows']),
        captured_at_start_ns=snapshot['captured_at_start_ns'],captured_at_end_ns=snapshot['captured_at_end_ns'])
    # Only retained exact windows + hashes, never all source files/Issue/cache in records.
    fields.pop('task_uid',None)
    return fields
def training_batch_done(batch,step):
    from formal_metrics import record_step
    record_step(batch,step)
    records=batch.non_tensor_batch.pop('pi_call_records',None)
    n=sum(len(r or []) for r in records) if records is not None else 0
    del records
    path=os.environ.get('ICPS_V11_RELEASE_AUDIT')
    if path:
        with open(path,'a') as f:f.write(json.dumps(dict(event='training_batch_done',step=step,records_released=n,batch_has_records='pi_call_records' in batch.non_tensor_batch,time_ns=time.time_ns()))+'\n')
