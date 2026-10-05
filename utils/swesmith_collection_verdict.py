"""Narrow, evidence-backed candidate failures; unknown infrastructure stays invalid.

Policies are verifier-owned task metadata, not inferred from model text. No
reference implementation is loaded or applied while grading a candidate.
"""
import ast
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def checked_path(root, relative):
    p = root/relative
    current = p
    while current != root:
        if current.is_symlink():
            raise ValueError('Symlink in candidate evidence path')
        current = current.parent
    return p


def known_candidate_failure(config, testbed, report, code, output):
    if code not in (2, 4):
        return None
    policy = config.get('collection_failure_policy')
    if not policy:
        return None
    root = ET.parse(report).getroot()
    errors = list(root.iter('error'))
    if any(e.get('message') != 'collection failure' for e in errors):
        return None
    messages = [(e.text or '').strip() for e in errors]
    nodes = set(config['FAIL_TO_PASS'] + config['PASS_TO_PASS'])
    if policy == 'missing_local_release_module':
        if 'tests/test_release.py::test_happy_path' not in nodes:
            return None
        if checked_path(testbed, 'scripts/release.py').exists():
            return None
        if messages and all("tests/test_release.py" in m and m.splitlines()[-1] == "E   ModuleNotFoundError: No module named 'scripts'" for m in messages):
            return 'candidate_missing_required_local_module'
    elif policy == 'removed_stdlib_mapping_import':
        import collections
        from collections.abc import Mapping
        if hasattr(collections, 'Mapping') or Mapping is None:
            return None
        tree = ast.parse(checked_path(testbed, 'patsy/constraint.py').read_text())
        bad_import = any(isinstance(n, ast.ImportFrom) and n.module == 'collections' and any(x.name == 'Mapping' for x in n.names) for n in tree.body)
        if bad_import and messages and all('patsy/constraint.py:' in m and re.fullmatch(r"E   ImportError: cannot import name 'Mapping' from 'collections' \([^\n]+/collections/__init__\.py\)", m.splitlines()[-1]) for m in messages):
            return 'candidate_unsupported_stdlib_import'
    elif policy == 'displaced_closest_doctest':
        node = 'pyquery/pyquery.py::pyquery.pyquery.PyQuery.closest'
        if node not in nodes or errors or list(root.iter('testcase')):
            return None
        tree = ast.parse(checked_path(testbed, 'pyquery/pyquery.py').read_text())
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PyQuery']
        if len(classes) != 1:
            return None
        methods = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == 'closest']
        if len(methods) != 1:
            return None
        method = methods[0]
        # Trusted embedded-test validation runs first, so this string is intact.
        displaced = ast.get_docstring(method) is None and any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str) and '>>>' in n.value.value for n in method.body[1:])
        cli_errors = re.findall(r'^ERROR: (.+)$', output, flags=re.M)
        if displaced and code == 4 and cli_errors == ['not found: /testbed/' + node]:
            return 'candidate_displaced_required_doctest'
    return None
