"""Stop only Ray daemons belonging to one isolated training session root."""

from __future__ import annotations

import os
import re
import sys

import psutil


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: stop_scoped_ray.py /tmp/lego-ray.XXXXXXXX")
    root = os.path.realpath(sys.argv[1])
    if (
        os.path.dirname(root) != "/tmp"
        or re.fullmatch(r"lego-ray\.[A-Za-z0-9]{8}", os.path.basename(root)) is None
        or not os.path.isdir(root)
        or os.stat(root).st_uid != os.getuid()
    ):
        raise SystemExit(f"refusing unsafe Ray session root: {root}")

    buckets: dict[str, list[psutil.Process]] = {
        "raylet": [],
        "other": [],
        "gcs_server": [],
    }
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            argv = proc.info["cmdline"] or []
            # All Ray daemons launched with --temp-dir carry their session path
            # in at least one argument. Check the exact root followed by '/'.
            if not any(root + "/" in arg or arg.endswith("=" + root) for arg in argv):
                continue
            name = proc.info["name"] or ""
            if name == "raylet":
                bucket = "raylet"
            elif name == "gcs_server":
                bucket = "gcs_server"
            elif name == "python" or name.startswith("python3") or name.startswith("ray::"):
                bucket = "other"
            else:
                continue
            buckets[bucket].append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    for label in ("raylet", "other", "gcs_server"):
        procs = buckets[label]
        if not procs:
            continue
        print(f"[ray] stopping {len(procs)} scoped {label} process(es)", flush=True)
        for proc in procs:
            try:
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _, alive = psutil.wait_procs(procs, timeout=8)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        psutil.wait_procs(alive, timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
