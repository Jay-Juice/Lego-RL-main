"""Shared frozen-forward configuration. No training/rollout code is invoked."""
import copy,hashlib,json,pathlib,sys
from inventory import B,R,F,P
sys.path[:0]=[str(R/'src'),str(R/'third_party/verl'),str(R/'third_party/harbor/src')]
EXP='sao-qwen35-9b-b64-icps-v11-192-full97-r2-20261024'
CKPT=F/'checkpoints/sao-qwen35-9b-swesmith'/EXP

def sha(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for data in iter(lambda:f.read(4*1024**2),b''):h.update(data)
    return h.hexdigest()
def save(p,x):
    with pathlib.Path(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def config(raw):
    from verl.utils.config import omega_conf_to_dataclass
    c=copy.deepcopy(raw['critic']);c['ppo_mini_batch_size']=1
    c['checkpoint']['load_contents']=['model']
    c['optim']['total_training_steps']=97
    c=omega_conf_to_dataclass(c)
    c.engine.infer_max_token_len_per_gpu=c.ppo_infer_max_token_len_per_gpu
    c.engine.max_token_len_per_gpu=c.ppo_max_token_len_per_gpu
    c.engine.use_remove_padding=c.model.use_remove_padding
    c.engine.use_fused_kernels=c.model.use_fused_kernels
    c.model.model_type='value_model'
    assert c.engine.ulysses_parallel_size==8
    assert list(c.engine.freeze_param_patterns)==['self_attn.','linear_attn.','visual.']
    assert c.checkpoint.load_contents==['model']
    return c
def make_td(row,condition,temperature):
    import torch
    from tensordict import TensorDict
    from verl.utils import tensordict_utils as tu
    from verl.workers.utils.padding import left_right_2_no_padding
    view=row['views'][condition];ids=view['input_ids'];plen=row['prompt_len'];actor=row['actor_ids']
    td=TensorDict(dict(input_ids=torch.tensor([ids]),attention_mask=torch.ones((1,len(ids)),dtype=torch.long),
                       position_ids=torch.arange(len(ids))[None,:],prompts=torch.tensor([actor[:plen]]),responses=torch.tensor([actor[plen:]]),
                       response_mask=torch.tensor([row['response_mask']],dtype=torch.long),
                       critic_value_gather_indices=torch.tensor([view['gather']]),critic_pi_mask=torch.tensor([view['pi_mask']])),batch_size=[1])
    td=left_right_2_no_padding(td)
    tu.assign_non_tensor(td,temperature=float(temperature),compute_loss=False,use_remove_padding=True,use_dynamic_bsz=True,
                         max_token_len_per_gpu=32768,micro_batch_size_per_gpu=1,use_fused_kernels=False,global_batch_size=1,sp_size=8,dp_size=1)
    return td
def forbidden(*a,**k):raise RuntimeError('Frozen diagnostic forbids optimizer/backward/save/generation')

