"""R8 formal freshbase full97 entry. Native fit/rollout/reward/update/save unchanged."""
import copy,hashlib,ipaddress,json,os,pathlib,re,sys,time,tempfile,subprocess
from gpu_launch_gate_r6 import B,N,file_sha,canonical_sha,collect_resources,validate_resources,require
from gpu_launch_config_r6 import prepare,differences
from full_private_ray_r8 import PrivateRayLease,private_path,validate_ray_namespace,owned_processes
EXP='sao-qwen35-9b-b64-pi-r8-1024-full97-20261029'
def read(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def config_for(run):
 require(run.parent==N/'runs' and re.fullmatch(r'full-r8-[0-9a-f]{16}',run.name),'formal namespace')
 surrogate=N/'runs'/run.name.replace('full-r8-','gpu-r6-')
 config,parity=prepare(surrogate);original=copy.deepcopy(config)
 config['trainer'].update(experiment_name=EXP,default_local_dir=str(N/'checkpoints'/EXP),episode_log_dir=str(run/'episode_logs'))
 config['actor_rollout_ref']['rollout']['trace']['experiment_name']=EXP
 config['ray_kwargs']['ray_init'].update(namespace=run.name,_temp_dir=str(private_path(run)/'ray'))
 allowed={'trainer.experiment_name','trainer.default_local_dir','trainer.episode_log_dir','actor_rollout_ref.rollout.trace.experiment_name','ray_kwargs.ray_init.namespace','ray_kwargs.ray_init._temp_dir'}
 diff=differences(config,original);require({x['key'] for x in diff}==allowed,'formal namespace-only configuration')
 validate_ray_namespace(config,run)
 return config,dict(inherited_two_phase_parity=parity,formal_namespace_changes=diff,recipe_unchanged=True)
def network_gate():
 pool=ipaddress.ip_network(os.environ['LEGO_EVAL_SUBNET_POOL'])
 ids=subprocess.check_output(['docker','network','ls','-q'],text=True).split()
 for net in json.loads(subprocess.check_output(['docker','network','inspect',*ids],text=True)) if ids else []:
  for row in net.get('IPAM',{}).get('Config') or []:
   if row.get('Subnet'):
    other=ipaddress.ip_network(row['Subnet']);require(other.version!=4 or not pool.overlaps(other),'Harbor subnet overlap')
 return str(pool)
def verify_environment():
 required={'PI_ENABLE':'1','PI_FORMAT':'icps_dynamic_v1','PI_MAX_TOKENS_PER_STATE':'1024','ICPS_EPISODE_PI_BUDGET':'4096','PI_TOTAL_BUDGET_ENABLE':'1','PI_CRITIC_MAX_SEQ_TOKENS':'245760','PI_ACTOR_RESERVED_TOKENS':'73728','PI_CHECKPOINT_STRICT':'1','PI_MIN_CHECKPOINT_FREE_GIB':'200','ICPS_V11_ROOT':str(N),'ICPS_V11_OVERLAY':'1','ICPS_V11_CACHED_IMAGES':str(N/'preflight/FULL6248_PREPARED_IMAGES.json'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
 for k,v in required.items():require(os.environ.get(k)==v,'environment '+k)
 return required
def prepare_evidence(run):
 config,parity=config_for(run);environment=verify_environment()
 from gpu_launch_r6 import sources_snapshot
 sources=sources_snapshot()
 for p in [N/'ops/FULL_R8.env',N/'ops/full_r8.sh']:sources[str(p)]=file_sha(p)
 data=read(N/'reports/FULL_DATA_R8.json');require(data['status']=='PASS_data_identity_and_offline_assets','full data pending')
 require(file_sha(N/'preflight/FULL6248_PREPARED_IMAGES.json')==data['prepared_manifest_SHA'],'prepared manifest drift')
 require(file_sha(N/'preflight/FULL6248_DATA_IDENTITY.json')==data['identity_manifest_SHA'],'data manifest drift')
 from gpu_offline_assets_r6 import collect
 assets,info=collect(config)
 prior=read(B/'experiments/icps_dynamic_state_v1_20261028/logs/gpu_offline_assets_r6_contracts_r2/offline_asset_manifest.json')
 require(assets==prior,'offline model/tokenizer/data changed')
 return config,dict(config_SHA=canonical_sha(config),parity=parity,environment=environment,sources=sources,assets=assets,asset_info=info,data=data)
def main():
 run=pathlib.Path(os.environ['ICPS_FORMAL_RUN_DIR']);config,evidence=prepare_evidence(run)
 if sys.argv[1]=='prepare':
  save(N/'reports/FULL_CONFIG_R8.json',dict(status='PASS_formal_config_and_offline_bindings',config=config,**evidence,training_admitted=False));return
 require(sys.argv[1]=='launch' and run.is_dir(),'formal invocation')
 coverage=read(N/'reports/recheck_r8/AGGREGATE.json');require(coverage['coverage_admission'] is True,'existing cohort recheck failed')
 require(coverage['status']=='EXISTING_CONFIRMATION_RECHECK_PASS','coverage scope mismatch')
 for relative,digest in coverage['source'].items():require(file_sha(N/relative)==digest,'PI changed after frozen recheck')
 ready=read(N/'reports/FULL_CONTROLLER_R8.json');require(ready['passed'] is True and ready['runtime_SHA']==file_sha(N/'runtime/ray_trainer.py'),'formal telemetry acceptance stale')
 gpu=read(N/'reports/GPU_SHORT_R8_REVIEW.json');require(gpu['exit_code']==0 and gpu['rank_before_after_pass'] and gpu['own_Ray_cleanup_pass'],'native eight GPU acceptance')
 checkpoint=pathlib.Path(config['trainer']['default_local_dir']);require(not checkpoint.exists(),'freshbase only; namespace already exists')
 import ray
 from omegaconf import OmegaConf
 import formal_main
 require(not ray.is_initialized(),'existing Ray')
 with PrivateRayLease(run) as lease:
  short=lease.temp/'tmp';short.mkdir(mode=0o700);os.environ['TMPDIR']=str(short);tempfile.tempdir=None
  resources=collect_resources();validate_resources(resources,time.time())
  require(resources['free_bytes']>=evidence['data']['minimum_before_start_bytes'],'full reserve including build contexts')
  network=network_gate()
  save(run/'FULL_LAUNCH_RECEIPT.json',dict(purpose='R8_freshbase_full97',created_at=time.time(),experiment=EXP,resources=resources,subnet=network,evidence=evidence,coverage_SHA=file_sha(N/'reports/recheck_r8/AGGREGATE.json'),controller_SHA=file_sha(N/'reports/FULL_CONTROLLER_R8.json'),native_GPU_review_SHA=file_sha(N/'reports/GPU_SHORT_R8_REVIEW.json'),budget=[1024,128,4096],reuse_old_checkpoint=False))
  os.environ['ICPS_CHECKPOINT_ROOT']=str(checkpoint)
  try:formal_main.main.__wrapped__(OmegaConf.create(config))
  finally:
   ray.shutdown();deadline=time.monotonic()+20
   while time.monotonic()<deadline:
    try:
     if not owned_processes(lease.owner):break
    except PermissionError:pass
    time.sleep(.5)
if __name__=='__main__':main()
