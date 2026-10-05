"""Port the frozen Agent Lightning Furl environment fix, task-local only."""
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import re
import shutil
import audit_swesmith_controls_20260929 as audit
from prepare_swesmith_harbor import RUN_TESTS, TEST_SH

SHA='f14ec821fe7ded126d2202eef195f66bd63f74975c9ae88322d0500f13eba8db'


def main():
    r=audit.ROOT; old=r/'data/swesmith_python_full_v7_verdict_v2_20260928'
    vendor=Path(__file__).parent/'vendor/cpython310/parse.py'; assert audit.sha(vendor)==SHA
    rows=[x for x in json.loads((old/'manifest.json').read_text())['tasks'] if x['instance_id'].startswith('gruns__furl.')]
    audit.DATA=r/'data/swesmith_furl_recovered_20260930';audit.OUT=r/'logs/swesmith_furl_recovered_20260930'
    audit.DATA.mkdir(exist_ok=False);audit.OUT.mkdir(exist_ok=False)
    for row in rows:
        task=audit.DATA/row['instance_id'];shutil.copytree(old/row['instance_id'],task)
        (task/'tests/run_tests.py').write_text(RUN_TESTS);(task/'tests/test.sh').write_text(TEST_SH)
        (task/'environment/compat').mkdir();shutil.copy2(vendor,task/'environment/compat/parse.py')
        f=task/'environment/Dockerfile';f.write_text(f.read_text()+'\nCOPY compat/parse.py /opt/miniconda3/envs/testbed/lib/python3.10/urllib/parse.py\n')
        tag='lego-furl-v4/'+hashlib.sha256(row['instance_id'].encode()).hexdigest()[:20]+':20260930'
        row['task_image']=tag;f=task/'task.toml';f.write_text(re.sub(r'docker_image = "[^"]+"',f'docker_image = "{tag}"',f.read_text()))
    base=audit.docker
    def docker(name,image,script,args=(),mounts=(),timeout=380):
        return base(name,image,'cp /compat-parse.py /opt/miniconda3/envs/testbed/lib/python3.10/urllib/parse.py; '+script,
                    args,[*mounts,(vendor,'/compat-parse.py','ro')],timeout)
    audit.docker=docker;results=[]
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        for f in cf.as_completed([pool.submit(audit.run,(row,'furl-original-cpython310')) for row in rows]):
            x=f.result();results.append(x);print(json.dumps({'iid':x['instance_id'],'ok':x['control_pass'],'bug':x.get('bug',{}).get('reward'),'oracle':x.get('oracle',{}).get('reward')}),flush=True)
    audit.dump(audit.DATA/'manifest.json',{'tasks':rows,'vendor_sha256':SHA,'activated_for_training':False})
    audit.dump(audit.OUT/'summary.json',{'total':len(results),'passed':sum(x['control_pass'] for x in results),'results':results})


if __name__=='__main__':main()
