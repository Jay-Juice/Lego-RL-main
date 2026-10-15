"""Wait before a complete checkpoint; never delete assets or partially save."""
import json
import os
import shutil
import time
from pathlib import Path


def wait_for_checkpoint_space(path, step):
    minimum = float(os.environ.get("PI_MIN_CHECKPOINT_FREE_GIB", "200")) * 1024**3
    root = Path(os.environ["LEGO_RL_ROOT"])
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    marker = root / "logs" / "checkpoint_space_wait.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    announced = False
    while True:
        free = shutil.disk_usage(directory).free
        if free >= minimum:
            if announced:
                marker.write_text(json.dumps({"status": "released", "step": step, "free_gib": free / 1024**3}))
                print(f"[PI disk] space available; saving full step {step}", flush=True)
            return
        marker.write_text(json.dumps({"status": "waiting", "step": step, "free_gib": free / 1024**3,
                                     "required_gib": minimum / 1024**3, "time": time.time()}))
        if not announced:
            print(f"[PI disk] waiting before checkpoint step {step}: {free/1024**3:.1f} GiB free, "
                  f"{minimum/1024**3:.1f} required. User will release D1 space.", flush=True)
            announced = True
        time.sleep(30)
