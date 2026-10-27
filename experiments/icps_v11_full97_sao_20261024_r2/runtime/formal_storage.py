"""Save gate keeps original200GiB floor AND reserves safe post-save space."""
import json,os,pathlib,shutil,time
def wait_for_checkpoint_space(path,step):
    directory=pathlib.Path(path);directory.mkdir(parents=True,exist_ok=True)
    base=float(os.environ.get('PI_MIN_CHECKPOINT_FREE_GIB','200'))*1024**3
    expected=189686470567;required=max(base,expected+base+10*1024**3)
    marker=pathlib.Path(os.environ['ICPS_FORMAL_RUN_DIR'])/'checkpoint_space_wait.json'
    announced=False
    while True:
        free=shutil.disk_usage(directory).free
        if free>=required:
            if announced:marker.write_text(json.dumps(dict(status='released',step=step,free_bytes=free,required_bytes=required)))
            return
        marker.write_text(json.dumps(dict(status='waiting',step=step,free_bytes=free,required_bytes=required,time=time.time())))
        if not announced:
            print(f'[ICPS disk] waiting before save{step}: {free/1024**3:.2f}GiB free, {required/1024**3:.2f} required; no deletion/partial save',flush=True)
            announced=True
        time.sleep(30)
