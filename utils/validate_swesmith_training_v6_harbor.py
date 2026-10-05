"""Real Harbor acceptance for the added native runner, Ray limits and fixtures."""
import asyncio
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial

R=Path('/media/ubuntu/D1/zsj/Lego-RL-main')


async def main():
    out=R/'logs/swesmith_training_v6_harbor_20260930';out.mkdir(exist_ok=False)
    records=json.loads((R/'logs/swesmith_training_v6_pydicom_recheck_20260930/summary.json').read_text())
    assert records['total']==records['passed']==29
    ids=['tornadoweb__tornado.d5ac65c1.func_pm_ctrl_invert_if__fu602vyd','modin-project__modin.8c7799fd.func_pm_op_change__k3u0veeu','sunpy__sunpy.f8edfd5c.func_pm_ctrl_invert_if__0ba7h4uf','pydicom__pydicom.7d361b3d.combine_file__51x7mr1y']
    results=[]
    for iid in ids:
        row=next(x for x in records['results'] if x['instance_id']==iid)
        origin='swesmith_training_v6_native_recheck_20260930' if iid.startswith('tornadoweb__') else 'swesmith_training_v6_20260930'
        if iid.startswith('pydicom__'):origin='swesmith_training_v6_pydicom_recheck_20260930'
        for mode,expected in [('bug',0),('oracle',1)]:
            name=hashlib.sha256(iid.encode()).hexdigest()[:10]+'-'+mode
            task=out/'tasks'/name;shutil.copytree(row['task'],task)
            image='lego-swesmith-v6-harbor:'+name
            f=task/'task.toml';f.write_text(re.sub(r'docker_image = "[^"]+"',f'docker_image = "{image}"',f.read_text()))
            content='FROM '+row['task_image']+'\n'
            if mode=='oracle':
                patch=R/'logs'/origin/iid/'oracle.patch';shutil.copy2(patch,task/'environment/oracle.patch')
                content+='COPY oracle.patch /tmp/oracle.patch\nRUN cd /testbed && git apply /tmp/oracle.patch\n'
            (task/'environment/Dockerfile').write_text(content)
            with (out/(name+'-build.log')).open('w') as log:
                subprocess.run(['docker','build','--network','none','--pull=false','-t',image,str(task/'environment')],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
            cfg=TrialConfig.model_validate({'task':{'path':str(task)},'trial_name':name,'trials_dir':str(out/'trials'),'agent':{'name':'nop'},'environment':{'type':'docker','force_build':False,'delete':False},'predict_patch':{'enabled':False}})
            trial=await Trial.create(cfg);result=await trial.run()
            reward=result.verifier_result.rewards.get('reward') if result.verifier_result else None
            item={'instance_id':iid,'mode':mode,'reward':reward,'expected':expected,'exception':str(result.exception_info) if result.exception_info else None}
            results.append(item);(out/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(item),flush=True)
            assert reward==expected,item
    (out/'PASS.json').write_text(json.dumps(results,indent=2))


if __name__=='__main__':asyncio.run(main())
