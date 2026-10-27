"""Paired frozen-forward results; semantic differences are compared with repeat noise."""
import json,math,pathlib
from gpu_common import *

def summarize_step(step):
    import numpy as np,torch
    from verl.trainer.ppo.core_algos import compute_gae_advantage_return,compute_length_adaptive_lam
    O=P/f'forward_step{step}'
    for rank in range(8):assert json.loads((O/f'complete_rank{rank}.json').read_text())['passed']
    rows=[torch.load(p,map_location='cpu',weights_only=False) for p in sorted(O.glob('row_*.pt'))]
    expected=json.loads((P/'CACHE_FULL_RECEIPT.json').read_text())['selected'];assert len(rows)==expected
    stats=[];conditions=['true','neutral','wrong','history'];actions=[]
    for row in rows:
        mask=row['response_mask'].bool();n=int(mask.sum());a={k:v[mask].double() for k,v in row['values'].items()}
        item=dict(selection_key=row['selection_key'],family=row['family'],reward=row['reward'],actions=n,conditions={})
        for c in conditions:
            v=a[f'{c}_0'];repeat=a[f'{c}_1'];y=row['reward'];q=max(1,n//4)
            d=dict(mean=float(v.mean()),repeat_MAE=float((v-repeat).abs().mean()),repeat_max=float((v-repeat).abs().max()),
                   early_mean=float(v[:q].mean()),late_mean=float(v[-q:].mean()))
            if y is not None:d.update(mse=float((v-y).square().mean()),bias=float(v.mean()-y),early_mse=float((v[:q]-y).square().mean()),late_mse=float((v[-q:]-y).square().mean()))
            item['conditions'][c]=d
        item['contrasts']={}
        for c in conditions[1:]:
            delta=a[f'{c}_0']-a['true_0']
            item['contrasts'][c]=dict(value_MAE=float(delta.abs().mean()),value_max=float(delta.abs().max()))
            if row['reward'] is not None:
                for stage in ['mse','early_mse','late_mse']:
                    item['contrasts'][c][stage+'_control_minus_true']=item['conditions'][c][stage]-item['conditions']['true'][stage]
        stats.append(item);actions.append(a)
    valid=[i for i,r in enumerate(rows) if r['reward'] is not None];assert valid
    # Same offline batch, full action timeline, binary terminal targets; no Actor update.
    width=max(actions[i]['true_0'].numel() for i in valid);mask=torch.zeros((len(valid),width),dtype=torch.float64);reward=torch.zeros_like(mask)
    for j,i in enumerate(valid):
        n=actions[i]['true_0'].numel();mask[j,:n]=1;reward[j,n-1]=rows[i]['reward']
    lam=compute_length_adaptive_lam(mask,1.5);advantages={}
    for c in conditions:
        values=torch.zeros_like(mask)
        for j,i in enumerate(valid):values[j,:actions[i][f'{c}_0'].numel()]=actions[i][f'{c}_0']
        advantages[c],returns=compute_gae_advantage_return(reward,values,mask,1.,lam,1.,True)
        assert torch.isfinite(advantages[c]).all()
    gae={c:dict(whitened_MAE=float((advantages[c]-advantages['true'])[mask.bool()].abs().mean()),
                sign_disagreement=float(((advantages[c]>0)!=(advantages['true']>0))[mask.bool()].double().mean())) for c in conditions[1:]}
    groups={}
    for c in conditions:
        rr=[stats[i] for i in valid];pos=[r for r in rr if r['reward']==1];neg=[r for r in rr if r['reward']==0]
        auc=sum(float(a['conditions'][c]['mean']>b['conditions'][c]['mean'])+.5*float(a['conditions'][c]['mean']==b['conditions'][c]['mean']) for a in pos for b in neg)/(len(pos)*len(neg)) if pos and neg else None
        groups[c]={k:float(np.mean([r['conditions'][c][k] for r in rr])) for k in ['mse','bias','early_mse','late_mse','repeat_MAE']};groups[c]['task_AUC']=auc
    rng=np.random.default_rng(20261027);families=sorted({stats[i]['family'] for i in valid});contrasts={}
    for c in conditions[1:]:
        contrasts[c]={}
        for metric in ['mse','early_mse','late_mse']:
            by_family={f:[stats[i]['contrasts'][c][metric+'_control_minus_true'] for i in valid if stats[i]['family']==f] for f in families}
            bootstrap=[]
            for _ in range(2000):
                selected=rng.choice(families,size=len(families),replace=True);x=[v for f in selected for v in by_family[f]];bootstrap.append(float(np.mean(x)))
            values=[stats[i]['contrasts'][c][metric+'_control_minus_true'] for i in valid]
            contrasts[c][metric]=dict(mean_control_minus_true=float(np.mean(values)),family_cluster_bootstrap95=list(map(float,np.quantile(bootstrap,[.025,.975]))))
        contrasts[c]['GAE']=gae[c]
    return dict(step=step,samples=len(rows),scored=len(valid),families=len(families),conditions=groups,contrasts=contrasts,rows=stats,
                interpretation='Positive control-minus-true MSE favors true PI. CIs exploratory across checkpoints/conditions. History-only changes shape. Null result is not proof PI has no information; cohort is initial-only and native-reserve-capped. GAE is offline batch32, not original training batch64.')

def main():
    import torch
    torch.set_num_threads(1)
    report=dict(scope=json.loads((P/'CACHE_FULL_RECEIPT.json').read_text())['scope'],results=[summarize_step(s) for s in [20,30,40]],training_changed=False)
    save(P/'FINAL_CONTRAST.json',report)
    print(json.dumps(dict(completed=True,steps=[20,30,40],training_changed=False)))
if __name__=='__main__':main()

