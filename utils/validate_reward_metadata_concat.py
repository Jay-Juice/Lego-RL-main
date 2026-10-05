"""Exercise actual output metadata expressions with real verl batch concatenation."""
import ast
import itertools
from types import SimpleNamespace
from pathlib import Path

import numpy as np
from verl import DataProto


def main():
    source = Path('src/verl_patch/agent_loop/builtin_swe_agent_loop.py').read_text()
    expressions = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == 'reward_extra_info':
                    expressions.append(value)
    assert len(expressions) == 2
    normal, empty = expressions
    def evaluate(expr, metrics, reason):
        return eval(compile(ast.Expression(expr), '<actual reward metadata>', 'eval'),
                    {'metrics': metrics, 'base_metrics': metrics, 'reason': reason})
    rows = [evaluate(normal, {}, 'completed'),
            evaluate(empty, {'verifier_unresolved': 1}, 'verifier_unresolved'),
            evaluate(empty, {}, 'env_setup_failed')]
    assert all(set(row) == set(rows[0]) for row in rows)
    assert rows[1]['verifier_unresolved'] == 1 and rows[1]['environment_failure'] == 0
    assert rows[2]['environment_failure'] == 1
    for order in (rows, rows[::-1]):
        data = [DataProto.from_dict(non_tensors={key: np.array([value])
                for key, value in row.items()}) for row in order]
        combined = DataProto.concat(data)
        assert combined.non_tensor_batch['verifier_unresolved'].tolist() == [
            row['verifier_unresolved'] for row in order]
    # Reproduce the actual worker meta_info["metrics"] path as well as rewards.
    tree = ast.parse(source)
    namespace = {"self": SimpleNamespace(harnesses=["openhands_sdk"]),
                 "harness_selection": SimpleNamespace(definition=SimpleNamespace(name="openhands_sdk"))}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and
                t.id in ("_HARBOR_TIMING_KEYS", "_PROXY_METRIC_KEYS", "_TRIAL_STATUS_METRIC_KEYS")
                for t in node.targets):
            exec(compile(ast.Module(body=[node], type_ignores=[]), "<constants>", "exec"), namespace)
    def initialization(variable):
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for i, stmt in enumerate(fn.body):
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == variable:
                    block = [stmt]
                    for nxt in fn.body[i+1:]:
                        if not isinstance(nxt, ast.For):
                            break
                        block.append(nxt)
                    env = dict(namespace)
                    exec(compile(ast.Module(body=block, type_ignores=[]), "<actual initialization>", "exec"), env)
                    return env[variable]
        raise AssertionError(variable)
    normal_metrics = initialization("metrics")
    empty_metrics = initialization("base_metrics")
    # These standard fields are filled by the framework for normal outputs.
    for key in ("generate_sequences", "tool_calls", "num_preempted"):
        normal_metrics.setdefault(key, 0.0)
    # Negative control: the exact former missing-default shape must fail.
    old_normal = {k:v for k,v in normal_metrics.items() if k not in ("agent_timeout", "verifier_timeout")}
    try:
        DataProto.concat([DataProto(meta_info={"metrics": [old_normal]}),
                          DataProto(meta_info={"metrics": [dict(old_normal, agent_timeout=1.0)]})])
    except AssertionError as error:
        assert "agent_timeout" in str(error)
    else:
        raise AssertionError("old schema unexpectedly passed")
    variants = [normal_metrics, dict(normal_metrics, agent_timeout=1.0),
                dict(normal_metrics, verifier_timeout=1.0),
                dict(empty_metrics, verifier_unresolved=1.0), empty_metrics]
    assert all(set(v) == set(variants[0]) for v in variants)
    for order in itertools.permutations(variants):
        merged = DataProto.concat([DataProto(meta_info={"metrics": [v]}) for v in order])
        assert all(len(v) == len(order) for v in merged.meta_info["metrics"].values())
        for key in ("agent_timeout", "verifier_timeout", "verifier_unresolved"):
            assert merged.meta_info["metrics"][key] == [v[key] for v in order]
    # All literal metric writes must have a default (dynamic harness keys handled above).
    written = {n.slice.value for n in ast.walk(tree) if isinstance(n, ast.Subscript)
               and isinstance(n.ctx, ast.Store) and isinstance(n.value, ast.Name)
               and n.value.id == "metrics" and isinstance(n.slice, ast.Constant)
               and isinstance(n.slice.value, str)}
    assert written <= set(normal_metrics), written - set(normal_metrics)
    print('PASS: reward metadata and actual metrics initialization; all 120 permutations; literal metric keys covered')


if __name__ == '__main__':
    main()
