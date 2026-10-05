import json
from pathlib import Path
import sys
import unittest
from xml.sax.saxutils import escape
from test_audit_safety import ROOT, workspace_temp
sys.path.insert(0, str(ROOT/'utils'))
from swesmith_collection_verdict import known_candidate_failure


class CollectionVerdictTests(unittest.TestCase):
    def check(self, policy, source, errors, output='', code=4, expected=None):
        with workspace_temp() as folder:
            root=Path(folder); bed=root/'bed';bed.mkdir()
            for path,text in source.items():
                p=bed/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            report=root/'report.xml'
            report.write_text('<testsuites><testsuite>'+''.join('<testcase><error message="collection failure">'+escape(x)+'</error></testcase>' for x in errors)+'</testsuite></testsuites>')
            config={'collection_failure_policy':policy,'FAIL_TO_PASS':['tests/test_release.py::test_happy_path','pyquery/pyquery.py::pyquery.pyquery.PyQuery.closest'],'PASS_TO_PASS':[]}
            result=known_candidate_failure(config,bed,report,code,output)
            self.assertEqual(result,expected)

    def test_missing_business_module(self):
        self.check('missing_local_release_module',{},["tests/test_release.py:14\nE   ModuleNotFoundError: No module named 'scripts'"],expected='candidate_missing_required_local_module')

    def test_unrelated_dependency_and_mixed_errors_not_zero(self):
        known="tests/test_release.py:14\nE   ModuleNotFoundError: No module named 'scripts'"
        other="tests/test_release.py:14\nE   ModuleNotFoundError: No module named 'numpy'"
        for errors in [[other],[known,other]]:self.check('missing_local_release_module',{},errors)

    def test_fixed_module_not_classified_from_stale_log(self):
        self.check('missing_local_release_module',{'scripts/release.py':'pass'},["tests/test_release.py:14\nE   ModuleNotFoundError: No module named 'scripts'"])

    def test_mapping_checks_both_source_and_error(self):
        msg="patsy/constraint.py:12\nE   ImportError: cannot import name 'Mapping' from 'collections' (/opt/lib/collections/__init__.py)"
        self.check('removed_stdlib_mapping_import',{'patsy/constraint.py':'from collections import Mapping'},[msg],expected='candidate_unsupported_stdlib_import')
        self.check('removed_stdlib_mapping_import',{'patsy/constraint.py':'from collections.abc import Mapping'},[msg])

    def test_displaced_docstring_not_all_cli_errors(self):
        source={'pyquery/pyquery.py':'class PyQuery:\n def closest(self):\n  return result\n  """>>> 1\n  1\n  """\n'}
        msg='ERROR: not found: /testbed/pyquery/pyquery.py::pyquery.pyquery.PyQuery.closest'
        self.check('displaced_closest_doctest',source,[],msg,expected='candidate_displaced_required_doctest')
        self.check('displaced_closest_doctest',source,[],msg+'\nERROR: unrecognized arguments: --missing-plugin')
        self.check('displaced_closest_doctest',source,[],msg,code=3)


if __name__=='__main__':unittest.main()
