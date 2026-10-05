"""Build and test isolated replacements for the 164 mixed/document tasks.

No historical files are replaced. A passing audit is necessary before these
replacement assets may be included in any new training index.
"""
import concurrent.futures as cf
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import tarfile
import time
import audit_swesmith_controls_20260929 as audit
from prepare_swesmith_harbor import RUN_TESTS
from swesmith_embedded import dedicated, embedded_tests, normalize_tests

ROOT=audit.ROOT
SOURCE=ROOT/'data/swesmith_python_full_v7_verdict_v2_20260928'
TARGET=ROOT/'data/swesmith_embedded_repaired_v4b_20260930'
OUT=ROOT/'logs/swesmith_embedded_repair_v4b_20260930'


def run(row):
    iid=row['instance_id']; old=SOURCE/iid; task=TARGET/iid; log=OUT/iid
    log.mkdir(); result={'instance_id':iid,'control_pass':False}
    prefix='sao-mixed-v4-'+hashlib.sha256(iid.encode()).hexdigest()[:12]
    try:
        if shutil.disk_usage(ROOT).free < 20*1024**3:raise RuntimeError('D1 reserve insufficient')
        config=json.loads((old/'tests/config.json').read_text())
        paths=sorted({n.split('::',1)[0] for n in config['FAIL_TO_PASS']+config['PASS_TO_PASS']})
        mixed=[p for p in paths if not dedicated(p) and p.endswith('.py')]
        docs=[p for p in paths if not dedicated(p) and not p.endswith('.py')]
        if any(Path(p).suffix.lower() not in {'.rst','.md','.txt'} for p in docs):raise ValueError('Unrecognized document format')
        refs={}
        if mixed:
            rc,raw=audit.docker(prefix+'-refs',row['base_image'],
                'cd /testbed && git checkout --quiet "$1" && shift && git archive HEAD~2 -- "$@"',
                [iid,*mixed],timeout=90)
            if rc:raise RuntimeError('Reference extraction failed: '+raw.decode(errors='replace')[-1000:])
            with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
                for path in mixed:
                    f=tf.extractfile(path)
                    if f is None:raise ValueError('Missing reference source')
                    refs[path]=f.read().decode()
        shutil.copytree(old,task)
        boot=task/'environment/embedded_source'; boot.mkdir()
        normalized=[]
        for path in mixed:
            payload=task/'tests/payload'/path; buggy=payload.read_text()
            fixed,names=normalize_tests(buggy,refs[path])
            if not embedded_tests(fixed):raise ValueError('Source has no identified embedded tests')
            dest=boot/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(fixed)
            payload.write_text(fixed)
            normalized.append({'path':path,'normalized_tests':names,'bug_sha256':hashlib.sha256(buggy.encode()).hexdigest(),
                               'prepared_sha256':audit.sha(dest),'reference_sha256':hashlib.sha256(refs[path].encode()).hexdigest()})
        dockerfile=task/'environment/Dockerfile'
        if mixed:dockerfile.write_text(dockerfile.read_text()+'\nCOPY embedded_source/ /testbed/\n')
        toml=task/'task.toml'
        toml.write_text(re.sub(r'docker_image = "[^"]+"',f'docker_image = "lego-swesmith-v4/{hashlib.sha256(iid.encode()).hexdigest()[:20]}:20260930"',toml.read_text()))
        code=RUN_TESTS.replace('        restore_dedicated_tests(config)','        from swesmith_embedded import restore_mixed_tests\n        restore_mixed_tests(config, TESTBED, TESTS)').replace('dedicated-tests-verdict-v3','mixed-tests-verdict-v4')
        (task/'tests/run_tests.py').write_text(code)
        shutil.copy2(Path(__file__).with_name('swesmith_embedded.py'),task/'tests/swesmith_embedded.py')
        # Normalize the BUG baseline index before diffing to the reference, as
        # the previous Agent Lightning adapter did for six mixed test mutations.
        setup='cd /testbed || exit 90; git checkout --quiet "$1" || exit 91; cp -r /bootstrap/. /testbed/ || exit 92; '
        extraction=setup+'git diff --name-only -z HEAD~1 HEAD~2 > /tmp/changed-v4; git add -u; git diff --binary -R --cached HEAD~2 --pathspec-from-file=/tmp/changed-v4 --pathspec-file-nul'
        # git diff lacks --pathspec-from-file on older git: use Python to pass argv.
        extraction=setup+'''python -c 'import subprocess; paths=subprocess.check_output(["git","diff","--name-only","-z","HEAD~1","HEAD~2"]).decode().strip("\\0").split("\\0"); subprocess.check_call(["git","add","-A"]); subprocess.check_call(["git","diff","--binary","-R","--cached","HEAD~2","--",*paths])' '''
        rc,patch=audit.docker(prefix+'-oracle',row['base_image'],extraction,[iid],[(boot,'/bootstrap','ro')],timeout=90)
        (log/'oracle_extraction.log').write_bytes(patch)
        if rc or not patch.startswith(b'diff --git '):raise RuntimeError('Normalized oracle empty or invalid '+str(rc))
        oracle=log/'oracle.patch'; oracle.write_bytes(patch)
        result.update(normalized=normalized,document_paths=docs,oracle_sha256=audit.sha(oracle),
                      verifier_sha256=audit.sha(task/'tests/run_tests.py'),task=str(task))
        for mode in ['bug','oracle']:
            logs=log/mode; logs.mkdir()
            mounts=[(task/'tests','/tests','ro'),(boot,'/bootstrap','ro'),(logs,'/logs','rw'),(oracle,'/oracle.patch','ro')]
            script=setup+'rm -rf /testbed/.git; '
            if mode=='oracle':script+='git apply /oracle.patch || exit 93; '
            # Assert byte-preservation of all mixed implementation files during grading.
            (logs/'mixed_paths.json').write_text(json.dumps(mixed))
            script+='''/opt/miniconda3/envs/testbed/bin/python -c 'import json,hashlib; from pathlib import Path; p=json.loads(Path("/logs/mixed_paths.json").read_text()); Path("/logs/source_before.json").write_text(json.dumps({x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in p}))'; /tests/test.sh; rc=$?; /opt/miniconda3/envs/testbed/bin/python -c 'import json,hashlib; from pathlib import Path; before=json.loads(Path("/logs/source_before.json").read_text()); after={x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in before}; Path("/logs/source_preserved.json").write_text(json.dumps({"preserved":before==after})); assert before==after'; check=$?; chmod -R a+rwX /logs; test $check = 0 || exit 94; exit $rc'''
            start=time.monotonic(); rc,output=audit.docker(prefix+'-'+mode,row['base_image'],script,[iid],mounts)
            (logs/'docker.log').write_bytes(output)
            rp=logs/'verifier/reward.txt'; sp=logs/'verifier/grading_status.json'; bp=logs/'source_preserved.json'
            result[mode]={'exit_code':rc,'reward':float(rp.read_text()) if rp.exists() else None,
                          'source_preserved':json.loads(bp.read_text())['preserved'] if bp.exists() else False,
                          'seconds':round(time.monotonic()-start,2),'status':json.loads(sp.read_text()) if sp.exists() else None}
        result['control_pass']=result['bug']['reward']==0 and result['oracle']['reward']==1 and all(result[m]['source_preserved'] for m in ['bug','oracle'])
    except Exception as e:result['error']=repr(e)
    audit.dump(log/'audit.json',result)
    return result


def main():
    TARGET.mkdir(exist_ok=False);OUT.mkdir(exist_ok=False)
    q=json.loads((ROOT/'data/swesmith_python_full_v7_verdict_v3_20260929/quarantine.json').read_text())
    ids={x['instance_id'] for x in q if x['unsafe_restore_paths']}
    rows=[x for x in json.loads((SOURCE/'manifest.json').read_text())['tasks'] if x['instance_id'] in ids]
    assert len(rows)==164
    audit.dump(OUT/'selection.json',{'count':len(rows),'ids':sorted(ids),'source_manifest_sha256':audit.sha(SOURCE/'manifest.json')})
    results=[]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        for f in cf.as_completed([pool.submit(run,row) for row in rows]):
            x=f.result();results.append(x);print(json.dumps({'done':len(results),'iid':x['instance_id'],'pass':x['control_pass'],'error':x.get('error'),'bug':x.get('bug',{}).get('reward'),'oracle':x.get('oracle',{}).get('reward')}),flush=True)
    summary={'total':len(results),'passed':sum(x['control_pass'] for x in results),'results':results,'activated_for_training':False}
    audit.dump(OUT/'summary.json',summary);print('DONE',summary['passed'],summary['total'],flush=True)


if __name__=='__main__':main()
