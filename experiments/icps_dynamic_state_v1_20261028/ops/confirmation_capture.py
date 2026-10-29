"""Read-only W0 capture from existing pinned prepared images; no task runs."""
import concurrent.futures
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import time
import uuid

B=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
N=B/'experiments/icps_dynamic_state_v1_20261028'
F=B/'experiments/icps_v11_full97_sao_20261024_r2'
V=N/'.private_confirmation_r4'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,allow_nan=False)

def one(row,pins):
    started=time.monotonic();task=pathlib.Path(row['task']);uid=row['uid']
    result=dict(uid=uid,status='UNSTARTED')
    try:
        assert shutil.disk_usage(N).free>=200*1024**3,'disk gate'
        for rel,key in [('instruction.md','instruction_SHA'),('task.toml','config_SHA'),('environment/Dockerfile','Dockerfile_SHA')]:
            assert sha(task/rel)==row[key],('task identity',rel)
        pin=pins[str((task/'environment').resolve())]
        if pin['mode']!='cached_prepared':
            result['status']='PINNED_PREPARED_UNAVAILABLE_NO_BUILD';return result
        inspect=subprocess.run(['docker','image','inspect',pin['tag']],capture_output=True,text=True,timeout=15)
        if inspect.returncode:
            result['status']='PINNED_IMAGE_MISSING_NO_PULL';return result
        image=json.loads(inspect.stdout)[0]
        assert image['Id']==pin['image_id'] and image['Config']['WorkingDir']=='/testbed','prepared image identity'
        first=(task/'environment/Dockerfile').read_text().splitlines()[0].split()
        assert len(first)==2 and first[0]=='FROM','unexpected prepared Dockerfile'
        base=json.loads(subprocess.check_output(['docker','image','inspect',first[1]],text=True,timeout=15))[0]
        layers=base['RootFS']['Layers'];actual=image['RootFS']['Layers']
        assert layers and len(actual)>len(layers) and actual[:len(layers)]==layers,'base layer identity'
        reader=(N/'core/workspace_read.py').read_text()
        marker="if __name__=='__main__':print(json.dumps(collect()))"
        assert marker in reader
        code=reader.replace(marker,'')+'''
import subprocess
s=collect('/testbed')
p=subprocess.run(['git','-c','safe.directory=/testbed','-C','/testbed','rev-parse','HEAD'],capture_output=True,text=True,timeout=10)
print(json.dumps(dict(snapshot=s,head=p.stdout.strip() if p.returncode==0 else None)))
'''
        owner=uuid.uuid4().hex;name='dynamic-confirm-'+owner[:16]
        cmd=['docker','run','--rm','--pull=never','--log-driver','none','--name',name,
             '--label','dynamic.confirm.owner='+owner,'--network','none','--read-only','--user','65534:65534',
             '--cpus','1','--memory','2g','--memory-swap','2g','--pids-limit','128','--cap-drop','ALL',
             '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777',
             '--entrypoint','/opt/miniconda3/envs/testbed/bin/python',image['Id'],'-B','-c',code]
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:out,err=proc.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            inspect=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=10)
            if inspect.returncode==0:
                owned=json.loads(inspect.stdout)[0]
                assert owned['Config']['Labels'].get('dynamic.confirm.owner')==owner
                subprocess.run(['docker','kill',owned['Id']],capture_output=True,check=True,timeout=10)
            proc.communicate(timeout=15)
            raise TimeoutError('own_readonly_capture_timeout90s')
        assert proc.returncode==0,('capture exit',proc.returncode,err[-300:])
        assert len(out.encode())<24*1024**2
        captured=json.loads(out);assert captured['snapshot']['stable'],'unstable W0'
        captured.update(uid=uid,issue=(task/'instruction.md').read_text(),issue_SHA=row['instruction_SHA'],
            image=dict(image_id=image['Id'],tag=pin['tag'],Dockerfile_SHA=row['Dockerfile_SHA'],declared_base=first[1],base_layer_prefix_verified=True))
        p=V/'captures'/f'{uid}.json.gz'
        with gzip.open(p,'xt',encoding='utf-8') as f:json.dump(captured,f)
        result.update(status='COMPLETE',capture_SHA=sha(p),limited=captured['snapshot'].get('limited'),source_bytes=captured['snapshot']['read_bytes'])
    except Exception as exc:
        result.update(status='CAPTURE_ERROR',error_type=type(exc).__name__,error=str(exc)[:500])
    finally:result['wall_seconds']=time.monotonic()-started
    return result

def main():
    os.umask(0o077);started=time.monotonic()
    m=read(V/'MANIFEST.json');public=read(N/'reports/CONFIRMATION_EXPOSURE_FREEZE_R4.json')
    assert sha(V/'MANIFEST.json')==public['manifest_SHA']
    frozen=read(N/'CANDIDATE_FREEZE_R4.json')
    assert sha(N/'CANDIDATE_FREEZE_R4.json')==m['candidate_freeze_SHA']
    for p,h in frozen['source_SHA'].items():assert sha(N/p)==h
    pins_path=F/'preflight/FULL6248_PREPARED_IMAGES.json';pins=read(pins_path)
    (V/'captures').mkdir(exist_ok=False)
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,row,pins):row['uid'] for row in m['rows']}
        for future in concurrent.futures.as_completed(futures):
            result=future.result();results.append(result)
            print(json.dumps(dict(done=len(results),total=len(futures),status=result['status'])),flush=True)
    assert len(results)==len(m['rows']) and len({r['uid'] for r in results})==len(results)
    save(V/'CAPTURE_RECEIPT.json',dict(rows=results,manifest_SHA=sha(V/'MANIFEST.json'),prepared_pins_SHA=sha(pins_path),wall_seconds=time.monotonic()-started,script_SHA=sha(pathlib.Path(__file__))))
    counts={s:sum(r['status']==s for r in results) for s in sorted({r['status'] for r in results})}
    save(N/'reports/CONFIRMATION_CAPTURE_R4.json',dict(counts=counts,total=len(results),receipt_SHA=sha(V/'CAPTURE_RECEIPT.json'),wall_seconds=time.monotonic()-started,GPU_jobs=0,verifier_runs=0,Actor_rollouts=0,no_replacement_samples=True))
    print(json.dumps(counts),flush=True)
if __name__=='__main__':main()
