"""Post-hoc CPU audit and calibration decomposition. No model training or GPU use."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',HF_HUB_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
import json,pathlib,re
import numpy as np
import torch
from gpu_common import P,B,sha,save
torch.set_num_threads(1)
CONDS=['true','neutral','wrong','history']

def mean(x):return float(np.mean(x))
def quant(x):return dict(zip(['min','q25','median','q75','max'],map(float,np.quantile(x,[0,.25,.5,.75,1]))))

def main():
    proof=json.loads((P/'PREFLIGHT_FULL.json').read_text())
    assert sha(P/'private_cache_full.pt')==proof['cache_SHA']
    cache=torch.load(P/'private_cache_full.pt',map_location='cpu',weights_only=False)
    selected=cache['rows'];assert len(selected)==32 and len({r['selection_key'] for r in selected})==32
    report=json.loads((P/'FINAL_CONTRAST.json').read_text())
    evidence=[];total_calls=0;all_exact=True
    for step,summary in zip([20,30,40],report['results'],strict=True):
        O=P/f'forward_step{step}';assert summary['step']==step
        assert json.loads((P/f'forward_step{step}.exit.json').read_text())['exit']==0
        for rank in range(8):
            completed=json.loads((O/f'complete_rank{rank}.json').read_text())
            loaded=json.loads((O/f'loaded_rank{rank}.json').read_text())
            assert completed['passed'] and completed['parameters_unchanged'] and completed['rows']==32
            assert completed['optimizer_steps']==completed['backward_calls']==0
            assert loaded['model_loaded'] and not loaded['optimizer_loaded'] and loaded['checkpoint_step']==step
        rows=[]
        for i,source in enumerate(selected):
            row=torch.load(O/f'row_{i:03d}.pt',map_location='cpu',weights_only=False)
            assert row['selection_key']==source['selection_key'] and row['reward']==source['reward']
            assert torch.equal(row['response_mask'],torch.tensor(source['response_mask']))
            mask=row['response_mask'].bool();values={}
            assert set(row['values'])=={f'{c}_{r}' for c in CONDS for r in [0,1]}
            for c in CONDS:
                a,b=row['values'][c+'_0'],row['values'][c+'_1']
                assert a.shape==b.shape==mask.shape and torch.isfinite(a).all() and torch.isfinite(b).all()
                all_exact &= torch.equal(a,b);total_calls+=2
                values[c]=a[mask].double().numpy()
            rows.append(dict(family=row['family'],reward=row['reward'],v=values))
        result=dict(step=step,conditions={},contrasts={})
        families=sorted({r['family'] for r in rows})
        y=np.array([r['reward'] for r in rows],dtype=float)
        for c in CONDS:
            mu=np.array([r['v'][c].mean() for r in rows]);m2=np.array([(r['v'][c]**2).mean() for r in rows])
            mse=m2-2*y*mu+y*y;bias=float((mu-y).mean())
            assert abs(mse.mean()-summary['conditions'][c]['mse'])<1e-12
            cv_intercept=[];cv_affine=[];cv_prior=[]
            # Fold assignments are by repository, identical across conditions.
            # Post-hoc scalar calibration of existing predictions, NOT a PI readout.
            for family in families:
                test=np.array([r['family']==family for r in rows]);train=~test
                delta=float((y[train]-mu[train]).mean())
                centered_mean=mu[test]+delta;centered_m2=m2[test]+2*delta*mu[test]+delta*delta
                cv_intercept.extend(centered_m2-2*y[test]*centered_mean+y[test]**2)
                gram=np.array([[1.,mu[train].mean()],[mu[train].mean(),m2[train].mean()]])
                rhs=np.array([y[train].mean(),(y[train]*mu[train]).mean()])
                intercept,slope=np.linalg.solve(gram+np.diag([0.,1e-10]),rhs)
                predmean=intercept+slope*mu[test]
                predm2=intercept**2+2*intercept*slope*mu[test]+slope**2*m2[test]
                cv_affine.extend(predm2-2*y[test]*predmean+y[test]**2)
                cv_prior.extend((y[train].mean()-y[test])**2)
            result['conditions'][c]=dict(mean_value=mean(mu),bias=bias,task_equal_MSE=mean(mse),
                within_trajectory_variance=mean(m2-mu**2),trajectory_mean_prediction_MSE=mean((mu-y)**2),
                in_sample_oracle_offset_corrected_MSE=mean(mse)-bias*bias,
                leave_repository_out_intercept_MSE=mean(cv_intercept),leave_repository_out_affine_MSE=mean(cv_affine),
                leave_repository_out_prior_MSE=mean(cv_prior),value_mean_by_outcome={str(label):mean(mu[y==label]) for label in [0,1]},
                task_equal_MSE_by_outcome={str(label):mean(mse[y==label]) for label in [0,1]},
                outside_0_1_fraction_task_equal=mean([mean((r['v'][c]<0)|(r['v'][c]>1)) for r in rows]))
        true_mse=np.array([mean((r['v']['true']-r['reward'])**2) for r in rows])
        for c in CONDS[1:]:
            delta=np.array([mean((r['v'][c]-r['reward'])**2)-true_mse[i] for i,r in enumerate(rows)])
            shift=np.array([mean(r['v'][c]-r['v']['true']) for r in rows])
            result['contrasts'][c]=dict(task_value_MAE=quant([mean(abs(r['v'][c]-r['v']['true'])) for r in rows]),
                mean_task_value_MAE=mean([mean(abs(r['v'][c]-r['v']['true'])) for r in rows]),
                mean_control_value_shift=mean(shift),positive_MSE_benefit_tasks=int((delta>0).sum()),negative_MSE_benefit_tasks=int((delta<0).sum()),
                raw_MSE_gain=mean(delta),gain_by_outcome={str(label):mean(delta[y==label]) for label in [0,1]},
                relative_raw_MSE_gain=mean(delta)/(true_mse.mean()+delta.mean()),
                gain_after_in_sample_offset_correction=result['conditions'][c]['in_sample_oracle_offset_corrected_MSE']-result['conditions']['true']['in_sample_oracle_offset_corrected_MSE'],
                gain_after_leave_repository_out_affine=result['conditions'][c]['leave_repository_out_affine_MSE']-result['conditions']['true']['leave_repository_out_affine_MSE'])
        evidence.append(result)
    # Conservative exact source-block visibility in ACTOR history before actions.
    # No token n-gram or broad term overlap is called semantic redundancy.
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(str(B/'Qwen3.5-9B'),local_files_only=True)
    visibility=[]
    for row in selected:
        blocks=[];current=[]
        for line in row['pi_text'].splitlines(keepends=True):
            if line.startswith('WINDOW '):
                if current:blocks.append(''.join(current));current=[]
            elif line.startswith('[ICPS1.1 '):continue
            else:current.append(line)
        if current:blocks.append(''.join(current))
        blocks=[' '.join(b.split()) for b in blocks if len(''.join(b.split()))>=20]
        action_indices=np.flatnonzero(row['response_mask']);n=len(action_indices)
        fractions={}
        for label,pos in [('initial',0),('quarter',n//4),('three_quarters',3*n//4),('last',n-1)]:
            prefix=row['actor_ids'][:row['prompt_len']+int(action_indices[pos])]
            text=' '.join(tokenizer.decode(prefix).split())
            fractions[label]=dict(seen=sum(b in text for b in blocks),total=len(blocks))
        visibility.append(fractions)
    vis={stage:dict(blocks=sum(r[stage]['total'] for r in visibility),seen=sum(r[stage]['seen'] for r in visibility),
        trajectories_with_any=sum(r[stage]['seen']>0 for r in visibility),trajectories_with_all=sum(r[stage]['total']>0 and r[stage]['total']==r[stage]['seen'] for r in visibility)) for stage in ['initial','quarter','three_quarters','last']}
    output=dict(passed=True,steps=[20,30,40],rows_each=32,total_trajectory_condition_forwards=total_calls,
        all_repeated_output_tensors_exact_equal=bool(all_exact),all_24_rank_parameter_fingerprints_unchanged=True,all_checkpoints_model_only_loaded=True,
        cache_SHA=proof['cache_SHA'],final_report_SHA=sha(P/'FINAL_CONTRAST.json'),all_GPU_tests_exit0=True,optimizer_steps=0,
        positive=26,negative=6,repository_families=16,constant_half_MSE=.25,in_sample_fitted_prior_MSE=(26/32)*(6/32),
        action_lengths=quant([sum(r['response_mask']) for r in selected]),actor_lengths=quant([len(r['actor_ids']) for r in selected]),
        PI_lengths=quant([len(r['true_pi_ids']) for r in selected]),results=evidence,exact_block_visibility=vis,
        limits=['Post-hoc exploratory calibration; same 32 off-policy training tasks, initial-only PI and six failures.',
                'Affine readout uses existing scalar V only, not hidden states or PI information; it does not test learnability of unused PI.',
                'In-sample offset/prior use all labels and are descriptive lower-complexity references, not held-out estimates.',
                'Exact block visibility collapses whitespace, requires >=20 nonspace chars, and sees only prior Actor context; no-match does not prove novelty.',
                'Equal repeats are confined to these forward tensors, not backward/update/checkpoint bitwise reproducibility.'])
    assert total_calls==768 and not torch.cuda.is_initialized()
    save(P/'POSTHOC_ANALYSIS_20261028.json',output)
    # Aggregate only; private trajectory outputs remain on server.
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
