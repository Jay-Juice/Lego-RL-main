"""Wait for protected training to exit naturally, then idle SP8 diagnostic only.

No process signals, Ray operations, cleanup, training resume, downloads or retries.
On failure preserve all outputs and stop. Started only under user's Oct27 approval.
"""
import datetime,fcntl,json,os,pathlib,shutil,subprocess,time
from gpu_common import B,R,F,P,sha,save

PROTECTED=F/'runs/resume40_after_eval_20261027_r2'
def status(phase,**details):
    (P/'QUEUE_STATE.json').write_text(json.dumps(dict(phase=phase,UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),**details),indent=2))
def source_check():
    manifest=json.loads((P/'DIAGNOSTIC_SOURCE_SHA.json').read_text())
    for name,h in manifest.items():assert sha(P/name)==h,name
    proof=json.loads((P/'PREFLIGHT_FULL.json').read_text());assert proof['passed'] and sha(P/'private_cache_full.pt')==proof['cache_SHA']
    for name,h in proof['source_SHA'].items():assert sha(name)==h,name
def idle_reason():
    if not (PROTECTED/'exit').is_file():return 'protected_training_has_not_exited'
    if (PROTECTED/'exit').read_text().strip()!='0':return 'protected_training_did_not_exit_successfully'
    active=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    if active:return 'GPU_compute_process_present'
    used=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).splitlines()
    if len(used)!=8 or any(int(x)>1000 for x in used):return 'GPU_memory_not_idle'
    for name in ['raylet','gcs_server']:
        if subprocess.run(['pgrep','-x',name],stdout=subprocess.DEVNULL).returncode==0:return 'Ray_present'
    if shutil.disk_usage(B).free<200*1024**3:return 'disk_below_200GiB'
    return None

def main():
    os.umask(0o077)
    with (P/'queue.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert not (P/'QUEUE_STARTED.json').exists(),'Do not repeat a started diagnostic'
        source_check();save(P/'QUEUE_STARTED.json',dict(pid=os.getpid(),authorization='2026-10-27 user: contrast tests; do not disturb training',protected_run=str(PROTECTED)))
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                 PYTHONPATH=f'{R}/src:{R}/third_party/verl:{R}/third_party/harbor/src:{R}',
                 GLOO_SOCKET_IFNAME='eno1',TP_SOCKET_IFNAME='eno1',NCCL_SOCKET_IFNAME='eno1')
        # No training overlay/import-time audit writes in this diagnostic process.
        for key in list(env):
            if key.startswith(('ICPS_','PI_')):env.pop(key)
        start=time.monotonic()
        try:
            for step in [20,30,40]:
                while True:
                    source_check();reason=idle_reason()
                    if reason is None:
                        status('confirming_idle',step=step);time.sleep(30)
                        if idle_reason() is None:break
                    else:status('waiting_resources',step=step,reason=reason)
                    if time.monotonic()-start>7*86400:raise RuntimeError('One-week resource wait expired; no GPU launch')
                    time.sleep(60)
                source_check();status('frozen_forward',step=step)
                command=['/home/ubuntu/.local/bin/lego-cuda12-run',str(B/'.venv/bin/torchrun'),'--standalone','--nproc_per_node=8',str(P/'frozen_forward.py'),'--step',str(step)]
                with (P/f'forward_step{step}.log').open('xb') as log:
                    done=subprocess.run(command,cwd=P,env=env,stdout=log,stderr=subprocess.STDOUT)
                save(P/f'forward_step{step}.exit.json',dict(exit=done.returncode))
                if done.returncode:raise RuntimeError(f'Frozen forward step{step} failed; no automatic retry')
                for rank in range(8):assert json.loads((P/f'forward_step{step}/complete_rank{rank}.json').read_text())['passed']
            status('summarizing')
            with (P/'summarize.log').open('xb') as log:
                completed=subprocess.run([str(B/'.venv/bin/python'),'-B',str(P/'summarize.py')],cwd=P,env=env,stdout=log,stderr=subprocess.STDOUT)
            assert completed.returncode==0 and (P/'FINAL_CONTRAST.json').is_file()
            status('complete');save(P/'QUEUE_EXIT.json',dict(exit=0))
        except BaseException as e:
            status('failed_no_retry',reason=str(e));save(P/'QUEUE_EXIT.json',dict(exit=1,error=str(e)));raise

if __name__=='__main__':main()
