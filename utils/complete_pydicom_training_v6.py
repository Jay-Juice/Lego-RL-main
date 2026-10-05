"""Materialize checksum-verified official test data in new task-local images."""
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import prepare_swesmith_training_v6 as v6
from audit_swesmith_controls_20260929 import dump,sha


def main():
    previous=v6.R/'logs/swesmith_training_v6_native_recheck_20260930/summary.json'
    summary=json.loads(previous.read_text())
    source=Path('/media/ubuntu/D1/zsj/agent-lightning-runtime/data/swe-smith-training/pydicom-download-fixtures-v2')
    provenance=json.loads((source/'manifest.json').read_text())
    stage=v6.NEW/'runtime_assets/pydicom';stage.mkdir(parents=True,exist_ok=False)
    (stage/'data').mkdir()
    for item in provenance['files']:
        name=item['name'];assert Path(name).name==name
        f=source/'data'/name;assert sha(f)==item['sha256'] and f.stat().st_size==item['size']
        shutil.copy2(f,stage/'data'/name)
    (stage/'Dockerfile').write_text('FROM scratch\nCOPY data/ /pydicom-data/\n')
    fixture_image='lego-pydicom-official-data:v6-20260930'
    with (stage/'build.log').open('w') as log:
        subprocess.run(['docker','build','--network','none','--pull=false','-t',fixture_image,str(stage)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    dump(stage/'provenance.json',{'source':str(source),'source_manifest_sha256':sha(source/'manifest.json'),'files':provenance['files'],'fixture_image':fixture_image})
    manifest=json.loads((v6.NEW/'manifest.json').read_text())
    for row in manifest['tasks']:
        iid=row['instance_id']
        if not iid.startswith('pydicom__pydicom.'):continue
        task=v6.NEW/iid;f=task/'environment/Dockerfile'
        f.write_text(f.read_text()+f'\nCOPY --from={fixture_image} /pydicom-data/ /tmp/lego-smith-home/.pydicom/data/\n')
        tag='lego-swesmith-v6-pydicom:'+hashlib.sha256(iid.encode()).hexdigest()[:20]
        f=task/'task.toml';f.write_text(re.sub(r'docker_image = "[^"]+"',f'docker_image = "{tag}"',f.read_text()))
        row['dockerfile_sha256']=sha(task/'environment/Dockerfile')
    dump(v6.NEW/'manifest.json',manifest)
    v6.OUT=v6.R/'logs/swesmith_training_v6_pydicom_recheck_20260930';v6.OUT.mkdir(exist_ok=False)
    ids=[x['instance_id'] for x in summary['results'] if x['instance_id'].startswith('pydicom__pydicom.')]
    with cf.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(v6.control,ids))
    combined=[x for x in summary['results'] if x['instance_id'] not in ids]+results
    report={'total':len(combined),'passed':sum(x['control_pass'] for x in combined),'results':combined,'predecessor':str(previous),'fixture_provenance':str(stage/'provenance.json')}
    dump(v6.OUT/'summary.json',report);print('FINAL_CONTROLS',report['passed'],report['total'],flush=True)
    assert report['passed']==report['total']==29


if __name__=='__main__':main()
