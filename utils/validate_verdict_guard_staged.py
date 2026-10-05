#!/usr/bin/env python3
"""Validate guarded real verl functions in memory, without changing the checkout."""
import ast
import sys
from pathlib import Path

import torch
from verl.trainer.ppo import core_algos
from apply_verdict_empty_batch_guard import transform


def main():
    root = Path('third_party/verl/verl/trainer/ppo')
    original = (root / 'core_algos.py').read_text()
    trainer = (root / 'ray_trainer.py').read_text()
    patched_core, patched_trainer = transform(original, trainer)
    assert transform(patched_core, patched_trainer) == (patched_core, patched_trainer)
    function = next(x for x in ast.parse(patched_core).body
                    if isinstance(x, ast.FunctionDef) and x.name == 'agg_loss')
    namespace = dict(vars(core_algos))
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<guarded agg_loss>', 'exec'), namespace)
    guarded = namespace['agg_loss']
    for mode in ('token-mean', 'seq-mean-token-sum', 'seq-mean-token-mean'):
        for mask in (torch.ones(2, 3), torch.tensor([[0., 0., 0.], [1., 1., 0.]])):
            values = torch.arange(6.).reshape(2, 3).requires_grad_()
            before = core_algos.agg_loss(values, mask, mode)
            after = guarded(values, mask, mode)
            assert torch.equal(before, after), mode
            assert torch.equal(torch.autograd.grad(before, values)[0],
                               torch.autograd.grad(after, values)[0]), mode
    # Execute the actual inserted trainer guard with a minimal DataProto-shaped object.
    guards = [n for n in ast.walk(ast.parse(patched_trainer)) if isinstance(n, ast.If)
              and 'All rollout responses are invalid' in ast.unparse(n)
              and ast.unparse(n.test) == "not batch.batch['response_mask'].any()"]
    assert len(guards) == 1
    code = compile(ast.Module(body=guards, type_ignores=[]), '<trainer guard>', 'exec')
    from types import SimpleNamespace
    exec(code, {'batch': SimpleNamespace(batch={'response_mask': torch.ones(2, 3)})})
    try:
        exec(code, {'batch': SimpleNamespace(batch={'response_mask': torch.zeros(2, 3)})})
    except RuntimeError as exc:
        assert 'refusing optimizer update' in str(exc)
    else:
        raise AssertionError('All-invalid batch must stop before optimizer update')
    core_algos.agg_loss = guarded
    import validate_verdict_training_cpu
    validate_verdict_training_cpu.main()
    print('PASS: real loss values/gradients unchanged; all-masked loss finite; all-invalid update refused')


if __name__ == '__main__':
    main()
