"""CPU cache/model inventory and actual native TensorDict preparation checks."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1')
import json,pathlib
from gpu_common import *

def main():
    import torch
    torch.set_num_threads(1)
    receipt=json.loads((P/'CACHE_FULL_RECEIPT.json').read_text());assert receipt['passed']
    assert sha(P/'private_cache_full.pt')==receipt['cache_SHA']
    data=torch.load(P/'private_cache_full.pt',map_location='cpu',weights_only=False)
    c=config(data['config']);temperature=data['config']['actor_rollout_ref']['rollout']['temperature']
    for row in data['rows']:
        prepared={k:make_td(row,k,temperature) for k in ['true','neutral','wrong','history']}
        for k in ['neutral','wrong']:
            for field in ['response_mask','critic_value_gather_indices','critic_pi_mask']:
                assert torch.equal(prepared[k][field],prepared['true'][field]),field
            assert torch.equal(prepared[k]['input_ids'].offsets(),prepared['true']['input_ids'].offsets())
        for td in prepared.values():
            assert td['input_ids'].is_nested and td['input_ids'].values().numel()>0
            assert td['response_mask'].sum()>0
    checkpoints={}
    for step in [20,30,40]:
        root=CKPT/f'global_step_{step}';m=json.loads((root/'PI_COMPLETE.json').read_text())
        assert m['experiment']==EXP and m['global_step']==step and m['world_size']==8
        assert m['pi_format']=='icps_window_v11'
        sizes={}
        for rank in range(8):
            p=root/'critic'/f'model_world_size_8_rank_{rank}.pt'
            assert p.is_file() and not p.is_symlink() and p.stat().st_size>1000000
            sizes[p.name]=p.stat().st_size
            assert sizes[p.name]==m['files']['critic/'+p.name]
        checkpoints[str(step)]=dict(marker_SHA=sha(root/'PI_COMPLETE.json'),model_shard_sizes=sizes,marker=m)
    sources=[F/'runtime/privileged_critic_builder.py',F/'src/window_serializer.py',F/'core/issue_program_state.py',
             R/'src/verl_patch/agent_loop/vllm_chat_completion_proxy.py',R/'src/verl_patch/agent_loop/privileged_critic_builder.py',
             R/'third_party/verl/verl/workers/engine/veomni/transformer_impl.py',R/'third_party/verl/verl/workers/utils/padding.py',
             R/'third_party/verl/verl/trainer/ppo/core_algos.py']
    out=dict(passed=True,cache_SHA=receipt['cache_SHA'],samples=len(data['rows']),checkpoints=checkpoints,
             source_SHA={str(p):sha(p) for p in sources},GPU_runs=0,model_tensor_loads=0,
             load_contents=['model'],optimizer_steps=0,cache_scope=receipt['scope'])
    assert not torch.cuda.is_initialized()
    save(P/'PREFLIGHT_FULL.json',out)
    print(json.dumps(dict(passed=True,samples=len(data['rows']),checkpoints=[20,30,40],GPU_runs=0)))

if __name__=='__main__':main()

