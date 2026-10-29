"""Read-only full6248 identity and offline image gate. No build/pull/model."""
import hashlib,json,pathlib,re,subprocess,tomllib,os
B=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main');N=pathlib.Path(__file__).resolve().parents[1]
F=B/'experiments/icps_v11_full97_sao_20261024_r2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def main():
 import pandas as pd
 os.umask(0o077);out=N/'preflight';out.mkdir(exist_ok=False)
 old=read(F/'preflight/FULL6248_DATA_IDENTITY.json');oldpins=read(F/'preflight/FULL6248_PREPARED_IMAGES.json')
 dataset=pathlib.Path(old['dataset']);assert sha(dataset)==old['SHA']
 df=pd.read_parquet(dataset,columns=['extra_info']);assert len(df)==6248
 expected={r['instance_id']:r for r in old['tasks']}
 images={}
 for line in subprocess.check_output(['docker','image','ls','--no-trunc','--digests','--format','{{json .}}'],text=True).splitlines():
  r=json.loads(line);images[r['Repository']+':'+r['Tag']]=r['ID']
  if r.get('Digest') not in (None,'<none>'):images[r['Repository']+'@'+r['Digest']]=r['ID']
 pins={};rows=[];contexts=0;cached=0
 for i,row in enumerate(df.extra_info):
  task=pathlib.Path(row['harbor_task_path']);task=(task if task.is_absolute() else B/task).resolve()
  prior=expected[row['instance_id']];assert str(task)==prior['task']
  for name,key in [('instruction.md','instruction_SHA'),('task.toml','config_SHA'),('environment/Dockerfile','Dockerfile_SHA')]:
   p=task/name;assert p.is_file() and not p.is_symlink() and sha(p)==prior[key],(i,name)
  env=task/'environment';assert not (env/'docker-compose.yaml').exists()
  pin=dict(oldpins[str(env)]);tag=pin['tag']
  if tag in images:
   if pin['mode']=='cached_prepared':assert images[tag]==pin['image_id'],('prepared image changed',i)
   pin.update(mode='cached_prepared',image_id=images[tag]);cached+=1
  else:
   parents=[]
   for line in (env/'Dockerfile').read_text().splitlines():
    if re.match(r'(?i)^FROM\s+',line.strip()):
     fields=line.split();name=fields[2] if fields[1].startswith('--') else fields[1]
     key=name if ':' in name.split('/')[-1] or '@' in name else name+':latest'
     assert key in images,('offline base missing',i,key)
     parents.append(dict(tag=key,image_id=images[key]))
   assert parents,('no offline FROM',i)
   size=sum(p.stat().st_size for p in env.rglob('*') if p.is_file() and not p.is_symlink());contexts+=size
   pin.update(mode='native_local_build',image_id=None,local_build_parents=parents,context_bytes=size)
  pins[str(env)]=pin;rows.append(prior)
 assert len(pins)==6248 and len(expected)==6248
 save(out/'FULL6248_PREPARED_IMAGES.json',pins)
 save(out/'FULL6248_DATA_IDENTITY.json',dict(dataset=str(dataset),SHA=sha(dataset),rows=6248,tasks=rows,cached_prepared=cached,native_local_build=6248-cached,no_pull=True,build_context_bytes=contexts))
 minimum=max(458392574347,200*1024**3+189686470567+50*1024**3+contexts*2)
 public=dict(status='PASS_data_identity_and_offline_assets',rows=6248,cached_prepared=cached,native_local_build=6248-cached,minimum_before_start_bytes=minimum,minimum_before_save_bytes=415172253607,dataset_SHA=sha(dataset),prepared_manifest_SHA=sha(out/'FULL6248_PREPARED_IMAGES.json'),identity_manifest_SHA=sha(out/'FULL6248_DATA_IDENTITY.json'),historical_dataset_identity_exact=True,task_metadata_all_exact=True,no_build_or_pull_executed=True,training_admission=False)
 save(N/'reports/FULL_DATA_R8.json',public);print(json.dumps(public),flush=True)
if __name__=='__main__':main()
