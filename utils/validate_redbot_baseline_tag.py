"""Isolated real-Harbor control for a Git baseline tag/version collision."""
import asyncio
import json
from pathlib import Path
import re
import shutil
import subprocess
from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
import audit_swesmith_controls_20260929 as audit

R = audit.ROOT
IID = 'Cog-Creators__Red-DiscordBot.33e0eac7.func_basic__jhzylht3'

async def main():
    out = R/'logs/redbot_baseline_tag_control_20260930'
    out.mkdir(exist_ok=False)
    source = R/'data/swesmith_python_full_v7_verdict_v6_20260930'/IID
    config = json.loads((source/'tests/config.json').read_text())
    rc, patch = audit.docker('redbot-tag-oracle-extract', config['image'],
        'cd /testbed && git -c safe.directory=/testbed checkout --quiet "$1" && git -c safe.directory=/testbed diff --binary HEAD~1 HEAD~2', [IID], timeout=90)
    assert rc == 0 and patch.startswith(b'diff --git ')
    (out/'oracle.patch').write_bytes(patch)
    records = []
    for mode, tag, expected in [('oracle-old','harbor-baseline',None), ('bug-new','harborbaseline',0), ('oracle-new','harborbaseline',1)]:
        task = out/'tasks'/mode
        shutil.copytree(source, task)
        image = 'lego-redbot-baseline-control:'+mode
        p = task/'task.toml'
        p.write_text(re.sub(r'docker_image = "[^"]+"', f'docker_image = "{image}"', p.read_text()))
        if mode.startswith('oracle'):
            shutil.copy2(out/'oracle.patch', task/'environment/oracle.patch')
            p = task/'environment/Dockerfile'
            p.write_text(p.read_text()+'\nCOPY oracle.patch /tmp/oracle.patch\nRUN cd /testbed && git apply /tmp/oracle.patch\n')
        with (out/(mode+'-build.log')).open('w') as log:
            subprocess.run(['docker','build','--network','none','--pull=false','-t',image,str(task/'environment')],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        cfg=TrialConfig.model_validate({'task':{'path':str(task)},'trial_name':mode,'trials_dir':str(out/'trials'),
            'agent':{'name':'nop'},'environment':{'type':'docker','force_build':False,'delete':True},
            'predict_patch':{'enabled':True,'repo_paths':['/testbed'],'auto_discover':False,'baseline_tag':tag}})
        trial=await Trial.create(cfg)
        result=await asyncio.wait_for(trial.run(),timeout=600)
        reward=result.verifier_result.rewards.get('reward') if result.verifier_result else None
        record={'mode':mode,'tag':tag,'reward':reward,'expected':expected,'exception':str(result.exception_info) if result.exception_info else None,'oracle_sha256':audit.sha(out/'oracle.patch')}
        records.append(record)
        (out/'results.json').write_text(json.dumps(records,indent=2))
        print(json.dumps(record),flush=True)
        assert reward==expected,record
        if expected is not None: assert result.exception_info is None,record
    (out/'PASS.json').write_text(json.dumps(records,indent=2))

if __name__=='__main__': asyncio.run(main())
