"""Build four new task-local repairs and execute unchanged bug/oracle controls."""
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import audit_swesmith_controls_20260929 as audit

R = audit.ROOT
SOURCE = R/'data/swesmith_python_full_v7_verdict_v4_candidate_20260930'
DATA = R/'data/swesmith_final_four_v5_20260930'
OUT = R/'logs/swesmith_final_four_v5_20260930'
POLICIES = {
    'john-kurkowski__tldextract.3d1bf184.pr_325':'missing_local_release_module',
    'pydata__patsy.a5d16484.pr_140':'removed_stdlib_mapping_import',
    'gawel__pyquery.811cd048.func_pm_ctrl_shuffle__1355aoe9':'displaced_closest_doctest',
}
CONAN = 'conan-io__conan.86f29e13.pr_15457'


def run(item):
    iid = item['instance_id']; task = DATA/iid; log = OUT/iid; log.mkdir()
    shutil.copytree(SOURCE/iid, task)
    code = (task/'tests/run_tests.py').read_text()
    config = json.loads((task/'tests/config.json').read_text())
    if iid in POLICIES:
        config['collection_failure_policy'] = POLICIES[iid]
        (task/'tests/config.json').write_text(json.dumps(config, indent=2))
        shutil.copy2(Path(__file__).with_name('swesmith_collection_verdict.py'), task/'tests/swesmith_collection_verdict.py')
        needle = '        if result.returncode not in (0, 1):'
        assert code.count(needle) == 1
        insertion = '''        from swesmith_collection_verdict import known_candidate_failure
        cause = known_candidate_failure(config, TESTBED, report, result.returncode, result.stdout)
        if cause is not None:
            reward_path.write_text("0\\n")
            status_path.write_text(json.dumps({"status":"scored", "reward":0,
                "protocol":"candidate-collection-verdict-v5", "reason":cause,
                "pytest_exit_code":result.returncode}))
            return 0
'''
        code = code.replace(needle, insertion + needle)
        oracle = Path(item['control']['evidence']).parent/iid/'oracle.patch'
    else:
        assert iid == CONAN
        cmake = Path('/opt/cmake-3.22.1-linux-x86_64')
        version = subprocess.check_output([str(cmake/'bin/cmake'),'--version'], text=True)
        assert 'cmake version 3.22.1' in version
        shutil.copytree(cmake, task/'environment/cmake', symlinks=True)
        tool_config = 'tools_locations = {"cmake":{"default":"3.22", "3.22":{"path":{"Linux":"/opt/lego-cmake/bin"}}}}\n'
        (task/'tests/conftest_user.py').write_text(tool_config)
        (task/'environment/conftest_user.py').write_text(tool_config)
        f = task/'environment/Dockerfile'
        f.write_text(f.read_text()+'\nCOPY cmake/ /opt/lego-cmake/\nCOPY conftest_user.py /testbed/test/conftest_user.py\nENV PATH="/opt/lego-cmake/bin:${PATH}"\n')
        code = code.replace('        restore_dedicated_tests(config)', '        shutil.copy2(TESTS/"conftest_user.py", TESTBED/"test/conftest_user.py")\n        restore_dedicated_tests(config)')
        oracle = R/'logs/swesmith_controls_audit_20260929'/iid/'oracle.patch'
        (log/'cmake_provenance.json').write_text(json.dumps({'source':str(cmake),'version':version,
             'files':{str(p.relative_to(cmake)):audit.sha(p) for p in cmake.rglob('*') if p.is_file()}}))
    (task/'tests/run_tests.py').write_text(code)
    shutil.copy2(oracle, log/'oracle.patch')
    tag = 'lego-final-four-v5:'+hashlib.sha256(iid.encode()).hexdigest()[:16]
    f = task/'task.toml'; f.write_text(re.sub(r'docker_image = "[^"]+"',f'docker_image = "{tag}"',f.read_text()))
    assert subprocess.run(['docker','image','inspect',tag],capture_output=True).returncode != 0
    with (log/'build.log').open('w') as handle:
        subprocess.run(['docker','build','--network','none','--pull=false','-t',tag,str(task/'environment')],stdout=handle,stderr=subprocess.STDOUT,check=True,timeout=180)
    result = {'instance_id':iid,'task':str(task),'task_image':tag,'oracle_sha256':audit.sha(oracle),'control_pass':False}
    for mode in ['bug','oracle']:
        folder = log/mode; folder.mkdir()
        script = 'cd /testbed || exit 90; '
        if mode == 'oracle': script += 'git apply /oracle.patch || exit 93; '
        script += '/tests/test.sh; rc=$?; chmod -R a+rwX /logs; exit $rc'
        start = time.monotonic()
        rc, output = audit.docker('sao-final-four-'+hashlib.sha256(iid.encode()).hexdigest()[:10]+'-'+mode,tag,script,
            mounts=[(task/'tests','/tests','ro'),(folder,'/logs','rw'),(oracle,'/oracle.patch','ro')])
        (folder/'docker.log').write_bytes(output)
        reward = folder/'verifier/reward.txt'; status = folder/'verifier/grading_status.json'
        result[mode]={'reward':float(reward.read_text()) if reward.exists() else None,'exit_code':rc,
          'seconds':round(time.monotonic()-start,2),'status':json.loads(status.read_text()) if status.exists() else None}
    result['control_pass'] = result['bug']['reward']==0 and result['oracle']['reward']==1
    audit.dump(log/'audit.json',result)
    return result


def main():
    DATA.mkdir(exist_ok=False); OUT.mkdir(exist_ok=False)
    rows = json.loads((SOURCE/'manifest.json').read_text())['pending']; assert len(rows)==4
    results=[]
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        for f in cf.as_completed([pool.submit(run,x) for x in rows]):
            result=f.result(); results.append(result);print(json.dumps(result),flush=True)
    audit.dump(OUT/'summary.json',{'total':4,'passed':sum(x['control_pass'] for x in results),'results':results})


if __name__=='__main__':main()
