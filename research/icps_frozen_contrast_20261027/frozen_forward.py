"""Native SP8 frozen Critic inference; separate process per checkpoint, no update."""
import os
os.environ.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1')
import argparse,datetime,json,pathlib,random,subprocess,time,traceback
from gpu_common import *

def main():
    import numpy as np,torch,torch.distributed as dist
    from verl.workers.utils.padding import no_padding_2_padding
    parser=argparse.ArgumentParser();parser.add_argument('--step',type=int,choices=[20,30,40],required=True);args=parser.parse_args()
    rank=int(os.environ['RANK']);dev=int(os.environ['LOCAL_RANK']);torch.set_num_threads(1)
    O=P/f'forward_step{args.step}';O.mkdir(exist_ok=True,mode=0o700)
    proof=json.loads((P/'PREFLIGHT_FULL.json').read_text());assert proof['passed'] and sha(P/'private_cache_full.pt')==proof['cache_SHA']
    for name,h in proof['source_SHA'].items():assert sha(name)==h,'Runtime source changed; no silent repair'
    root=CKPT/f'global_step_{args.step}';assert sha(root/'PI_COMPLETE.json')==proof['checkpoints'][str(args.step)]['marker_SHA']
    for name,size in proof['checkpoints'][str(args.step)]['model_shard_sizes'].items():assert (root/'critic'/name).stat().st_size==size
    torch.cuda.set_device(dev);dist.init_process_group('nccl',timeout=datetime.timedelta(minutes=20))
    assert dist.get_world_size()==8
    try:
        own=[None]*8;dist.all_gather_object(own,os.getpid())
        active=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).split()
        assert set(map(int,active))<=set(own),'Other GPU process present; abort own diagnostic'
        data=torch.load(P/'private_cache_full.pt',map_location='cpu',weights_only=False);c=config(data['config'])
        random.seed(42);np.random.seed(42);torch.manual_seed(42);torch.cuda.manual_seed_all(42)
        c.model.get_processor()
        from verl.workers.engine.veomni.transformer_impl import VeOmniEngineWithValueHead
        engine=VeOmniEngineWithValueHead(model_config=c.model,engine_config=c.engine,optimizer_config=c.optim,checkpoint_config=c.checkpoint)
        engine.initialize()
        assert engine.checkpoint_manager.should_load_model and not engine.checkpoint_manager.should_load_optimizer and not engine.checkpoint_manager.should_load_extra
        engine.load_checkpoint(str(root/'critic'),del_local_after_load=False)
        def fingerprint():
            hashes=[]
            for name,param in engine.module.named_parameters():
                local=param.to_local() if hasattr(param,'to_local') else param
                raw=local.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
                hashes.append((name,hashlib.sha256(raw).hexdigest()))
            return hashlib.sha256(json.dumps(hashes).encode()).hexdigest()
        before=fingerprint()
        save(O/f'loaded_rank{rank}.json',dict(checkpoint_step=args.step,rank=rank,model_loaded=True,optimizer_loaded=False,parameter_SHA=before,
                                           model_shard_SHA=sha(root/'critic'/f'model_world_size_8_rank_{rank}.pt')))
        engine.optimizer.step=engine.optimizer_step=engine.lr_scheduler_step=engine.train_batch=engine.save_checkpoint=forbidden
        engine.checkpoint_manager.save_checkpoint=forbidden
        # forward_backward_batch is also the native inference implementation;
        # reject backward explicitly while retaining the native forward path.
        real_forward=engine.forward_backward_batch
        def forward(data,loss_function,forward_only=False):
            assert forward_only and loss_function is None
            return real_forward(data,loss_function,forward_only=True)
        engine.forward_backward_batch=forward
        torch.Tensor.backward=forbidden
        temperature=data['config']['actor_rollout_ref']['rollout']['temperature'];outputs=[];started=time.monotonic()
        for i,row in enumerate(data['rows']):
            vals={}
            # Balanced order across rows; every condition has its own repeat floor.
            conditions=['true','neutral','wrong','history'];shift=i%4;conditions=conditions[shift:]+conditions[:shift]
            for condition in conditions:
                td=make_td(row,condition,temperature)
                for repeat in [0,1]:
                    with engine.eval_mode():
                        out=engine.infer_batch(td.clone(),loss_function=None)
                        v=no_padding_2_padding(out['model_output']['values'],td.to(dev)).float().cpu()[0]
                    assert torch.isfinite(v).all() and v.numel()==len(row['response_mask'])
                    vals[f'{condition}_{repeat}']=v
            if rank==0:
                outputs.append(dict(selection_key=row['selection_key'],family=row['family'],reward=row['reward'],
                                    response_mask=torch.tensor(row['response_mask']),values=vals))
                with (O/f'row_{i:03d}.pt').open('xb') as f:torch.save(outputs[-1],f)
                with (O/'progress.jsonl').open('a') as f:f.write(json.dumps(dict(completed=i+1,total=len(data['rows']),elapsed_seconds=time.monotonic()-started))+'\n')
        after=fingerprint();assert before==after,'Frozen parameters changed'
        assert len(engine.optimizer.state)==0,'Unexpected optimizer state'
        save(O/f'complete_rank{rank}.json',dict(passed=True,step=args.step,rank=rank,rows=len(data['rows']),parameters_unchanged=True,
                                              optimizer_steps=0,backward_calls=0,wall_seconds=time.monotonic()-started))
    except BaseException:
        save(O/f'failure_rank{rank}.json',dict(traceback=traceback.format_exc(),optimizer_steps=0));raise
    finally:
        if dist.is_initialized():dist.destroy_process_group()

if __name__=='__main__':main()
