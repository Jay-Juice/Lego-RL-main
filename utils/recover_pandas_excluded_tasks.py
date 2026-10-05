"""Recover six export-ignore omissions, without changing old manifests."""
import concurrent.futures as cf
import json
from pathlib import Path
import audit_swesmith_controls_20260929 as audit
from prepare_swesmith_harbor import write_task


def main():
    r=audit.ROOT
    source=r/'data/swesmith_python_full_v7_verdict_v2_20260928/manifest.json'
    manifest=json.loads(source.read_text()); ids={x['instance_id'] for x in manifest['excluded']}
    rows=[json.loads(line) for line in Path(manifest['source']).read_text().splitlines()]
    rows=[x for x in rows if x['instance_id'] in ids];assert len(rows)==6
    audit.DATA=r/'data/swesmith_pandas_recovered_20260930';audit.OUT=r/'logs/swesmith_pandas_recovered_20260930'
    audit.DATA.mkdir(exist_ok=False);audit.OUT.mkdir(exist_ok=False)
    selected=[]
    for x in rows:
        tag='lego-swesmith-pandas-recovered/'+x['instance_id'].lower().replace('_','-')+':20260930'
        write_task(x,audit.DATA/x['instance_id'],tag)
        selected.append(dict(instance_id=x['instance_id'],base_image=x['image'],task_image=tag,
            FAIL_TO_PASS=len(x['FAIL_TO_PASS']),PASS_TO_PASS=len(x['PASS_TO_PASS']),source_row_sha256=x['source_row_sha256']))
    audit.dump(audit.DATA/'manifest.json',{'tasks':selected,'activated_for_training':False})
    results=[]
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        for f in cf.as_completed([pool.submit(audit.run,(x,'export-ignore-recovery')) for x in selected]):
            x=f.result();results.append(x);print(json.dumps({'iid':x['instance_id'],'ok':x['control_pass'],'bug':x.get('bug'),'oracle':x.get('oracle'),'error':x.get('audit_error')}),flush=True)
    audit.dump(audit.OUT/'summary.json',{'total':len(results),'passed':sum(x['control_pass'] for x in results),'results':results})


if __name__=='__main__':main()
