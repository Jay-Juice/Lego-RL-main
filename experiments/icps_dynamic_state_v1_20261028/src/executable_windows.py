"""Label-blind executable anchors and bounded syntactic name relations.

Pure current-source input; no filesystem, labels, rewards or future actions.
Name sharing is a heuristic, not a claim of semantic dataflow.
"""
import ast
import collections
import math
import re
from window_serializer import resolve, terms, query, sha


def line_signals(entity, lines, issue, flow=False):
    lo, hi = entity['start_line'], entity['end_line']
    node = entity.get('node')
    q, explicit = query(issue)
    excluded = set()
    if node:
        for n in ast.walk(node):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                first = n.body[0] if n.body else None
                header_end = first.lineno - 1 if first else n.lineno
                excluded.update(range(n.lineno, header_end + 1))
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                excluded.update(range(n.lineno, n.end_lineno + 1))
    executable = [i for i in range(lo, hi + 1)
                  if i not in excluded and lines[i-1].strip()
                  and not lines[i-1].lstrip().startswith('#')]
    df = collections.Counter(t for i in executable for t in terms(lines[i-1]))
    scores = {}
    for i in executable:
        ts = terms(lines[i-1])
        ids = {v.lower() for v in re.findall(r'[A-Za-z_]\w*', lines[i-1])}
        scores[i] = 3 * len(ids & explicit) + sum(1 / math.sqrt(df[t]) for t in ts & q)
    linked = set()
    if flow and node:
        seeds = [i for i in sorted(scores, key=lambda i: (-scores[i], i)) if scores[i] > 0][:3]
        names = collections.defaultdict(set)
        stores = collections.defaultdict(set)
        terminals = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id not in {'self', 'cls'}:
                names[n.lineno].add(n.id)
                if isinstance(n.ctx, ast.Store):
                    stores[n.lineno].add(n.id)
            if isinstance(n, (ast.Return, ast.Raise)):
                terminals.update(range(n.lineno, n.end_lineno + 1))
        for seed in seeds:
            for i in executable:
                if i < seed and stores[i] & names[seed]:
                    linked.add(i)
                if i in terminals and names[i] & names[seed]:
                    linked.add(i)
        for i in linked:
            scores[i] += 1
    return scores, excluded, linked


def proposals(candidates, files, issue, flow=False):
    out = []
    for rank, e in enumerate(resolve(candidates, files)):
        if not e['available']:
            continue
        lines = files[e['file']].splitlines(True)
        lo, hi = e['start_line'], e['end_line']
        scores, _, _ = line_signals(e, lines, issue, flow)
        positive = [i for i in scores if scores[i] > 0]
        anchors = sorted(positive, key=lambda i: (-scores[i], i))[:12]
        if not anchors:
            executable = sorted(scores)
            anchors = ([executable[0], executable[len(executable)//2]] if executable else [lo])
        seen = set()
        for anchor in anchors:
            for size in (7, 5, 3):
                a = max(lo, min(anchor - 2, hi - size + 1))
                b = min(hi, a + size - 1)
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                code = ''.join(lines[a-1:b])
                strength = scores.get(anchor, 0)
                out.append(dict(file=e['file'], qualified=e['qualified'], entity_id=e['entity_id'],
                    rank=rank, start=a, end=b, code=code, source_hash=sha(code),
                    syntax=e.get('syntax', 'valid'), partial=a != lo or b != hi,
                    low_confidence=strength == 0, score=strength +
                    sum(scores.get(i, 0) for i in range(a, b+1))/max(1, b-a+1)))
    return out
