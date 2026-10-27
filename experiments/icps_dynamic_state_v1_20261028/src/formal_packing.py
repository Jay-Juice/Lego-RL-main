"""Historical SAO packing phases, using native per-batch engineering overrides.

The native TrainingWorker honors max_token_len_per_gpu when supplied in data.
This changes packing only; no model, optimizer, scheduler or sample is modified.
Actor old-logprob/reference inference retain their native 14336 budget.
"""
import json
import os
from pathlib import Path


def budget(role, step):
    if not isinstance(step, int) or isinstance(step, bool) or not 1 <= step <= 97:
        raise ValueError(f'not a full97 training step: {step}')
    if role not in ('actor_train', 'critic_train', 'critic_infer'):
        raise ValueError(role)
    if role == 'critic_infer':
        return 32768  # actual native CriticConfig.ppo_infer field, not deprecated forward field
    if role == 'actor_train':
        return 14336 if step <= 20 else 16384
    return 20480 if step <= 20 else 45056


def record_phase(trainer):
    """Witness at loop entry, before rollout; never a pause or scheduler update."""
    step = trainer.global_steps
    assert trainer.total_training_steps == 97
    assert len(trainer.train_dataloader) == 97
    if step not in (1, 21):
        return
    info = dict(step=step, full_horizon=97,
                actor_train=budget('actor_train', step),
                critic_train=budget('critic_train', step),
                critic_infer=budget('critic_infer', step),
                actor_logprob=14336, ref_logprob=14336,
                transport='native TensorDict max_token_len_per_gpu override',
                optimizer_and_scheduler_untouched=True)
    p = Path(os.environ['ICPS_FORMAL_RUN_DIR']) / 'packing_phases.jsonl'
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(info) + '\n')
    print('[ICPS_FULL97_PACKING] ' + json.dumps(info), flush=True)
