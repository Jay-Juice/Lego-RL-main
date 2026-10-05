"""Repeat the same frozen audit selection on eligible v3 tasks, no resampling."""
import argparse
import concurrent.futures as cf
import json
import pathlib
import audit_swesmith_controls_20260929 as audit


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--selection',type=pathlib.Path,required=True)
    args=p.parse_args()
    audit.DATA=args.data.resolve();audit.OUT=args.output.resolve()
    audit.OUT.mkdir(exist_ok=False)
    manifest=json.loads((audit.DATA/'manifest.json').read_text())
    current={x['instance_id']:x for x in manifest['tasks']}
    old=json.loads(args.selection.read_text())['selected']
    selected=[(current[x['instance_id']],x['stratum']) for x in old if x['instance_id'] in current]
    excluded=[x['instance_id'] for x in old if x['instance_id'] not in current]
    assert selected
    audit.dump(audit.OUT/'selection.json',dict(source_selection_sha256=audit.sha(args.selection),
        manifest_sha256=audit.sha(audit.DATA/'manifest.json'),excluded_from_original_selection=excluded,
        selected=[dict(**r,stratum=s) for r,s in selected]))
    results=[]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        for f in cf.as_completed([pool.submit(audit.run,item) for item in selected]):
            x=f.result();results.append(x)
            print(json.dumps(dict(done=len(results),iid=x['instance_id'],ok=x['control_pass'])),flush=True)
    summary=dict(total=len(results),passed=sum(x['control_pass'] for x in results),
        exclusions=excluded,results=results)
    audit.dump(audit.OUT/'summary.json',summary)
    print('DONE',summary['total'],summary['passed'],flush=True)
    if summary['passed']!=summary['total']:raise SystemExit(1)


if __name__=='__main__':main()
