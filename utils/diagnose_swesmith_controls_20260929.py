"""Isolated causal checks for audit anomalies; never changes production assets."""
import ast
import hashlib
import json
import pathlib
import re
import shutil
import time
from audit_swesmith_controls_20260929 import ROOT, DATA, OUT, docker, dump, sha

DEST = ROOT/'logs/swesmith_controls_diagnosis_20260929'

def main():
    DEST.mkdir(exist_ok=False)
    rows={r['instance_id']:r for r in json.loads((DATA/'manifest.json').read_text())['tasks']}
    ids=['davidhalter__parso.338a5760.func_basic__xlbdayjr',
         'pydata__patsy.a5d16484.func_basic__dg2dvm91',
         'pwaller__pyfiglet.f8c5f35b.combine_file__sind222x',
         'conan-io__conan.86f29e13.pr_15457']
    results=[]
    for iid in ids:
        row=rows[iid];task=DATA/iid;folder=DEST/iid;folder.mkdir()
        oracle=OUT/iid/'oracle.patch'; overlap=[]
        for path in re.findall(r'^\+\+\+ b/(.+)$',oracle.read_text(),re.M):
            if (task/'tests/payload'/path).exists(): overlap.append(path)
        if overlap:
            tree=ast.parse((task/'tests/run_tests.py').read_text())
            class NoRestore(ast.NodeTransformer):
                def visit_For(self,node):
                    if isinstance(node.target,ast.Name) and node.target.id=='source' and 'payload.rglob' in ast.unparse(node.iter):
                        return ast.Pass()
                    return self.generic_visit(node)
            tree=ast.fix_missing_locations(NoRestore().visit(tree))
            diag=folder/'run_tests_without_second_restore.py';diag.write_text(ast.unparse(tree))
            modes=['original_restore_after_oracle','diagnostic_restore_once_before_oracle']
        else:
            modes=['diagnostic_conda_path_only']
        for mode in modes:
            logs=folder/mode;logs.mkdir();prefix='sao-diag-'+hashlib.sha256((iid+mode).encode()).hexdigest()[:12]
            prepare='cd /testbed && git checkout --quiet "$1" && test "$(git log -1 --format=%s)" = "Remove F2P Tests" && rm -rf /testbed/.git || exit 92; '
            mounts=[(task/'tests','/tests','ro'),(oracle,'/oracle.patch','ro'),(logs,'/logs','rw')]
            if overlap:
                prepare += 'cp -a /tests/payload/. /testbed/; git apply /oracle.patch || exit 93; '
                paths=' '.join(overlap)
                prepare += f'sha256sum {paths} > /logs/before.sha256; '
                if mode=='diagnostic_restore_once_before_oracle':
                    mounts.append((diag,'/diagnostic.py','ro'))
                    prepare += '/opt/miniconda3/envs/testbed/bin/python /diagnostic.py; rc=$?; '
                else: prepare += '/tests/test.sh; rc=$?; '
                prepare += f'sha256sum {paths} > /logs/after.sha256; '
            else:
                prepare += 'git apply /oracle.patch || exit 93; export PATH=/opt/miniconda3/envs/testbed/bin:$PATH; command -v pyfiglet; command -v cmake; /tests/test.sh; rc=$?; '
            prepare += 'chmod -R a+rwX /logs; exit $rc'
            rc,output=docker(prefix,row['base_image'],prepare,[iid],mounts)
            (logs/'docker.log').write_bytes(output)
            rf=logs/'verifier/reward.txt'
            result=dict(instance_id=iid,mode=mode,overlap=overlap,exit_code=rc,
                        reward=float(rf.read_text()) if rf.exists() else None,oracle_sha256=sha(oracle))
            if overlap:
                result['before']=(logs/'before.sha256').read_text()
                result['after']=(logs/'after.sha256').read_text()
            results.append(result);print(json.dumps(result),flush=True)
    dump(DEST/'summary.json',results)

if __name__=='__main__': main()
