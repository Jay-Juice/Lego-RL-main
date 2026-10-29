"""Read-only native-worker metadata audits for the disposable probe.

CPU fixture tests validate the assertions, never constitute eight-GPU evidence.
No parameter values, gradients or optimizer states are copied or modified here.
"""
import hashlib
import inspect
import json
import os
from pathlib import Path

CRITIC_PATTERNS = ['self_attn.', 'linear_attn.', 'visual.']


def check(value, message):
    if not value:
        raise RuntimeError('R6 rank audit: '+message)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def parameter_audit(module, optimizer, patterns, role):
    """Inspect named parameters and real optimizer membership without reading weights."""
    import torch
    check(role in ('actor', 'critic'), 'role')
    expected = CRITIC_PATTERNS if role == 'critic' else []
    check(list(patterns or []) == expected, 'freeze configuration changed')
    named = list(module.named_parameters())
    check(named and optimizer is not None, 'module or optimizer missing')
    optim_params = [p for group in optimizer.param_groups for p in group['params']]
    optim_ids = [id(p) for p in optim_params]
    check(len(optim_ids) == len(set(optim_ids)), 'duplicate optimizer parameters')
    optim_ids = set(optim_ids)
    train_ids = {id(p) for _, p in named if p.requires_grad}
    check(optim_ids == train_ids, 'optimizer must contain exactly trainable parameters')
    matches = {pattern: 0 for pattern in expected}
    rows = []
    for name, param in named:
        hits = [pattern for pattern in expected if pattern in name]
        for hit in hits:
            matches[hit] += 1
        check(bool(param.requires_grad) == (not hits), 'unexpected freeze: '+name)
        rows.append(dict(name=name, shape=list(param.shape), dtype=str(param.dtype),
                         trainable=bool(param.requires_grad), optimizer=id(param) in optim_ids))
    check(all(matches.values()), 'freeze pattern matched nothing')
    check(bool(train_ids), 'no trainable parameters')
    heads = []
    if role == 'critic':
        for name, submodule in module.named_modules():
            if name == 'score' or name.endswith('.score'):
                check(isinstance(submodule, torch.nn.Linear) and submodule.out_features == 1,
                      'critic must have native scalar Linear score head')
                heads.append(dict(name=name, in_features=submodule.in_features,
                                  out_features=submodule.out_features))
        check(len(heads) == 1, 'exactly one scalar score head required')
        check(any(r['name'].endswith('score.weight') and r['trainable'] and r['optimizer'] for r in rows),
              'score weight not trainable/in optimizer')
        check(not any('lm_head' in r['name'] for r in rows), 'critic has language model head')
    return dict(parameter_inventory_SHA=sha(rows), parameter_tensors=len(rows),
                trainable_tensors=len(train_ids), frozen_tensors=len(rows)-len(train_ids),
                optimizer_tensors=len(optim_ids), freeze_patterns=expected, pattern_matches=matches,
                scalar_heads=heads, optimizer_class=type(optimizer).__module__+'.'+type(optimizer).__qualname__)


def engine_audit(worker, role, stage):
    """Called on each real rank only after the native engine has initialized."""
    import torch
    check(torch.distributed.is_initialized(), 'distributed process group absent')
    engine = worker.engine
    check(engine.ulysses_sequence_parallel_size == 8 and engine.use_ulysses_sp, 'SP8 disabled')
    check(engine.ulysses_parallel_group is not None, 'SP process group absent')
    world = torch.distributed.get_world_size()
    sp = torch.distributed.get_world_size(engine.ulysses_parallel_group)
    dp = engine.get_data_parallel_size()
    check(world == 8 and sp == 8 and dp == 1, 'requires world8/SP8/DP1')
    mro = [cls.__module__+'.'+cls.__qualname__ for cls in type(engine.module).__mro__]
    source = None
    if role == 'critic':
        classes = [cls for cls in type(engine.module).__mro__ if cls.__name__ == 'Qwen3_5ForTokenClassification']
        check(len(classes) == 1, 'native Qwen3.5 token-classification class absent')
        path = Path(inspect.getfile(classes[0])).resolve()
        source = dict(path=str(path), SHA=hashlib.sha256(path.read_bytes()).hexdigest())
    result = parameter_audit(engine.module, engine.optimizer,
                             worker.engine_config.get('freeze_param_patterns'), role)
    result.update(role=role, stage=stage, pid=os.getpid(), rank=torch.distributed.get_rank(),
                  world_size=world, SP_size=sp, DP_size=dp, DP_rank=engine.get_data_parallel_rank(),
                  engine_class=type(engine).__module__+'.'+type(engine).__qualname__,
                  module_MRO=mro, native_head_source=source)
    return result


def validate_rank_rows(rows, role, stage):
    check(isinstance(rows, list) and len(rows) == 8, 'eight individual rank results required')
    check({r['rank'] for r in rows} == set(range(8)), 'rank coverage/duplicates')
    check(len({r['pid'] for r in rows}) == 8, 'eight worker processes required')
    for row in rows:
        check(row['role'] == role and row['stage'] == stage, 'wrong role/stage')
        check((row['world_size'], row['SP_size'], row['DP_size'], row['DP_rank']) == (8, 8, 1, 0), 'rank topology')
        check(row['freeze_patterns'] == (CRITIC_PATTERNS if role == 'critic' else []), 'rank freeze configuration')
        check(row['optimizer_tensors'] == row['trainable_tensors'] > 0, 'rank optimizer inventory')
        if role == 'critic':
            check(len(row['scalar_heads']) == 1 and row['scalar_heads'][0]['out_features'] == 1, 'rank head')
            check(row['native_head_source'] is not None and row['frozen_tensors'] > 0, 'rank native head/freeze witness')
    for field in ('parameter_inventory_SHA', 'engine_class', 'module_MRO', 'native_head_source'):
        check(len({sha(row[field]) for row in rows}) == 1, 'rank disagreement: '+field)
    return sorted(rows, key=lambda r: r['rank'])


def compare_stages(before, after):
    for role in ('actor', 'critic'):
        for old, new in zip(before[role], after[role], strict=True):
            for field in ('rank', 'pid', 'parameter_inventory_SHA', 'engine_class', 'module_MRO',
                          'native_head_source', 'SP_size', 'DP_size', 'freeze_patterns'):
                check(old[field] == new[field], 'native inventory changed during updates: '+field)
