"""Real TensorDict/native iterator/audit API regression, CPU only."""
import json,os,tempfile
from pathlib import Path
import torch
from tensordict import TensorDict
from verl.utils import tensordict_utils as tu
from verl.workers.engine import utils
from formal_packing import budget

F=Path(__file__).resolve().parents[1]

def main():
    assert not torch.cuda.is_initialized()
    # Demonstrate that the previous call form was invalid in this deployed API.
    data=TensorDict({'loss_mask':torch.ones(2,3),'critic_value_gather_indices':torch.zeros(2,3,dtype=torch.long)},batch_size=[2])
    tu.assign_non_tensor(data,max_token_len_per_gpu=20480)
    try:tu.get_non_tensor_data(data,key='max_token_len_per_gpu')
    except TypeError:previous_bug_reproduced=True
    else:raise AssertionError('unexpected deployed API signature')
    original=utils._v11_original_prepare_micro_batches
    saved=os.environ.get('ICPS_V11_MICROBATCH_AUDIT')
    tests=[]
    try:
        with tempfile.TemporaryDirectory(dir=F/'preflight') as temp:
            log=Path(temp)/'actual_api.jsonl';os.environ['ICPS_V11_MICROBATCH_AUDIT']=str(log)
            for role in ['actor_train','critic_train','critic_infer']:
                for step in [1,20,21,97]:
                    target=budget(role,step);tu.assign_non_tensor(data,max_token_len_per_gpu=target)
                    before={key:val.clone() for key,val in data.items() if isinstance(val,torch.Tensor)}
                    output=([data],None)
                    utils._v11_original_prepare_micro_batches=lambda *a,**k:output
                    assert utils.prepare_micro_batches(data=data) is output
                    witness=json.loads(log.read_text().splitlines()[-1]);assert witness['max_token_len_per_gpu']==target
                    assert all(torch.equal(data[key],val) for key,val in before.items())
                    batches=list(tu.make_iterator(data,mini_batch_size=2,epochs=2,seed=42,dataloader_kwargs={'shuffle':True}))
                    assert len(batches)==2
                    assert all(tu.get_non_tensor_data(b,key='max_token_len_per_gpu',default=None)==target for b in batches)
                    tests.append(dict(role=role,step=step,budget=target,exact_result_object=True,tensors_unchanged=True,native_iterator_retained_override=True))
    finally:
        utils._v11_original_prepare_micro_batches=original
        if saved is None:os.environ.pop('ICPS_V11_MICROBATCH_AUDIT',None)
        else:os.environ['ICPS_V11_MICROBATCH_AUDIT']=saved
    assert not torch.cuda.is_initialized()
    report=dict(passed=True,previous_bug_reproduced=previous_bug_reproduced,real_native_API=True,real_TensorDict=True,actual_audit_wrapper=True,
        scope='native packer mocked to check wrapper result identity; real native TensorDict iterator and helper called',GPU_compute=False,cases=tests)
    with (F/'preflight/REAL_ENGINE_AUDIT_API_PROBE.json').open('x') as h:json.dump(report,h,indent=2)
    print(json.dumps(dict(passed=True,real_API_cases=len(tests),GPU_compute=False)))

if __name__=='__main__':main()
