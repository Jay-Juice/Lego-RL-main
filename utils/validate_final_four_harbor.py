"""Exercise real Harbor positives and environment/tamper negative controls."""
import asyncio
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial

ROOT=Path('/media/ubuntu/D1/zsj/Lego-RL-main')


async def main():
    out=ROOT/'logs/swesmith_final_four_harbor_v5_20260930';out.mkdir(exist_ok=False)
    summary=json.loads((ROOT/'logs/swesmith_final_four_v5_20260930/summary.json').read_text())
    assert summary['passed']==4
    cases=[]
    for row in summary['results']:
        cases += [(row,'bug',0),(row,'oracle',1)]
    patsy=next(x for x in summary['results'] if x['instance_id'].startswith('pydata__patsy.'))
    pyquery=next(x for x in summary['results'] if x['instance_id'].startswith('gawel__pyquery.'))
    cases += [(patsy,'missing_numpy',None),(pyquery,'invalid_pytest_option',None),(pyquery,'test_tamper',None)]
    results=[]
    for row,mode,expected in cases:
        name=hashlib.sha256(row['instance_id'].encode()).hexdigest()[:8]+'-'+mode
        task=out/'tasks'/name;shutil.copytree(Path(row['task']),task)
        image='lego-final-four-harbor-v5:'+name
        f=task/'task.toml';f.write_text(re.sub(r'docker_image = "[^"]+"',f'docker_image = "{image}"',f.read_text()))
        f=task/'environment/Dockerfile'
        # Reuse the task image; only the controlled test setup changes.
        dockerfile='FROM '+row['task_image']+'\n'
        if mode in ('oracle','missing_numpy'):
            patch=ROOT/'logs/swesmith_final_four_v5_20260930'/row['instance_id']/'oracle.patch'
            shutil.copy2(patch,task/'environment/oracle.patch')
            dockerfile+='COPY oracle.patch /oracle.patch\nRUN git apply /oracle.patch && rm /oracle.patch\n'
        if mode=='missing_numpy':
            dockerfile+='RUN mv /opt/miniconda3/envs/testbed/lib/python3.10/site-packages/numpy /opt/numpy-withheld-for-negative-control\n'
        if mode=='invalid_pytest_option':
            dockerfile+='ENV PYTEST_ADDOPTS="--lego-deliberately-invalid-option"\n'
        if mode=='test_tamper':
            dockerfile+='RUN /opt/miniconda3/envs/testbed/bin/python -c "from pathlib import Path; p=Path(\'/testbed/pyquery/pyquery.py\'); s=p.read_text(); assert \'>>>\' in s; p.write_text(s.replace(\'>>>\',\'###\',1))"\n'
        f.write_text(dockerfile)
        assert subprocess.run(['docker','image','inspect',image],capture_output=True).returncode!=0
        with (out/(name+'-build.log')).open('w') as log:
            subprocess.run(['docker','build','--network','none','--pull=false','-t',image,str(task/'environment')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        config=TrialConfig.model_validate({'task':{'path':str(task)},'trial_name':name,'trials_dir':str(out/'trials'),
          'agent':{'name':'nop'},'environment':{'type':'docker','force_build':False,'delete':False},'predict_patch':{'enabled':False}})
        trial=await Trial.create(config); result=await trial.run()
        reward=result.verifier_result.rewards.get('reward') if result.verifier_result else None
        record={'instance_id':row['instance_id'],'mode':mode,'reward':reward,'expected':expected,'exception':result.exception_info.exception_type if result.exception_info else None}
        results.append(record);(out/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(record),flush=True)
        assert reward==expected,record
    (out/'PASS.json').write_text(json.dumps(results,indent=2))


if __name__=='__main__':asyncio.run(main())
