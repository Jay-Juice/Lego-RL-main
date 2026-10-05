"""Real Harbor checks on repaired mixed-source tasks, no LLM or training."""
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
    out=ROOT/'logs/swesmith_embedded_harbor_v4_20260930';out.mkdir(exist_ok=False)
    iid='pydata__patsy.a5d16484.combine_file__4zw01ak1'
    template=ROOT/'data/swesmith_patsy_reportguard_v4_20260930'/iid
    patch=ROOT/'logs/swesmith_patsy_reportguard_v4_20260930'/iid/'oracle.patch'
    results={}
    for name,expected in [('bug',0),('oracle',1),('test_tampering',None)]:
        task=out/'tasks'/name;shutil.copytree(template,task)
        image='lego-embedded-v4-check:'+hashlib.sha256(str(task).encode()).hexdigest()[:12]
        f=task/'task.toml';f.write_text(re.sub(r'docker_image = "[^"]+"',f'docker_image = "{image}"',f.read_text()))
        f=task/'environment/Dockerfile'
        if name=='oracle':
            shutil.copy2(patch,task/'environment/oracle.patch')
            f.write_text(f.read_text()+'\nCOPY oracle.patch /oracle.patch\nRUN git apply /oracle.patch && rm /oracle.patch\n')
        if name=='test_tampering':
            p=task/'environment/embedded_source/patsy/categorical.py'
            s=p.read_text();s=s.replace('def test_CategoricalSniffer():','def test_CategoricalSniffer():\n    return\n')
            assert s!=p.read_text();p.write_text(s)
        assert subprocess.run(['docker','image','inspect',image],capture_output=True).returncode!=0
        with (out/(name+'-image-build.log')).open('w') as log:
            subprocess.run(['docker','build','--network','none','--pull=false','-t',image,str(task/'environment')],stdout=log,stderr=subprocess.STDOUT,check=True)
        config=TrialConfig.model_validate({'task':{'path':str(task)},'trial_name':name,'trials_dir':str(out/'trials'),
            'agent':{'name':'nop'},'environment':{'type':'docker','force_build':False,'delete':False},'predict_patch':{'enabled':False}})
        trial=await Trial.create(config);result=await trial.run()
        reward=result.verifier_result.rewards.get('reward') if result.verifier_result else None
        results[name]={'reward':reward,'expected':expected,'exception':result.exception_info.exception_type if result.exception_info else None}
        (out/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results[name]),flush=True)
        assert reward==expected,(name,reward,expected)
    (out/'PASS.json').write_text(json.dumps(results,indent=2))


if __name__=='__main__':asyncio.run(main())
