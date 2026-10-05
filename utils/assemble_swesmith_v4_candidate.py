"""Reassemble all 6248 AL-v7 task IDs; preserve unresolved readiness explicitly."""
import hashlib
import json
from pathlib import Path
import shutil
import pandas as pd
from prepare_swesmith_harbor import RUN_TESTS, TEST_SH, parquet_row

ROOT=Path('/media/ubuntu/D1/zsj/Lego-RL-main')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    old=ROOT/'data/swesmith_python_full_v7_verdict_v2_20260928'
    oldmanifest=json.loads((old/'manifest.json').read_text())
    rows=[json.loads(l) for l in Path(oldmanifest['source']).read_text().splitlines()]
    assert len(rows)==6248 and len({r['instance_id'] for r in rows})==6248
    target=ROOT/'data/swesmith_python_full_v7_verdict_v4_candidate_20260930';target.mkdir(exist_ok=False)
    controls={}
    for folder in ['swesmith_embedded_repair_v4b_20260930','swesmith_patsy_reportguard_v4_20260930','swesmith_furl_recovered_20260930','swesmith_pandas_recovered_20260930','swesmith_dvc_serial_recovered_20260930','swesmith_pyquery_http_recovered_v4b_20260930']:
        p=ROOT/'logs'/folder/'summary.json'; m=json.loads(p.read_text())
        for row in m['results']: controls[row['instance_id']]=dict(row,evidence=str(p),evidence_sha256=sha(p))
    choices=['swesmith_pyquery_http_recovered_v4b_20260930','swesmith_dvc_serial_recovered_20260930','swesmith_patsy_reportguard_v4_20260930','swesmith_embedded_repaired_v4b_20260930','swesmith_furl_recovered_20260930','swesmith_pandas_recovered_20260930','swesmith_python_full_v7_verdict_v3_20260929','swesmith_python_full_v7_verdict_v2_20260928']
    original=pd.read_parquet(str(old)+'.parquet');byid={r['extra_info']['instance_id']:r.to_dict() for _,r in original.iterrows()}
    output=[]; provenance=[]; pending=[]
    frozen_before={'manifest':sha(old/'manifest.json'),'parquet':sha(Path(str(old)+'.parquet'))}
    for row in rows:
        iid=row['instance_id']; src=next(ROOT/'data'/name/iid for name in choices if (ROOT/'data'/name/iid).is_dir())
        dst=target/iid;shutil.copytree(src,dst)
        if src.parent==old:
            (dst/'tests/run_tests.py').write_text(RUN_TESTS);(dst/'tests/test.sh').write_text(TEST_SH)
        record=byid.get(iid)
        if record is None:
            # Same schema as the original preparer's parquet rows.
            record=parquet_row(dst,row)
        else:
            record=dict(record); record['prompt']=[dict(x) for x in record['prompt']]
            record['prompt'][0]['content']=str(dst);record['extra_info']=dict(record['extra_info']);record['extra_info']['harbor_task_path']=str(dst)
        output.append(record)
        c=controls.get(iid); status='matched_bug_oracle_pass' if c and c['control_pass'] else ('control_unresolved' if c else 'not_rechecked_in_this_repair')
        if (c and not c['control_pass']) or iid.startswith('conan-io__conan.86f29e13.pr_15457'):
            pending.append({'instance_id':iid,'control':c,'note':'Preserved; not approved for training by this audit'})
        provenance.append({'instance_id':iid,'asset_source':str(src),'status':status,
                           'run_tests_sha256':sha(dst/'tests/run_tests.py'),'config_sha256':sha(dst/'tests/config.json'),
                           'dockerfile_sha256':sha(dst/'environment/Dockerfile'),
                           'control_evidence':c.get('evidence') if c else None})
    frame=pd.DataFrame(output); parquet=Path(str(target)+'.parquet');frame.to_parquet(parquet,index=False)
    assert [x['instance_id'] for x in pd.read_parquet(parquet).extra_info]==[x['instance_id'] for x in rows]
    assert frozen_before=={'manifest':sha(old/'manifest.json'),'parquet':sha(Path(str(old)+'.parquet'))}
    manifest={'task_count':6248,'tasks':provenance,'source_jsonl':oldmanifest['source'],'source_jsonl_sha256':sha(Path(oldmanifest['source'])),
        'row_order_matches_AL_v7':True,'original_6242_preserved':True,'restored_pandas_task_count':6,
        'activated_for_training':False,'training_ready':False,'pending':pending,
        'note':'Full membership candidate, not a claim of full runtime certification. Do not launch training until pending controls and environment dependencies are resolved.',
        'parquet_sha256':sha(parquet),'original_sha256':frozen_before}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'tasks':6248,'pending_count':len(pending),'pending_ids':[x['instance_id'] for x in pending],'parquet':str(parquet),'training_ready':False}),flush=True)


if __name__=='__main__':main()
