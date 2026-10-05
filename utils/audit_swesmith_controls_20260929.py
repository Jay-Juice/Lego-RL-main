"""Bounded, isolated bug/oracle audit. Never mutates training assets."""
import concurrent.futures as cf
import hashlib
import json
import pathlib
import random
import re
import shutil
import subprocess as sp
import time

ROOT = pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
DATA = ROOT / 'data/swesmith_python_full_v7_verdict_v2_20260928'
OUT = ROOT / 'logs/swesmith_controls_audit_20260929'
LABEL = 'lego.controls.audit=20260929'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2))

def docker(name, image, script, args=(), mounts=(), timeout=380):
    argv = ['docker', 'run', '--rm', '--pull=never', '--name', name,
            '--label', LABEL, '--network', 'none', '--cpus', '4', '--memory', '8g']
    for src, dst, mode in mounts:
        argv += ['-v', f'{src}:{dst}:{mode}']
    argv += ['--entrypoint', '/bin/bash', image, '-c', script, 'audit', *args]
    try:
        p = sp.run(argv, stdout=sp.PIPE, stderr=sp.STDOUT, timeout=timeout)
        return p.returncode, p.stdout
    except sp.TimeoutExpired as e:
        return 124, (e.stdout or b'') + b'\nAUDIT_OUTER_TIMEOUT\n'
    finally:
        # Only our newly created, exactly named and labelled temporary container.
        q = sp.run(['docker', 'inspect', '--format', '{{index .Config.Labels "lego.controls.audit"}}', name], capture_output=True)
        if q.returncode == 0 and q.stdout.strip() == b'20260929':
            sp.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)

def run(item):
    row, reason = item
    iid = row['instance_id']
    assert re.fullmatch(r'[A-Za-z0-9_.-]+', iid)
    task = DATA / iid
    folder = OUT / iid
    folder.mkdir()
    result = dict(instance_id=iid, stratum=reason, repo=iid.split('.')[0],
                  fail_to_pass=row['FAIL_TO_PASS'], pass_to_pass=row['PASS_TO_PASS'],
                  base_image=row['base_image'], source_row_sha256=row['source_row_sha256'],
                  tests_sha={p.name: sha(p) for p in (task/'tests').iterdir() if p.is_file()})
    prefix = 'sao-controls-' + hashlib.sha256(iid.encode()).hexdigest()[:12]
    start = time.monotonic()
    try:
        if shutil.disk_usage(ROOT).free < 20 * 1024**3:
            raise RuntimeError('D1 below 20 GiB reserve')
        rc, patch = docker(prefix+'-extract', row['base_image'],
            'cd /testbed && git checkout --quiet "$1" && git diff --binary HEAD~1 HEAD~2', [iid], timeout=75)
        if rc or not patch.startswith(b'diff --git '):
            (folder/'extraction.log').write_bytes(patch)
            raise RuntimeError(f'oracle extraction invalid: {rc}')
        oracle = folder/'oracle.patch'
        oracle.write_bytes(patch)
        result['oracle_sha256'] = sha(oracle)
        cached = sp.run(['docker', 'image', 'inspect', row['task_image']], capture_output=True).returncode == 0
        image = row['task_image'] if cached else row['base_image']
        result['image_mode'] = 'cached_task_image' if cached else 'pinned_base_reconstruct_bug_commit'
        prepare = 'cd /testbed || exit 90; '
        if not cached:
            # Same build steps as production Dockerfile, inside this disposable
            # container; /testbed is never a host mount.
            prepare += 'git checkout --quiet "$1" || exit 91; test "$(git log -1 --format=%s)" = "Remove F2P Tests" || exit 92; rm -rf /testbed/.git; '
        for mode in ['bug', 'oracle']:
            logs = folder/mode
            logs.mkdir()
            mounts = [(task/'tests','/tests','ro'), (logs,'/logs','rw')]
            script = prepare
            if mode == 'oracle':
                mounts += [(oracle,'/oracle.patch','ro')]
                script += 'git apply /oracle.patch || exit 93; '
            script += '/tests/test.sh; rc=$?; chmod -R a+rwX /logs; exit $rc'
            t = time.monotonic()
            rc, output = docker(prefix+'-'+mode, image, script, [iid], mounts)
            (logs/'docker.log').write_bytes(output)
            rewardfile = logs/'verifier/reward.txt'
            statusfile = logs/'verifier/grading_status.json'
            reward = float(rewardfile.read_text().strip()) if rewardfile.exists() else None
            result[mode] = dict(exit_code=rc, reward=reward, seconds=round(time.monotonic()-t, 2),
                               grading_status=json.loads(statusfile.read_text()) if statusfile.exists() else None)
        result['control_pass'] = result['bug']['reward'] == 0 and result['oracle']['reward'] == 1
    except Exception as e:
        result['audit_error'] = repr(e)
        result['control_pass'] = False
    result['seconds'] = round(time.monotonic()-start, 2)
    dump(folder/'audit.json', result)
    return result

def main():
    OUT.mkdir(exist_ok=False)
    manifest = json.loads((DATA/'manifest.json').read_text())
    rows = manifest['tasks']
    rng = random.Random(20260929)
    selected = {}
    known = ['iterative__dvc.1d6ea681.func_pm_remove_loop__tu21q9d9',
             'python-trio__trio.cfbbe2c1.func_pm_class_rm_funcs__z53t7qz3',
             'python-trio__trio.cfbbe2c1.func_basic__e95hvdta']
    byid = {x['instance_id']: x for x in rows}
    for iid in known:
        selected[iid] = (byid[iid], 'historical_timeout')
    groups = {}
    for row in rows:
        groups.setdefault(row['instance_id'].split('.')[0], []).append(row)
    repos = sorted(groups)
    rng.shuffle(repos)
    for repo in repos[:80]:
        choices = [x for x in groups[repo] if x['instance_id'] not in selected]
        if choices:
            row = rng.choice(choices)
            selected[row['instance_id']] = (row, 'repository_random')
    heavy = sorted(rows, key=lambda x: x['FAIL_TO_PASS']+x['PASS_TO_PASS'], reverse=True)
    for row in heavy:
        if row['instance_id'] not in selected:
            selected[row['instance_id']] = (row, 'large_test_set')
        if len(selected) >= 92:
            break
    empty = [x for x in rows if not x['PASS_TO_PASS'] and x['instance_id'] not in selected]
    rng.shuffle(empty)
    for row in empty[:100-len(selected)]:
        selected[row['instance_id']] = (row, 'no_pass_to_pass')
    assert len(selected) == 100
    dump(OUT/'selection.json', dict(seed=20260929, manifest_sha256=sha(DATA/'manifest.json'),
         selected=[dict(**row,stratum=reason) for row,reason in selected.values()],
         note='Risk enriched, not a population error-rate estimate; four concurrent isolated 4CPU/8GB controls.'))
    results = []
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run, x) for x in selected.values()]
        for f in cf.as_completed(futures):
            result = f.result()
            results.append(result)
            print(json.dumps(dict(done=len(results), iid=result['instance_id'], ok=result['control_pass'],
                bug=result.get('bug',{}).get('reward'), oracle=result.get('oracle',{}).get('reward'),
                error=result.get('audit_error')),ensure_ascii=False), flush=True)
    summary = dict(total=len(results), passed=sum(x['control_pass'] for x in results),
                   repositories=len({x['repo'] for x in results}), results=results)
    dump(OUT/'summary.json', summary)
    print('AUDIT_DONE', summary['total'], summary['passed'], flush=True)

if __name__ == '__main__':
    main()
