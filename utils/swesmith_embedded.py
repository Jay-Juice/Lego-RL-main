"""Mixed source/test support, ported from our Agent Lightning adapter.

Prepare buggy implementation once, normalize only top-level test definitions
from the pre-injection reference, and verify embedded tests without restoring
the implementation during grading. No model or algorithm changes.
"""
import ast
import shutil
from pathlib import Path, PurePosixPath


def is_test(node):
    return (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_')) or (
        isinstance(node, ast.ClassDef) and node.name.startswith('Test'))


def embedded_tests(source):
    tests = {}
    def visit(node, scope):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope = (*scope, node.name)
            if is_test(node):
                key = 'test:' + '.'.join(scope)
                if key in tests:
                    raise ValueError('Duplicate embedded test: ' + key)
                tests[key] = ast.dump(node)
                return
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            doc = node.value.value
            if isinstance(doc, str) and '>>>' in doc:
                tests.setdefault('doctest:' + '.'.join(scope), []).append(doc)
        for child in ast.iter_child_nodes(node):
            visit(child, scope)
    visit(ast.parse(source), ())
    return tests


def production(source):
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if not is_test(node)]
    return ast.dump(tree)


def normalize_tests(buggy, trusted):
    """Preserve implementation bytes; reject changes we cannot safely separate."""
    old_tree, good_tree = ast.parse(buggy), ast.parse(trusted)
    old = {node.name: node for node in old_tree.body if is_test(node)}
    good = {node.name: node for node in good_tree.body if is_test(node)}
    if old.keys() != good.keys() or len(old) != sum(is_test(n) for n in old_tree.body):
        raise ValueError('Changed or ambiguous embedded test inventory')
    if len(good) != sum(is_test(n) for n in good_tree.body):
        raise ValueError('Ambiguous reference tests')
    lines, ref = buggy.splitlines(keepends=True), trusted.splitlines(keepends=True)
    changes = []
    for name, node in old.items():
        replacement = good[name]
        if ast.dump(node) == ast.dump(replacement):
            continue
        start = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
        refstart = min([replacement.lineno] + [d.lineno for d in replacement.decorator_list]) - 1
        changes.append((start, node.end_lineno, ref[refstart:replacement.end_lineno], name))
    for start, end, replacement, _ in sorted(changes, reverse=True):
        lines[start:end] = replacement
    repaired = ''.join(lines)
    if embedded_tests(repaired) != embedded_tests(trusted):
        raise ValueError('Unsupported nested test or doctest mutation')
    if production(repaired) != production(buggy):
        raise ValueError('Normalization changed implementation')
    return repaired, [x[3] for x in changes]


def dedicated(path):
    p = PurePosixPath(path)
    return any(x.lower() in {'test','tests'} for x in p.parts[:-1]) or p.name.lower().startswith('test_') or p.name.lower().endswith('_test.py') or p.name.lower() in {'tests.py','test.py','conftest.py'}


def restore_mixed_tests(config, testbed, tests):
    expected = {n.split('::',1)[0] for n in config['FAIL_TO_PASS'] + config['PASS_TO_PASS']}
    payload = tests/'payload'
    plan = []
    for path in expected:
        p = PurePosixPath(path)
        if p.is_absolute() or '..' in p.parts or '\\' in path:
            raise ValueError('Unsafe path')
        src, dst = payload/path, testbed/path
        for f, root in [(src,payload),(dst,testbed)]:
            current = f
            while current != root:
                if current.is_symlink():
                    raise ValueError('Symlink in test path')
                current = current.parent
        if not src.is_file():
            raise ValueError('Missing trusted test payload')
        if dedicated(path) or p.suffix.lower() in {'.rst','.md','.txt'}:
            plan.append((src,dst))
        elif p.suffix == '.py':
            trusted = embedded_tests(src.read_text())
            if not trusted or not dst.is_file() or embedded_tests(dst.read_text()) != trusted:
                raise ValueError('Embedded tests changed or missing: ' + path)
            # Critical: never copy this file over the candidate implementation.
        else:
            raise ValueError('Unsupported mixed test file: ' + path)
    actual = set()
    for f in payload.rglob('*'):
        if f.is_symlink():
            raise ValueError('Symlink in payload')
        if f.is_file():
            actual.add(f.relative_to(payload).as_posix())
    if actual != expected:
        raise ValueError('Unexpected or missing payload')
    for src,dst in plan:
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
