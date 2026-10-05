"""Immutable full dataset with the remaining AL environment adapters restored."""
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess as sp
import time
import pandas as pd
import audit_swesmith_controls_20260929 as audit
from swesmith_special_runners import MODIN_ENV

R = audit.ROOT
OLD = R/'data/swesmith_python_full_v7_verdict_v5_candidate_20260930'
NEW = R/'data/swesmith_python_full_v7_verdict_v6_20260930'
OUT = R/'logs/swesmith_training_v6_20260930'
PREFIXES = ('pydicom__pydicom.', 'sunpy__sunpy.', 'modin-project__modin.', 'tornadoweb__tornado.', 'jd__tenacity.')
FIXTURES = {
 'pydicom__pydicom.': ('pydicom-fixtures-v1/MR-SIEMENS-DICOM-WithOverlays.dcm', '094faf56c63bff84c30567e29de0c67d7c5a8ae05cf880ac12175491b6b645d2', '/tmp/lego-smith-home/.pydicom/data/MR-SIEMENS-DICOM-WithOverlays.dcm'),
 'sunpy__sunpy.': ('iers-fixtures-v1/Leap_Second.dat', '6cb6f5d4b819f2e568e25db4b0b26d89dedf031fdffb18bc94d40f4e94e268d7', '/opt/miniconda3/envs/testbed/lib/python3.11/site-packages/astropy_iers_data/data/Leap_Second.dat'),
}


def control(iid):
    task = NEW/iid; log = OUT/iid; log.mkdir()
    config = json.loads((task/'tests/config.json').read_text())
    image = re.search(r'docker_image = "([^"]+)"', (task/'task.toml').read_text()).group(1)
    name = 'sao-v6-' + hashlib.sha256(iid.encode()).hexdigest()[:12]
    result = {'instance_id': iid, 'task': str(task), 'task_image': image, 'control_pass': False}
    try:
        rc, patch = audit.docker(name+'-extract', config['image'],
            'cd /testbed && git -c safe.directory=/testbed checkout --quiet "$1" && git -c safe.directory=/testbed diff --binary HEAD~1 HEAD~2', [iid], timeout=90)
        assert rc == 0 and patch.startswith(b'diff --git '), (rc, patch[-1000:])
        oracle = log/'oracle.patch'; oracle.write_bytes(patch)
        result['oracle_sha256'] = audit.sha(oracle)
        with (log/'build.log').open('w') as f:
            sp.run(['docker','build','--pull=false','--network','none','-t',image,str(task/'environment')],stdout=f,stderr=sp.STDOUT,check=True,timeout=180)
        for mode in ('bug','oracle'):
            folder=log/mode;folder.mkdir()
            script='cd /testbed || exit 90; '
            if mode=='oracle':script+='git apply /oracle.patch || exit 93; '
            script+='/tests/test.sh; rc=$?; chmod -R a+rwX /logs; exit $rc'
            started=time.monotonic()
            rc,output=audit.docker(name+'-'+mode,image,script,mounts=[(task/'tests','/tests','ro'),(folder,'/logs','rw'),(oracle,'/oracle.patch','ro')])
            (folder/'docker.log').write_bytes(output)
            rp=folder/'verifier/reward.txt';st=folder/'verifier/grading_status.json'
            result[mode]={'exit':rc,'reward':float(rp.read_text()) if rp.exists() else None,'seconds':round(time.monotonic()-started,2),'status':json.loads(st.read_text()) if st.exists() else None}
        result['control_pass']=result['bug']['reward']==0 and result['oracle']['reward']==1
    except Exception as e:result['error']=repr(e)
    audit.dump(log/'audit.json',result)
    print(json.dumps(result),flush=True)
    return result


def main():
    NEW.mkdir(exist_ok=False);OUT.mkdir(exist_ok=False)
    manifest=json.loads((OLD/'manifest.json').read_text());assert manifest['last_four_resolved'] and not manifest['pending']
    selected=[];counts={p:0 for p in PREFIXES};changed=[]
    for row in manifest['tasks']:
        iid=row['instance_id'];task=NEW/iid;shutil.copytree(OLD/iid,task)
        prefix=next((p for p in PREFIXES if iid.startswith(p)),None)
        if prefix:
            changed.append(iid);counts[prefix]+=1
            # All smaller repository groups; two representative fixture groups.
            if prefix not in FIXTURES or counts[prefix]<=2:selected.append(iid)
            dockerfile=task/'environment/Dockerfile'
            if prefix in FIXTURES:
                rel,digest,destination=FIXTURES[prefix]
                src=Path('/media/ubuntu/D1/zsj/agent-lightning-runtime/data/swe-smith-training')/rel
                assert audit.sha(src)==digest
                shutil.copy2(src,task/'environment'/src.name)
                dockerfile.write_text(dockerfile.read_text()+f'\nCOPY {src.name} {destination}\nRUN chmod 444 {destination}\n')
            else:
                code=(task/'tests/run_tests.py').read_text();needle='        result = subprocess.run('
                assert code.count(needle)==1
                code=code.replace(needle,'        from swesmith_special_runners import adapt\n        command, env = adapt(config, nodes, command, env, report)\n'+needle)
                (task/'tests/run_tests.py').write_text(code)
                shutil.copy2(Path(__file__).with_name('swesmith_special_runners.py'),task/'tests/swesmith_special_runners.py')
                if prefix=='modin-project__modin.':
                    dockerfile.write_text(dockerfile.read_text()+'\nENV '+' '.join(k+'='+v for k,v in MODIN_ENV.items())+'\n')
            toml=task/'task.toml';tag='lego-swesmith-v6:'+hashlib.sha256(iid.encode()).hexdigest()[:20]
            toml.write_text(re.sub(r'docker_image = "[^"]+"',f'docker_image = "{tag}"',toml.read_text()))
            row.update(status='environment_adapter_restored_pending_controls',asset_source=str(OLD/iid))
        row.update(run_tests_sha256=audit.sha(task/'tests/run_tests.py'),config_sha256=audit.sha(task/'tests/config.json'),dockerfile_sha256=audit.sha(task/'environment/Dockerfile'))
    frame=pd.read_parquet(str(OLD)+'.parquet');rows=[]
    for _,s in frame.iterrows():
        row=s.to_dict();iid=row['extra_info']['instance_id'];row['extra_info']=dict(row['extra_info']);row['extra_info']['harbor_task_path']=str(NEW/iid)
        row['prompt']=[dict(x) for x in row['prompt']];row['prompt'][0]['content']=str(NEW/iid);rows.append(row)
    pd.DataFrame(rows).to_parquet(str(NEW)+'.parquet',index=False)
    manifest.update(training_ready=False,activated_for_training=False,full_dataset_dynamically_certified=False,task_count=len(rows),changed_environment_counts=counts,parquet_sha256=audit.sha(Path(str(NEW)+'.parquet')),predecessor_manifest_sha256=audit.sha(OLD/'manifest.json'))
    audit.dump(NEW/'manifest.json',manifest);audit.dump(OUT/'selection.json',{'ids':selected,'changed':changed,'counts':counts})
    results=[]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        for f in cf.as_completed([pool.submit(control,iid) for iid in selected]):results.append(f.result())
    summary={'total':len(results),'passed':sum(x['control_pass'] for x in results),'results':results}
    audit.dump(OUT/'summary.json',summary);print('CONTROLS',summary['passed'],summary['total'],flush=True)
    assert summary['passed']==summary['total']


if __name__=='__main__':main()
