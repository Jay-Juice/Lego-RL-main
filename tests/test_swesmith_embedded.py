import sys
import unittest
from pathlib import Path
from test_audit_safety import ROOT, workspace_temp
sys.path.insert(0,str(ROOT/'utils'))
from swesmith_embedded import normalize_tests, embedded_tests, production, restore_mixed_tests


class EmbeddedTests(unittest.TestCase):
    def test_normalize_only_tests(self):
        bug = 'def f():\n    return 0\ndef test_f():\n    assert f() == 0\n'
        ref = bug.replace('return 0','return 1').replace('f() == 0','f() == 1')
        fixed,names = normalize_tests(bug,ref)
        self.assertEqual(names,['test_f'])
        self.assertEqual(production(fixed),production(bug))
        self.assertEqual(embedded_tests(fixed),embedded_tests(ref))
        self.assertIn('return 0',fixed)

    def test_does_not_overwrite_oracle_and_rejects_test_edit(self):
        with workspace_temp() as folder:
            root=Path(folder); bed=root/'bed'; tests=root/'tests'
            (tests/'payload/pkg').mkdir(parents=True); (bed/'pkg').mkdir(parents=True)
            code='def f():\n    """>>> f()\n    1\n    """\n    return 0\n'
            (tests/'payload/pkg/core.py').write_text(code)
            target=bed/'pkg/core.py'; target.write_text(code.replace('return 0','return 1'))
            config={'FAIL_TO_PASS':['pkg/core.py::pkg.core.f'],'PASS_TO_PASS':[]}
            before=target.read_bytes(); restore_mixed_tests(config,bed,tests)
            self.assertEqual(before,target.read_bytes())
            target.write_text(code.replace('>>> f()','>>> 1'))
            with self.assertRaises(ValueError):restore_mixed_tests(config,bed,tests)

    def test_document_restored(self):
        with workspace_temp() as folder:
            root=Path(folder); bed=root/'bed'; tests=root/'tests'
            bed.mkdir(); (tests/'payload').mkdir(parents=True)
            (tests/'payload/README.rst').write_text('>>> 1 + 1\n2\n')
            (bed/'README.rst').write_text('tampered')
            restore_mixed_tests({'FAIL_TO_PASS':['README.rst::README.rst'],'PASS_TO_PASS':[]},bed,tests)
            self.assertIn('>>>',(bed/'README.rst').read_text())

    def test_reject_unproven_doctest_normalization(self):
        with self.assertRaises(ValueError):normalize_tests('""">>> 1\n0\n"""','""">>> 1\n1\n"""')

    def test_duplicate_tests_rejected(self):
        with self.assertRaises(ValueError):embedded_tests('def test_x(): pass\ndef test_x(): pass\n')


if __name__=='__main__':unittest.main()
