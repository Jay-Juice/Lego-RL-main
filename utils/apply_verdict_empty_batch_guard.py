#!/usr/bin/env python3
"""Apply narrowly checked guards to the project-owned vendored verl checkout."""
import argparse
import hashlib
import json
from pathlib import Path


def transform(core, trainer):
    marker = '# LEGO_VERDICT_V2_EMPTY_LOSS_GUARD'
    if marker not in core:
        anchor = '    if loss_agg_mode == "token-mean":\n'
        start = core.index('def agg_loss(')
        pos = core.index(anchor, start)
        guard = (
            '    ' + marker + '\n'
            '    # A local microbatch may contain only masked rows; retain a zero-gradient graph.\n'
            '    if not torch.any(loss_mask):\n'
            '        return (loss_mat * loss_mask).sum()\n'
        )
        core = core[:pos] + guard + core[pos:]
    marker = '# LEGO_VERDICT_V2_ALL_INVALID_BATCH_GUARD'
    if marker not in trainer:
        anchor = '                        metrics.update(traj_filter_metrics)\n'
        if trainer.count(anchor) != 1:
            raise ValueError('Unexpected trainer filter call structure')
        guard = (
            '                        ' + marker + '\n'
            '                        # Fail closed before any Actor/Critic optimizer update.\n'
            '                        if not batch.batch["response_mask"].any():\n'
            '                            raise RuntimeError("All rollout responses are invalid; refusing optimizer update")\n'
        )
        trainer = trainer.replace(anchor, anchor + guard)
    compile(core, 'core_algos.py', 'exec')
    compile(trainer, 'ray_trainer.py', 'exec')
    return core, trainer


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--verl-root', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    files = [args.verl_root / 'verl/trainer/ppo' / x for x in ('core_algos.py', 'ray_trainer.py')]
    old = [f.read_text() for f in files]
    new = transform(*old)
    for f, before, after in zip(files, old, new):
        print(json.dumps({'file': str(f), 'changed': before != after,
              'before': hashlib.sha256(before.encode()).hexdigest(),
              'after': hashlib.sha256(after.encode()).hexdigest()}))
        if args.apply and before != after:
            backup = f.with_suffix(f.suffix + '.pre_verdict_v2')
            if backup.exists():
                raise FileExistsError(backup)
            backup.write_text(before)
            f.write_text(after)


if __name__ == '__main__':
    main()
