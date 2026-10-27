"""Oct27 explicit user stop; signal only identity-checked driver and own idle queue."""
import datetime,json,os,pathlib,signal
from gpu_common import F,P,CKPT,EXP,save
RUN=F/'runs/resume40_after_eval_20261027_r2'

def identity(pid,kind):
    proc=pathlib.Path('/proc')/str(pid)
    cmd=proc.joinpath('cmdline').read_bytes().split(b'\0')
    args=[x.decode() for x in cmd if x]
    env=dict(x.split(b'=',1) for x in proc.joinpath('environ').read_bytes().split(b'\0') if b'=' in x)
    if kind=='driver':
        assert '-m' in args and 'icps_resume_main' in args
        assert env[b'ICPS_FORMAL_RUN_DIR'].decode()==str(RUN)
        assert 'trainer.experiment_name='+EXP in args
    else:
        assert args[-1]=='wait_and_run.py'
        assert proc.joinpath('cwd').resolve()==P
        assert json.loads((P/'QUEUE_STATE.json').read_text())['phase']=='waiting_resources'
        assert not list(P.glob('forward_step*/loaded_rank*.json'))
    return dict(pid=pid,start=proc.joinpath('stat').read_text().split(') ',1)[1].split()[19],kind=kind)

def main():
    assert not (RUN/'exit').exists()
    identities=[identity(2447768,'idle_queue'),identity(1661889,'driver')]
    checkpoints={}
    for step in [20,30,40]:
        root=CKPT/f'global_step_{step}';m=json.loads((root/'PI_COMPLETE.json').read_text())
        assert m['experiment']==EXP and m['global_step']==step and m['world_size']==8
        for rel,size in m['files'].items():assert (root/rel).is_file() and (root/rel).stat().st_size==size
        checkpoints[str(step)]=dict(required_files=len(m['files']),inventory_passed=True)
    assert (CKPT/'latest_checkpointed_iteration.txt').read_text().strip()=='40'
    save(P/'USER_STOP_REQUEST.json',dict(time=datetime.datetime.now().astimezone().isoformat(),authorization='2026-10-27 user: stop training and directly perform checks',run=str(RUN),identities=identities,checkpoints=checkpoints,last_complete_checkpoint=40,last_completed_step=42,unsaved_progress='41/42 and in-flight43',restart_authorized=False))
    for old in identities:
        assert identity(old['pid'],old['kind'])==old
        os.kill(old['pid'],signal.SIGINT)
        print(json.dumps(dict(signal='SIGINT',**old)),flush=True)

if __name__=='__main__':main()
