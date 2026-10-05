import json
from pathlib import Path
import subprocess
import sys
from test_audit_safety import workspace_temp
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'utils'))
from swesmith_special_runners import TORNADO, adapt


class SpecialRunnersTest(unittest.TestCase):
    def test_native_body_errors_differ_from_setup_teardown(self):
        fixture = '''import sys,types,unittest
class Body(unittest.TestCase):
    def test_ok(self): pass
    def test_assert(self): self.assertEqual(1,2)
    def test_exception(self): raise ValueError('business failure')
class Setup(unittest.TestCase):
    def setUp(self): raise ImportError('missing dependency')
    def test_check(self): pass
class Teardown(unittest.TestCase):
    def tearDown(self): raise RuntimeError('cleanup failed')
    def test_check(self): pass
def main():
    suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
    result=unittest.TextTestRunner(resultclass=unittest.TextTestResult).run(suite)
    raise SystemExit(not result.wasSuccessful())
mod=types.ModuleType('tornado.test.runtests');mod.main=main
sys.modules['tornado.test.runtests']=mod
'''
        with workspace_temp() as temp:
            report=Path(temp)/'report.xml'
            names=['__main__.Body.test_ok','__main__.Body.test_assert','__main__.Body.test_exception','__main__.Setup.test_check','__main__.Teardown.test_check']
            result=subprocess.run([sys.executable,'-c',fixture+TORNADO,json.dumps(names),str(report)],capture_output=True)
            self.assertEqual(result.returncode,1,result.stderr)
            cases=list(ET.parse(report).getroot().iter('testcase'))
            self.assertEqual(len(cases),5)
            self.assertEqual(sum(c.find('failure') is not None for c in cases),2)
            self.assertEqual(sum(c.find('error') is not None for c in cases),2)

    def test_selected_nodes_preserved(self):
        nodes=['b.py::test_b','a.py::test_a','b.py::test_c']
        command,env=adapt({'instance_id':'jd__tenacity.x'},nodes,['python','-m','pytest',*nodes],{},'out')
        self.assertEqual(command[3:],['a.py::test_a','b.py::test_b','b.py::test_c'])
        self.assertEqual(set(command[3:]),set(nodes))
        command,env=adapt({'instance_id':'modin-project__modin.x'},nodes,['python','-n','2',*nodes],{},'out')
        self.assertEqual(command[2],'0');self.assertEqual(env['MODIN_CPUS'],'2')


if __name__=='__main__':unittest.main()
