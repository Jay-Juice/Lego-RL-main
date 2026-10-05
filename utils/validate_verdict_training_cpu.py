#!/usr/bin/env python3
"""Exercise deployed verl filtering/losses and checkpoint sampler restoration on CPU."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from omegaconf import OmegaConf
from torchdata.stateful_dataloader import StatefulDataLoader
from verl import DataProto
from verl.trainer.main_ppo import create_rl_sampler
from verl.trainer.ppo.trajectory_filter import apply_trajectory_filter, zero_filtered_advantages
from verl.trainer.ppo.core_algos import compute_value_loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-index', required=True)
    parser.add_argument('--new-index', required=True)
    parser.add_argument('--data-state', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    checks = {}
    for all_invalid in (False, True):
        mask = torch.tensor([[0., 0.], [0., 0.] if all_invalid else [1., 1.]])
        batch = DataProto.from_dict(tensors={
            'token_level_rewards': torch.ones(2, 2), 'response_mask': mask,
            'advantages': torch.ones(2, 2), 'returns': torch.ones(2, 2)},
            non_tensors={'termination_reason': np.array(['env_setup_failed',
                'env_setup_failed' if all_invalid else 'agent_completed'], dtype=object),
                'uid': np.array(['a', 'b'], dtype=object)})
        batch, metrics = apply_trajectory_filter(batch, OmegaConf.create({'enable': True}))
        zero_filtered_advantages(batch)
        assert not batch.batch['advantages'][0].any()
        assert not batch.batch['returns'][0].any()
        predictions = torch.full((2, 2), 0.3, requires_grad=True)
        loss, clip = compute_value_loss(predictions, batch.batch['returns'],
                                       torch.zeros(2, 2), mask, 0.2)
        assert torch.isfinite(loss) and torch.isfinite(clip)
        loss.backward()
        assert not predictions.grad[0].any()
        if all_invalid:
            assert loss.item() == 0 and not predictions.grad.any()
        checks[str(all_invalid)] = {'critic_loss': loss.item(), 'metrics': metrics}
    old, new = pd.read_parquet(args.old_index), pd.read_parquet(args.new_index)
    old_ids = [x['instance_id'] for x in old.extra_info]
    new_ids = [x['instance_id'] for x in new.extra_info]
    assert old_ids == new_ids and len(new_ids) == 6242
    state = torch.load(args.data_state, map_location='cpu', weights_only=False)
    batches = []
    for ids in (old_ids, new_ids):
        config = OmegaConf.create({'shuffle': True, 'seed': 1})
        sampler = create_rl_sampler(config, ids)
        loader = StatefulDataLoader(ids, batch_size=16, num_workers=8,
                                    drop_last=True, sampler=sampler)
        loader.load_state_dict(state)
        batches.append(next(iter(loader)))
    assert batches[0] == batches[1]
    for x in new.extra_info:
        assert 'verdict_v2_20260928' in x['harbor_task_path']
    checks['resume'] = {'same_next_16_ids': True, 'next_ids': list(batches[1]),
                        'checkpoint_snapshot_step': state['_snapshot']['_snapshot_step']}
    with Path(args.output).open('x') as f:
        json.dump(checks, f, indent=2)
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
