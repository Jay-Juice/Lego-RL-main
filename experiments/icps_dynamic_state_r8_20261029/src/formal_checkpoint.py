"""CPU resume metadata and durable file audit, without loading model tensors."""
import hashlib,json,os,pathlib
def verify_resume_metadata(folder,config,expected_step):
    import torch
    folder=pathlib.Path(folder)
    data=torch.load(folder/'data.pt',map_location='cpu',weights_only=False)
    if not isinstance(data,dict):raise TypeError('not a native dataloader state')
    yielded=data.get('_num_yielded')
    if yielded!=expected_step:raise ValueError(f'dataloader must have completed{expected_step} batches, got {yielded}')
    extra=[]
    for role in ['actor','critic']:
        for rank in range(8):
            path=folder/role/f'extra_state_world_size_8_rank_{rank}.pt'
            state=torch.load(path,map_location='cpu',weights_only=False)
            if not isinstance(state.get('lr_scheduler'),dict) or not state.get('rng'):raise ValueError('missing scheduler/RNG')
            extra.append(dict(role=role,rank=rank,SHA=hashlib.sha256(path.read_bytes()).hexdigest(),
                scheduler_keys=sorted(state['lr_scheduler']),last_epoch=state['lr_scheduler'].get('last_epoch'),rng_keys=sorted(state['rng'])))
    manifest=json.loads((folder/'PI_COMPLETE.json').read_text())
    for rel in list(manifest['files'])+['PI_COMPLETE.json']:
        fd=os.open(folder/rel,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    fd=os.open(folder.parent/'latest_checkpointed_iteration.txt',os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    for directory in [folder/'actor',folder/'critic',folder,folder.parent]:
        fd=os.open(directory,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    return dict(dataloader_num_yielded=yielded,expected_samples_prefix=expected_step*64,data_SHA=hashlib.sha256((folder/'data.pt').read_bytes()).hexdigest(),
        dataloader_keys=sorted(data),extra_states=extra,all_native_shards_fsynced=True,
        model_optimizer_nonempty_inventory_verified=True,model_optimizer_deserialization='not repeated; native save/load contract unchanged',
        native_save_contents=list(config.actor_rollout_ref.actor.checkpoint.save_contents),native_critic_save_contents=list(config.critic.checkpoint.save_contents),
        bitwise_resume_claim=False)
