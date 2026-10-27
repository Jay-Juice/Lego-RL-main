"""Full-data identity/cache inventory and namespace; no GPU/model/Gold access."""
import hashlib,ipaddress,json,os,pathlib,re,shutil,socket,subprocess,time,tomllib
import pandas as pd
B=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main');OLD=B/'experiments/pi_repair_state_v2_20261015';F=pathlib.Path(__file__).resolve().parents[1]
EXP='sao-qwen35-9b-b64-icps-v11-192-full97-r2-20261024'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*a):return subprocess.check_output(a,text=True,timeout=120)
def save(p,x):
    with p.open('x') as h:json.dump(x,h,indent=2,allow_nan=False)
def resources():
    pids=run('nvidia-smi','--query-compute-apps=pid','--format=csv,noheader').strip();assert not pids,'GPU occupied: do not stop others'
    mem=[int(x) for x in run('nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits').splitlines()];assert len(mem)==8 and max(mem)<1000
    for n in ['raylet','gcs_server']:assert subprocess.run(['pgrep','-x',n],stdout=subprocess.DEVNULL).returncode!=0
    for port in [6399,8299,8265]:
        with socket.socket() as s:s.bind(('0.0.0.0',port))
    ids=run('docker','network','ls','-q').split();pool=ipaddress.ip_network('172.16.160.0/20')
    for n in json.loads(run('docker','network','inspect',*ids)) if ids else []:
        for c in n.get('IPAM',{}).get('Config') or []:
            if c.get('Subnet'):
                net=ipaddress.ip_network(c['Subnet']);assert net.version!=4 or not net.overlaps(pool),'new subnet overlaps existing; never prune'
    return dict(free_bytes=shutil.disk_usage(F).free,inodes_free=os.statvfs(F).f_favail,GPUs_free=8,Ray_absent=True,subnet=str(pool),ports_checked=[6399,8299,8265])
def main():
    os.umask(0o077);res=resources()
    prior=OLD/'ops/icps_v11_window_20261023'
    assert json.loads((prior/'CURRENT_RUNTIME.json').read_text())['status']=='ONLINE_CANARY_PASSED' if (prior/'CURRENT_RUNTIME.json').exists() else json.loads((OLD/'logs/icps_v11_window_20261023/ONLINE_SUMMARY_r3.json').read_text())['status']=='ONLINE_CANARY_PASSED'
    assert sha(F/'src/window_serializer.py')==sha(prior/'src_r3/window_serializer.py')
    protected={}
    receipt=json.loads((F/'runtime/SOURCE_DIFF_RECEIPT.json').read_text())
    for z in receipt.values():
        assert sha(OLD/z['relative'])==z['original_SHA'];protected[z['relative']]=z['original_SHA']
        assert sha(F/'runtime'/z['file'])==z['candidate_SHA']
    dataset=B/'data/swesmith_python_full_v7_verdict_v6_20260930.parquet';df=pd.read_parquet(dataset)
    assert len(df)==6248 and {'prompt','reward_model','extra_info'}<=set(df.columns)
    images={}
    for line in run('docker','image','ls','--no-trunc','--digests','--format','{{json .}}').splitlines():
        r=json.loads(line);images[r['Repository']+':'+r['Tag']]=r['ID']
        if r.get('Digest') not in (None,'<none>'):images[r['Repository']+'@'+r['Digest']]=r['ID']
    pins={};task_rows=[];missing=[];compose=[];contexts=0
    for i,row in enumerate(df.extra_info):
        task=pathlib.Path(row['harbor_task_path']);task=task if task.is_absolute() else B/task;task=task.resolve()
        assert task.is_dir() and (task/'instruction.md').is_file()
        env=task/'environment';dockerfile=env/'Dockerfile';assert dockerfile.is_file() and not dockerfile.is_symlink()
        config=tomllib.loads((task/'task.toml').read_text())
        if (env/'docker-compose.yaml').exists():compose.append(str(task))
        native_name=(config.get('task') or {}).get('name',task.name)
        tag=re.sub('[^a-z0-9._-]','-',('hb__'+native_name).lower())+':latest'
        entry=dict(Dockerfile_SHA=sha(dockerfile),tag=tag,task_config_SHA=sha(task/'task.toml'),instruction_SHA=sha(task/'instruction.md'))
        if tag in images:entry.update(mode='cached_prepared',image_id=images[tag])
        else:
            parents=[]
            for line in dockerfile.read_text().splitlines():
                if re.match('(?i)^FROM\\s+',line.strip()):
                    parts=line.split();name=parts[1] if not parts[1].startswith('--') else parts[2]
                    key=name if ':' in name.split('/')[-1] or '@' in name else name+':latest'
                    if key not in images:raise ValueError('missing local prepared and FROM base: '+task.name+'; no pull allowed')
                    parents.append(dict(tag=key,image_id=images[key]))
            assert parents,'unresolved local Dockerfile FROM'
            size=sum(f.stat().st_size for f in env.rglob('*') if f.is_file() and not f.is_symlink());contexts+=size
            entry.update(mode='native_local_build',image_id=None,local_build_parents=parents,context_bytes=size);missing.append(task.name)
        pins[str(env.resolve())]=entry
        task_rows.append(dict(row=i,instance_id=row['instance_id'],task=str(task),config_SHA=entry['task_config_SHA'],instruction_SHA=entry['instruction_SHA'],Dockerfile_SHA=entry['Dockerfile_SHA']))
    assert len(pins)==6248 and len({r['instance_id'] for r in task_rows})==6248 and not compose,'duplicate task or unsupported compose'
    required=200*1024**3+189686470567+50*1024**3+contexts*2
    assert res['free_bytes']>=required,f'insufficient safe training+one save+evaluation/cache reserve: {res["free_bytes"]} < {required}'
    save(F/'preflight/FULL6248_PREPARED_IMAGES.json',pins)
    save(F/'preflight/FULL6248_DATA_IDENTITY.json',dict(dataset=str(dataset),SHA=sha(dataset),rows=6248,columns=list(df.columns),tasks=task_rows,
        cached_prepared=len(pins)-len(missing),native_local_build=len(missing),no_pull=True,build_context_bytes=contexts))
    attempt='full_'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_'+str(os.getpid())
    run_dir=F/'runs'/attempt;run_dir.mkdir(parents=True,exist_ok=False)
    checkpoint=F/'checkpoints/sao-qwen35-9b-swesmith'/EXP
    assert not checkpoint.exists(),'new experiment checkpoint namespace already exists'
    save(F/'preflight/NAMESPACE.json',dict(experiment=EXP,attempt=attempt,run=str(run_dir),checkpoint=str(checkpoint),source_root=str(F),repository_runtime=str(OLD)))
    save(F/'preflight/RESOURCE_AND_SOURCE.json',dict(resources=res,minimum_before_start_bytes=required,expected_checkpoint_bytes=189686470567,
        post_checkpoint_free_reserve_GiB=200,cache_eval_contingency_GiB=50,protected_production_SHA=protected,
        method_SHA=sha(F/'src/window_serializer.py'),core_SHA=sha(F/'core/issue_program_state.py'),prepared_manifest_SHA=sha(F/'preflight/FULL6248_PREPARED_IMAGES.json'),
        dataset_SHA=sha(dataset),config_SHA=sha(F/'ICPS_V11_FULL_LAUNCH_CONFIG.env'),native_entry_SHA=sha(OLD/'scripts/train/train.sh'),
        baseline_phase='steps1-20 actor14336 critic20480; steps21-97 actor16384 critic45056; native actual critic infer32768 unchanged, actor/ref14336 unchanged',
        all_source_SHA={str(p.relative_to(F)):sha(p) for d in ['runtime','src','core','tests'] for p in (F/d).rglob('*.py')}))
    print(json.dumps(dict(passed=True,rows=6248,cached=len(pins)-len(missing),native_local_build=len(missing),free_GiB=res['free_bytes']/1024**3,required_GiB=required/1024**3,run=str(run_dir))))
if __name__=='__main__':main()
