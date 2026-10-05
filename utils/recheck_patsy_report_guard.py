"""Repeat all 70 Patsy controls with task-local exception rendering guard."""
import concurrent.futures as cf
import json
import shutil
from pathlib import Path
import repair_swesmith_embedded_assets as repair


def main():
    repair.TARGET=repair.ROOT/'data/swesmith_patsy_reportguard_v4_20260930'
    repair.OUT=repair.ROOT/'logs/swesmith_patsy_reportguard_v4_20260930'
    repair.TARGET.mkdir(exist_ok=False);repair.OUT.mkdir(exist_ok=False)
    # Scope guard to these Patsy tasks. No shared package installation or edits.
    repair.RUN_TESTS=repair.RUN_TESTS.replace('        command += nodes', '        command += ["-p", "swesmith_pytest_report_guard"]\n        command += nodes').replace('"PYTHONPATH": "/testbed"','"PYTHONPATH": "/testbed:/tests"')
    original_copytree=shutil.copytree
    def copytree(src,dst,*args,**kwargs):
        result=original_copytree(src,dst,*args,**kwargs)
        if Path(dst).parent == repair.TARGET:
            shutil.copy2(Path(__file__).with_name('swesmith_pytest_report_guard.py'),Path(dst)/'tests/swesmith_pytest_report_guard.py')
        return result
    repair.shutil.copytree=copytree
    q=json.loads((repair.ROOT/'data/swesmith_python_full_v7_verdict_v3_20260929/quarantine.json').read_text())
    ids={x['instance_id'] for x in q if x['unsafe_restore_paths'] and x['instance_id'].startswith('pydata__patsy.')}
    rows=[x for x in json.loads((repair.SOURCE/'manifest.json').read_text())['tasks'] if x['instance_id'] in ids];assert len(rows)==70
    results=[]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        for f in cf.as_completed([pool.submit(repair.run,row) for row in rows]):
            x=f.result();results.append(x);print(json.dumps({'done':len(results),'iid':x['instance_id'],'pass':x['control_pass'],'bug':x.get('bug',{}).get('reward'),'oracle':x.get('oracle',{}).get('reward'),'error':x.get('error')}),flush=True)
    repair.audit.dump(repair.OUT/'summary.json',{'total':len(results),'passed':sum(x['control_pass'] for x in results),'results':results})


if __name__=='__main__':main()
