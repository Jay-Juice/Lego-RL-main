"""Recheck native-runner reporting before activating this turn's new assets."""
import concurrent.futures as cf
import json
from pathlib import Path
import shutil
import prepare_swesmith_training_v6 as v6
from audit_swesmith_controls_20260929 import dump,sha


def main():
    old=v6.OUT
    summary=json.loads((old/'summary.json').read_text())
    v6.OUT=v6.R/'logs/swesmith_training_v6_native_recheck_20260930'
    v6.OUT.mkdir(exist_ok=False)
    source=Path(__file__).with_name('swesmith_special_runners.py')
    ids=[x['instance_id'] for x in summary['results'] if x['instance_id'].startswith('tornadoweb__tornado.')]
    assert len(ids)==15
    for iid in ids:
        target=v6.NEW/iid/'tests/swesmith_special_runners.py'
        shutil.copy2(target,v6.OUT/(iid+'.old-runner.py'))
        shutil.copy2(source,target)
    with cf.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(v6.control,ids))
    combined=[x for x in summary['results'] if x['instance_id'] not in ids]+results
    report={'total':len(combined),'passed':sum(x['control_pass'] for x in combined),'results':combined,'native_runner_sha256':sha(source),'superseded_native_results':str(old/'summary.json')}
    dump(v6.OUT/'summary.json',report)
    print('RECHECK',report['passed'],report['total'],flush=True)


if __name__=='__main__':main()
