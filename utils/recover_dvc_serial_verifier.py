"""Task-local serial pytest control; preserve test selection and verdict rules."""
import json
import shutil
import audit_swesmith_controls_20260929 as audit
from prepare_swesmith_harbor import RUN_TESTS, TEST_SH


def main():
    r = audit.ROOT
    iid = 'iterative__dvc.1d6ea681.func_pm_remove_loop__tu21q9d9'
    old = r/'data/swesmith_python_full_v7_verdict_v2_20260928'
    row = next(x for x in json.loads((old/'manifest.json').read_text())['tasks'] if x['instance_id'] == iid)
    audit.DATA = r/'data/swesmith_dvc_serial_recovered_20260930'
    audit.OUT = r/'logs/swesmith_dvc_serial_recovered_20260930'
    audit.DATA.mkdir(exist_ok=False)
    audit.OUT.mkdir(exist_ok=False)
    task = audit.DATA/iid
    shutil.copytree(old/iid, task)
    assert RUN_TESTS.count('command += ["-n", "2"]') == 1
    verifier = RUN_TESTS.replace('command += ["-n", "2"]', 'command += ["-n", "0"]')
    (task/'tests/run_tests.py').write_text(verifier)
    (task/'tests/test.sh').write_text(TEST_SH)
    result = audit.run((row, 'task-local-pytest-serial'))
    audit.dump(audit.OUT/'summary.json', {'total':1, 'passed':int(result['control_pass']), 'results':[result],
               'change':'pytest -n 2 to -n 0 for this task only; nodes, assertions, timeout, JUnit rules unchanged'})
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
