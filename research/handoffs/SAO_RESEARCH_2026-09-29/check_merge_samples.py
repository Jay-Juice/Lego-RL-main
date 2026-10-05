"""Read-only CPU source-shard/HF sampled numerical comparison (not full parity)."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import contextlib
import json
from pathlib import Path
import torch
from safetensors import safe_open

torch.set_num_threads(2)
root = Path('/media/ubuntu/D1/zsj/Lego-RL-main')
src = root/'checkpoints/sao-qwen35-9b-swesmith/sao-qwen35-9b-swesmith-64k-full-sp8-tokenpack-v1/global_step_80/actor'
dst = root/'merged_models/sao-qwen35-9b-swesmith-sp8-step80-direct-20260929'
index = json.loads((dst/'model.safetensors.index.json').read_text())['weight_map']
bad, checked, count, dtypes = [], set(), 0, set()
with contextlib.ExitStack() as stack:
    handles = {f:stack.enter_context(safe_open(str(dst/f),framework='pt')) for f in set(index.values())}
    for rank in range(8):
        state = torch.load(src/f'model_world_size_8_rank_{rank}.pt',map_location='cpu',weights_only=False,mmap=True)
        for key,dt in state.items():
            local = dt.to_local() if hasattr(dt,'to_local') else dt
            shape = tuple(dt.shape)
            hp = handles[index[key]].get_tensor(key)
            n = min(9,local.numel())
            positions = torch.tensor([i*(local.numel()-1)//max(1,n-1) for i in range(n)],dtype=torch.long)
            coords = list(torch.unravel_index(positions, local.shape))
            if hasattr(dt,'placements'):
                assert len(dt.placements)==1
                place = dt.placements[0]
                if place.is_shard():
                    dim = place.dim
                    chunk = (shape[dim]+7)//8
                    coords[dim] = coords[dim] + rank*chunk
                else:
                    assert place.is_replicate(),str(place)
            actual = hp[tuple(coords)]
            expected = local.reshape(-1)[positions].to(hp.dtype)
            if not torch.equal(actual,expected):bad.append({'rank':rank,'key':key,'max_abs_diff':float((actual.float()-expected.float()).abs().max())})
            count += positions.numel();checked.add(key);dtypes.add((str(local.dtype),str(hp.dtype)))
        del state
print('AUDIT_JSON='+json.dumps({'step':80,'trained_keys':len(checked),'ranks':8,'sampled_values':count,
 'mismatches':bad,'dtype_conversions':sorted(dtypes),'source':str(src),'merged':str(dst),
 'limitation':'9 spread values per tensor per rank; not full-tensor or forward-logit parity; MTP backfill excluded'}))
