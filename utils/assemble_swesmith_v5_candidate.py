"""Publish a new full-membership candidate after four-task Harbor acceptance."""
import json
from pathlib import Path
import shutil
import pandas as pd
from audit_swesmith_controls_20260929 import ROOT, sha


def main():
    old=ROOT/'data/swesmith_python_full_v7_verdict_v4_candidate_20260930'
    target=ROOT/'data/swesmith_python_full_v7_verdict_v5_candidate_20260930'
    controls=ROOT/'logs/swesmith_final_four_v5_20260930/summary.json'
    integration=ROOT/'logs/swesmith_final_four_harbor_v5_20260930/PASS.json'
    results=json.loads(controls.read_text())
    checks=json.loads(integration.read_text())
    assert results['passed']==results['total']==4
    assert len(checks)==11 and all(x['reward']==x['expected'] for x in checks)
    before={str(p):sha(p) for p in [old/'manifest.json',Path(str(old)+'.parquet')]}
    manifest=json.loads((old/'manifest.json').read_text())
    replacements={x['instance_id']:x for x in results['results']}
    assert set(replacements)=={x['instance_id'] for x in manifest['pending']}
    target.mkdir(exist_ok=False)
    for row in manifest['tasks']:
        iid=row['instance_id']; replacement=replacements.get(iid)
        source=Path(replacement['task']) if replacement else old/iid
        dst=target/iid;shutil.copytree(source,dst)
        if replacement:
            row.update(asset_source=str(source),status='matched_bug_oracle_pass',control_evidence=str(controls),
                control_evidence_sha256=sha(controls),run_tests_sha256=sha(dst/'tests/run_tests.py'),
                config_sha256=sha(dst/'tests/config.json'),dockerfile_sha256=sha(dst/'environment/Dockerfile'))
    frame=pd.read_parquet(str(old)+'.parquet');rows=[]
    for _,series in frame.iterrows():
        row=series.to_dict();iid=row['extra_info']['instance_id'];dst=target/iid
        row['prompt']=[dict(x) for x in row['prompt']];row['prompt'][0]['content']=str(dst)
        row['extra_info']=dict(row['extra_info']);row['extra_info']['harbor_task_path']=str(dst);rows.append(row)
    pd.DataFrame(rows).to_parquet(str(target)+'.parquet',index=False)
    assert [x['instance_id'] for x in pd.read_parquet(str(target)+'.parquet').extra_info]==[x['instance_id'] for x in frame.extra_info]
    assert before=={p:sha(Path(p)) for p in before}
    manifest.update(pending=[],last_four_resolved=True,task_count=len(rows),training_ready=False,activated_for_training=False,
        full_dataset_dynamically_certified=False,parquet_sha256=sha(Path(str(target)+'.parquet')),
        predecessor_sha256=before,harbor_acceptance={'path':str(integration),'sha256':sha(integration)},
        note='All 167 previously quarantined tasks plus 6 extraction omissions recovered. Full 6248 membership and order preserved. Targeted controls complete; full-dataset dynamic certification and training launch are separate.')
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'tasks':len(rows),'pending':0,'control_pass_tasks':sum(x['status']=='matched_bug_oracle_pass' for x in manifest['tasks']),
                      'activated_for_training':False,'path':str(target)}),flush=True)


if __name__=='__main__':main()
