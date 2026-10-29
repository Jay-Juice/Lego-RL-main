"""Bounded scalar diagnostics only. Never change batch, targets or model inputs."""
import hashlib,inspect,json,math,os,time
def summarize_records(records):
    # Normal per-call logs intentionally contain NO code/text/PI IDs.
    return [dict(state_seq=r.get('state_seq'),state_hash=r.get('state_hash'),pi_format=r.get('pi_format'),
        pre_action=r.get('pre_action'),tokens=len(r.get('pi_ids',[])),unknown=r.get('unknown'),truncated=r.get('pi_truncated'),
        windows=[{k:w.get(k) for k in ['file','qualified','start','end','source_hash','file_sha','partial','syntax']} for w in r.get('windows',[])],
        changed_files=r.get('changed_files'),captured_at_start_ns=r.get('captured_at_start_ns'),captured_at_end_ns=r.get('captured_at_end_ns')) for r in records or []]
def record_step(batch,step):
    import torch
    parent=inspect.currentframe().f_back.f_back
    metrics=parent.f_locals.get('metrics',{})
    trainer=parent.f_locals.get('self')
    rows=batch.non_tensor_batch.get('pi_call_records',[])
    counts=[len(r or []) for r in rows];tokens=[len(x.get('pi_ids',[])) for rr in rows for x in rr or []]
    initial=[];updates=[];unknown=0;changed=0
    for rr in rows:
        for i,r in enumerate(rr or []):
            n=len(r.get('pi_ids',[]));unknown+=int(bool(r.get('unknown')))
            if i==0:initial.append(n)
            elif n:updates.append(n);changed+=1
    stats=dict(step=int(step),time_ns=time.time_ns(),batch_rows=len(rows),captured_calls=sum(counts),nonempty_insertions=sum(x>0 for x in tokens),
        related_updates=changed,actual_PI_tokens=sum(tokens),max_state_tokens=max(tokens,default=0),initial_tokens=initial,update_tokens=updates,
        unknown_records=unknown,total_training_steps=int(trainer.total_training_steps) if trainer else None,
        Actor_update_called='actor/lr' in metrics,metrics={k:float(v) for k,v in metrics.items() if isinstance(v,(float,int)) or type(v).__module__=='numpy' and getattr(v,'ndim',1)==0})
    # Available from the real pre-update forward, task equal not token pooled.
    try:
        values=batch.batch['values'].detach().float().cpu();mask=batch.batch['response_mask'].detach().bool().cpu()
        rewards=batch.batch['token_level_scores'].detach().float().cpu().sum(-1)
        scores=[]
        for i in range(len(mask)):
            v=values[i][mask[i]];reward=float(rewards[i])
            if not len(v) or reward not in (0.,1.) or not torch.isfinite(v).all():continue
            scores.append(dict(row=i,reward=reward,task_MSE=float(((v-reward)**2).mean()),mean_value=float(v.mean()),min_value=float(v.min()),max_value=float(v.max())))
        def avg(kk,ss):return sum(x[kk] for x in ss)/len(ss) if ss else None
        failures=[s for s in scores if s['reward']==0];success=[s for s in scores if s['reward']==1]
        auc=sum(float(a['mean_value']>b['mean_value'])+.5*float(a['mean_value']==b['mean_value']) for a in success for b in failures)/(len(success)*len(failures)) if success and failures else None
        stats['preupdate_binary_return_calibration']=dict(eligible=len(scores),task_equal_MSE=avg('task_MSE',scores),failure_MSE=avg('task_MSE',failures),
            success_mean_value=avg('mean_value',success),failure_mean_value=avg('mean_value',failures),task_AUC=auc,rows=scores,
            scope='action mask after native filtering; real preupdate value vs original binary terminal reward, not heldout evaluation')
    except (KeyError,ValueError,RuntimeError,TypeError) as err:stats['preupdate_binary_return_calibration']=dict(status='NOT_AVAILABLE',reason=type(err).__name__)
    p=os.path.join(os.environ['ICPS_FORMAL_RUN_DIR'],'training_metrics.jsonl')
    with open(p,'a') as f:f.write(json.dumps(stats,allow_nan=False,default=str)+'\n')
