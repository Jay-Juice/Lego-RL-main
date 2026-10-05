"""Regression checks for source restoration, CLI environment and verdict reports."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path, PurePosixPath
from unittest.mock import patch
import types
import unittest
from test_audit_safety import ROOT, workspace_temp


def verifier():
    tree = ast.parse((ROOT/'utils/prepare_swesmith_harbor.py').read_text(encoding='utf-8'))
    code = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(getattr(t, 'id', '') == 'RUN_TESTS' for t in n.targets))
    ns = {'__name__': 'audit'}
    exec(compile(code, '<verifier>', 'exec'), ns)
    return ns


class BoundaryTests(unittest.TestCase):
    def test_generator_and_runtime_policy_match(self):
        ns = verifier()
        tree = ast.parse((ROOT/'utils/prepare_swesmith_harbor.py').read_text(encoding='utf-8'))
        f = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name=='is_dedicated_test_path')
        gen = {'PurePosixPath': PurePosixPath}
        exec(compile(ast.Module(body=[f],type_ignores=[]), '<policy>', 'exec'),gen)
        for name, expected in [('tests/test_cli.py',True),('test/unit/a.py',True),
                               ('test_x.py',True),('patsy/test_highlevel.py',True),
                               ('parso/tree.py',False),('patsy/infix_parser.py',False),
                               ('latest_module.py',False),('../tests/test_x.py',False),
                               ('/tests/test_x.py',False),('tests\\test_x.py',False)]:
            self.assertEqual(ns['is_dedicated_test_path'](name),expected,name)
            self.assertEqual(gen['is_dedicated_test_path'](name),expected,name)

    def fixture(self, root, ns):
        for name in ['testbed','tests/payload','logs/verifier']:
            (root/name).mkdir(parents=True,exist_ok=True)
        ns.update(TESTBED=root/'testbed',TESTS=root/'tests',LOGS=root/'logs/verifier')

    def test_embedded_tests_rejected_before_any_write(self):
        ns=verifier()
        with workspace_temp() as tmp:
            r=Path(tmp);self.fixture(r,ns)
            for where,text in [('testbed/parso/tree.py','MODEL_FIXED'),('tests/payload/parso/tree.py','ORIGINAL_BUG')]:
                p=r/where;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            config={'FAIL_TO_PASS':['parso/tree.py::dump'],'PASS_TO_PASS':[]}
            with self.assertRaisesRegex(RuntimeError,'Unsafe test restoration'):
                ns['restore_dedicated_tests'](config)
            self.assertEqual((r/'testbed/parso/tree.py').read_text(),'MODEL_FIXED')

    def test_test_tampering_reset_but_source_retained(self):
        ns=verifier()
        with workspace_temp() as tmp:
            r=Path(tmp);self.fixture(r,ns)
            (r/'testbed/module.py').write_text('MODEL_FIXED')
            (r/'testbed/test_x.py').write_text('assert True')
            (r/'tests/payload/test_x.py').write_text('TRUSTED_ASSERTIONS')
            ns['restore_dedicated_tests']({'FAIL_TO_PASS':['test_x.py::test_x'],'PASS_TO_PASS':[]})
            self.assertEqual((r/'testbed/test_x.py').read_text(),'TRUSTED_ASSERTIONS')
            self.assertEqual((r/'testbed/module.py').read_text(),'MODEL_FIXED')

    def test_unexpected_payload_rejected(self):
        ns=verifier()
        with workspace_temp() as tmp:
            r=Path(tmp);self.fixture(r,ns)
            (r/'tests/payload/module.py').write_text('BUG')
            with self.assertRaisesRegex(RuntimeError,'Unexpected'):
                ns['restore_dedicated_tests']({'FAIL_TO_PASS':['test_x.py::test_x'],'PASS_TO_PASS':[]})
            self.assertFalse((r/'testbed/module.py').exists())

    def test_symlink_cannot_redirect_test_restore_to_source(self):
        ns=verifier()
        with workspace_temp() as tmp:
            r=Path(tmp);self.fixture(r,ns)
            (r/'testbed/module.py').write_text('MODEL_FIXED')
            (r/'tests/payload/test_x.py').write_text('TRUSTED')
            try:
                (r/'testbed/test_x.py').symlink_to(r/'testbed/module.py')
            except OSError:
                self.skipTest('Symlink creation unavailable on this host')
            with self.assertRaisesRegex(RuntimeError,'Symlink'):
                ns['restore_dedicated_tests']({'FAIL_TO_PASS':['test_x.py::test_x'],'PASS_TO_PASS':[]})
            self.assertEqual((r/'testbed/module.py').read_text(),'MODEL_FIXED')

    def test_junit_setup_error_and_skip_are_not_valid_failures(self):
        ns=verifier()
        with workspace_temp() as tmp:
            p=Path(tmp)/'report.xml'
            for body,exitcode,expected in [('<testcase/>',0,1),
                    ('<testcase><failure/></testcase>',1,0),
                    ('<testcase><error/></testcase>',1,None),
                    ('<testcase><skipped/></testcase>',0,None),
                    ('<testcase><failure/></testcase><testcase><error/></testcase>',1,None),
                    ('',0,None)]:
                p.write_text('<testsuites><testsuite>'+body+'</testsuite></testsuites>')
                if expected is None:
                    with self.assertRaises(RuntimeError): ns['junit_verdict'](p,exitcode)
                else:self.assertEqual(ns['junit_verdict'](p,exitcode)[0],expected)

    def test_cli_path_and_missing_report_remove_stale_reward(self):
        ns=verifier()
        with workspace_temp() as tmp:
            r=Path(tmp);self.fixture(r,ns)
            (r/'tests/payload/test_x.py').write_text('def test_x(): pass')
            (r/'tests/config.json').write_text(json.dumps({'FAIL_TO_PASS':['test_x.py::test_x'],'PASS_TO_PASS':[]}))
            reward=r/'logs/verifier/reward.txt';reward.write_text('1')
            calls=[]
            def invoke(*args,**kwargs):
                calls.append(kwargs)
                return types.SimpleNamespace(returncode=0,stdout='missing report')
            with patch.object(ns['subprocess'],'run',side_effect=invoke),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ns['main'](),2)
            self.assertFalse(reward.exists())
            self.assertEqual(len(calls),1)
            expected = str(Path('/opt/miniconda3/envs/testbed/bin/python').parent)+os.pathsep
            self.assertTrue(calls[0]['env']['PATH'].startswith(expected))


if __name__=='__main__': unittest.main()
