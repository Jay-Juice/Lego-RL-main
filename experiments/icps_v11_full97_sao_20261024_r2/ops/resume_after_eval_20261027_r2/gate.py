import hashlib,json,os,pathlib,shutil,subprocess,sys
F=pathlib.Path(os.environ['ICPS_FORMAL_ROOT'])
R=F.parent/'pi_repair_state_v2_20261015'
O=pathlib.Path(__file__).resolve().parent
RUN=pathlib.Path(os.environ['ICPS_FORMAL_RUN_DIR'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit_sources():
    for base,manifest in [(F,F/'DEPLOYMENT.sha256'),(O,O/'SHA256SUMS')]:
        for line in manifest.read_text().splitlines():
            h,n=line.split(None,1);assert sha(base/n.strip())==h,n
    for z in json.loads((F/'runtime/SOURCE_DIFF_RECEIPT.json').read_text()).values():
        assert sha(R/z['relative'])==z['original_SHA'],z['relative']
        assert sha(F/'runtime'/z['file'])==z['candidate_SHA']
def checkpoint():
    root=pathlib.Path(os.environ['ICPS_CHECKPOINT_ROOT']); ck=pathlib.Path(os.environ['ICPS_RESUME_FROM'])
    assert (root/'latest_checkpointed_iteration.txt').read_text().strip()=='40','latest checkpoint changed: review required'
    from verl_patch.agent_loop.pi_checkpoint import validate_complete
    os.environ['PI_FORMAT']='icps_window_v11'
    m=validate_complete(ck,root.name)
    assert m['experiment']=='sao-qwen35-9b-b64-icps-v11-192-full97-r2-20261024' and m['global_step']==40 and m['world_size']==8
    assert m['source_revision']==sha(F/'DEPLOYMENT.sha256')
    import torch
    d=torch.load(ck/'data.pt',map_location='cpu',weights_only=False)
    assert d['_snapshot']['_snapshot_step']==40 and d['_steps_since_snapshot']==0
    ms=d['_snapshot']['_main_snapshot']
    assert ms['_sampler_iter_yielded']==40 and ms['_sampler_iter_state']['samples_yielded']==2560
    for role in ['actor','critic']:
        for rank in range(8):
            x=torch.load(ck/role/f'extra_state_world_size_8_rank_{rank}.pt',map_location='cpu',weights_only=False)
            assert isinstance(x.get('lr_scheduler'),dict) and x.get('rng')
    return dict(step=40,batches=40,samples=2560,required_files=len(m['files']),model_optimizer_deserialization=False)
def evaluations():
    for q in ['eval_icps203040_20261026','eval_icps_supp_20261027']:
        e=R/'logs'/q/'exit_code'
        if not e.exists():return 'waiting_evaluation:'+q
        assert e.read_text().strip()=='0','evaluation queue failed: '+q
    for step in [20,30,40]:
        a=json.loads((R/f'logs/eval-qwen35-9b-verified-full/icps-v11-step{step}-20261026-n32-threads/summary_exception_review_20261026.json').read_text())
        assert a['coverage_complete'] and a['total']==500 and not a['missing'] and not a['duplicates']
        s=json.loads((R/f'logs/eval_icps_supp_20261027/step{step}.review.json').read_text())
        assert s['complete'] and all(v=='0' for v in s['exits']), 'supplement incomplete: '+str(step)
        assert all(row['finished'] for row in s['rows'])
        expected=['django__django-10097'] if step==30 else []
        assert s['unresolved']==expected, 'unexpected unresolved task: '+str(step)
        if expected:
            row=next(row for row in s['rows'] if row['task']==expected[0])
            assert row['exception']['exception_type']=='VerifierTimeoutError'
            assert row['reward'] is None and not row['valid_verdict']
        # Finished evaluation with explicitly reported missing verdict is not a checkpoint defect.
    return None
def main():
    if len(sys.argv)>1 and sys.argv[1]=='verify':
        audit_sources(); print(json.dumps(checkpoint()));return
    waiting=evaluations()
    # User explicitly approved starting after evaluations with available space.
    # Save-time reserve remains unchanged in formal_storage.py.
    required=200*1024**3
    free=shutil.disk_usage(F).free
    if not waiting and free<required:waiting='waiting_disk'
    if not waiting:
        try:
            from prepare_full import resources
            resources()
        except (AssertionError,OSError) as e:waiting='waiting_resources:'+str(e)
    state=dict(phase=waiting or 'gates_passed',free_bytes=free,required_bytes=required)
    (RUN/'gate.json').write_text(json.dumps(state,indent=2));(RUN/'state').write_text(state['phase']+'\n')
    print(json.dumps(state))
    if waiting:sys.exit(75)
    audit_sources();state['checkpoint']=checkpoint();(RUN/'launch_gate.json').write_text(json.dumps(state,indent=2))
if __name__=='__main__':main()
