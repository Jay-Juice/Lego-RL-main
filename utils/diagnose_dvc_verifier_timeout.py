"""Bounded oracle diagnostic; no alteration of grading or shared resources."""
import json
import shlex
from pathlib import Path
import audit_swesmith_controls_20260929 as audit


def main():
    r=audit.ROOT;iid='iterative__dvc.1d6ea681.func_pm_remove_loop__tu21q9d9'
    task=r/'data/swesmith_python_full_v7_verdict_v2_20260928'/iid
    row=json.loads((task/'tests/config.json').read_text());nodes=list(dict.fromkeys(row['FAIL_TO_PASS']+row['PASS_TO_PASS']))
    out=r/'logs/swesmith_dvc_bounded_20260930';out.mkdir(exist_ok=False)
    oracle=r/'logs/swesmith_controls_audit_20260929'/iid/'oracle.patch'
    script='cd /testbed; git checkout --quiet "$1"; rm -rf .git; git apply /oracle.patch || exit 93; cp -r /tests/payload/. /testbed/; export PATH=/opt/miniconda3/envs/testbed/bin:$PATH; export PYTHONPATH=/testbed; export HOME=/tmp/lego-smith-home; mkdir -p "$HOME"; '
    script+='timeout 110 /opt/miniconda3/envs/testbed/bin/python -u -m pytest -vv -s -p no:snail -n 0 --no-cov -o faulthandler_timeout=30 '+shlex.join(nodes)+' > /logs/test-output.log 2>&1; rc=$?; chmod -R a+rwX /logs; exit $rc'
    rc,output=audit.docker('sao-dvc-bounded-diagnostic',row['image'],script,[iid],[(task/'tests','/tests','ro'),(oracle,'/oracle.patch','ro'),(out,'/logs','rw')],timeout=140)
    (out/'docker.log').write_bytes(output);(out/'result.json').write_text(json.dumps({'exit_code':rc,'diagnostic_only':True,'changed_diagnostic_parallelism':0,'timeout_seconds':110,'oracle_sha256':audit.sha(oracle)}));print('diagnostic_exit',rc,flush=True)


if __name__=='__main__':main()
