"""Record clean resource release after the explicitly authorized stop."""
import datetime,json,pathlib,subprocess
from gpu_common import P,F,save
RUN=F/'runs/resume40_after_eval_20261027_r2'
request=json.loads((P/'USER_STOP_REQUEST.json').read_text())
assert request['run']==str(RUN)
pids=[r['pid'] for r in request['identities']]
assert all(not pathlib.Path('/proc',str(pid)).exists() for pid in pids)
code=(RUN/'exit').read_text().strip();assert code in ['0','1','130']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
memory=list(map(int,subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).split()))
assert len(memory)==8 and max(memory)<1000
for name in ['raylet','gcs_server']:
    assert subprocess.run(['pgrep','-x',name],stdout=subprocess.DEVNULL).returncode==1
out=dict(user_authorized_stop=True,time=datetime.datetime.now().astimezone().isoformat(),run=str(RUN),training_exit=code,stopped_pids=pids,GPU_memory_MiB=memory,all_GPU_idle=True,no_Ray=True,training_restart_authorized=False,latest_complete_checkpoint=40)
save(P/'USER_STOP_CONFIRMED.json',out)
print(json.dumps(out))
