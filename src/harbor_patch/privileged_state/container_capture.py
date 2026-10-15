"""Executed in the task container. Stdlib only; read-only Git/filesystem access."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import tempfile
import shutil

MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 16 * 1024 * 1024
MAX_CAPTURE_ATTEMPTS = 5
CAPTURE_RETRY_DELAY_SEC = 0.05
_observer_git_dir = None


class UnstableSnapshotError(RuntimeError):
    """A concurrent workspace writer invalidated this entire read attempt."""


def git_result(root, *args, input=None):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_PAGER="cat", LC_ALL="C")
    env.pop("GIT_EXTERNAL_DIFF", None)
    cmd = ["git", "-c", "core.fsmonitor=false", "-c", "diff.external=", "-C", root, *args]
    if _observer_git_dir:
        cmd[1:1] = ["--git-dir=" + _observer_git_dir, "--work-tree=" + root]
    return subprocess.run(cmd, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=15)


def git(root, *args):
    result = git_result(root, *args)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-2000:])
    return result.stdout


def preserve_baseline(root, baseline):
    """Preserve only the prepared commit and its tree, outside the Actor worktree."""
    directory = tempfile.mkdtemp(prefix="lego-pi-baseline-")
    try:
        subprocess.run(["git", "init", "--bare", "-q", directory], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        objects = git(root, "rev-list", "--objects", "--no-object-names", baseline + "^{tree}")
        # No ancestor history, references or oracle data. Pack avoids hardlinks to
        # objects the Actor may subsequently remove or replace.
        packed = git_result(root, "pack-objects", "--stdout", input=baseline.encode() + b"\n" + objects)
        if packed.returncode:
            raise RuntimeError(packed.stderr.decode("utf-8", "replace"))
        subprocess.run(["git", "--git-dir=" + directory, "index-pack", "--stdin"],
                       input=packed.stdout, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=30)
        subprocess.run(["git", "--git-dir=" + directory, "read-tree", baseline],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        pathlib.Path(directory, "pi_baseline.json").write_text(json.dumps(
            {"repo_root": str(pathlib.Path(root).resolve()), "baseline_sha": baseline}))
        return directory
    except BaseException:
        shutil.rmtree(directory)
        raise


def _collect_once(root=None, baseline=None):
    begin = time.time_ns()
    root = root or git(os.getcwd(), "rev-parse", "--show-toplevel").decode().strip()
    if baseline is None:
        baseline = git(root, "rev-parse", "HEAD").decode().strip()
        status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
        if status:
            raise RuntimeError("Prepared buggy baseline is dirty: " + status.decode("utf-8", "replace")[:1500])
        return {"repo_root": root, "baseline_sha": baseline, "captured_at_start_ns": begin,
                "captured_at_end_ns": time.time_ns(), "clean": True}
    names = git(root, "diff", "--no-ext-diff", "--no-textconv", "--name-only", "-z", baseline, "--")
    names += git(root, "ls-files", "--others", "--exclude-standard", "-z")
    paths = sorted(set(x.decode("utf-8", "surrogateescape") for x in names.split(b"\0") if x))
    files, used = [], 0
    for name in paths:
        rel = pathlib.PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts or ".git" in rel.parts:
            raise RuntimeError("Out-of-worktree changed path")
        path = pathlib.Path(root, name)
        if any(pathlib.Path(root, *rel.parts[:i]).is_symlink() for i in range(1, len(rel.parts))):
            raise RuntimeError("Symlink ancestor in changed path: " + name)
        item = {"path": name, "status": "modified", "current_source": None, "old_source": None}
        old = git_result(root, "show", baseline + ":" + name)
        if old.returncode:
            if git(root, "ls-tree", "-z", baseline, "--", name):
                raise RuntimeError("Cannot read prepared baseline blob: " + name)
            item["status"] = "added"
        if not path.exists() and not path.is_symlink():
            item["status"] = "removed"
            current = b""
        elif path.is_symlink():
            current = os.readlink(path).encode("utf-8", "surrogateescape")
            item["kind"] = "symlink"
        elif path.is_file():
            before = path.stat()
            with path.open("rb") as f:
                current = f.read(MAX_FILE + 1)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise UnstableSnapshotError("File changed during PI capture: " + name)
            item["mode"] = before.st_mode
            item["size"] = before.st_size
        else:
            item["kind"] = "non_regular"
            current = b""
        if len(current) > MAX_FILE or len(old.stdout) > MAX_FILE or used + len(current) + len(old.stdout) > MAX_TOTAL:
            # Fail rather than silently identifying distinct states with incomplete hashes.
            raise RuntimeError("PI capture byte budget exceeded: " + name)
        used += len(current) + len(old.stdout)
        item["sha256"] = hashlib.sha256(current).hexdigest()
        if item.get("kind") not in {"symlink", "non_regular"}:
            try:
                if b"\0" in current or b"\0" in old.stdout:
                    raise UnicodeError("binary")
                item["current_source"] = current.decode("utf-8")
                item["old_source"] = old.stdout.decode("utf-8") if old.returncode == 0 else ""
                item["kind"] = "text"
            except UnicodeError:
                item["kind"] = "binary"
        files.append(item)
    again = git(root, "diff", "--no-ext-diff", "--no-textconv", "--name-only", "-z", baseline, "--")
    again += git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if set(names.split(b"\0")) != set(again.split(b"\0")):
        raise UnstableSnapshotError("Changed path inventory unstable during PI capture")
    return {"repo_root": root, "baseline_sha": baseline, "files": files,
            "captured_at_start_ns": begin, "captured_at_end_ns": time.time_ns(),
            "atomic": False, "valid": True}


def _collect(root=None, baseline=None):
    # Initial buggy baseline still requires clean state; never retry onto a new HEAD.
    if baseline is None:
        return _collect_once(root, baseline)
    begin = time.time_ns()
    root = root or git(os.getcwd(), "rev-parse", "--show-toplevel").decode().strip()
    errors = []
    for attempt in range(1, MAX_CAPTURE_ATTEMPTS + 1):
        try:
            snapshot = _collect_once(root, baseline)
        except (UnstableSnapshotError, FileNotFoundError) as exc:
            # Discard every file from this attempt, then reread the full current delta.
            # All attempts finish before the proxy may start generating this action.
            errors.append(str(exc))
            if attempt == MAX_CAPTURE_ATTEMPTS:
                raise UnstableSnapshotError(
                    f"PI snapshot unstable after {attempt} attempts: {exc}") from exc
            time.sleep(CAPTURE_RETRY_DELAY_SEC)
        else:
            snapshot.update(captured_at_start_ns=begin, capture_attempts=attempt,
                            capture_retry_errors=errors)
            return snapshot


def collect(root=None, baseline=None, observer=None, *, preserve=False):
    global _observer_git_dir
    if baseline is None:
        snapshot = _collect(root, baseline)
        if preserve:
            snapshot["baseline_observer"] = preserve_baseline(snapshot["repo_root"], snapshot["baseline_sha"])
        return snapshot
    previous = _observer_git_dir
    try:
        if observer:
            probe = git_result(root, "cat-file", "-e", baseline + "^{commit}")
            if probe.returncode:
                error = probe.stderr.decode("utf-8", "replace")
                if not any(s in error.lower() for s in ("not a valid object", "bad object", "not a git repository")):
                    raise RuntimeError(error)
                meta = json.loads(pathlib.Path(observer, "pi_baseline.json").read_text())
                if meta != {"repo_root": str(pathlib.Path(root).resolve()), "baseline_sha": baseline}:
                    raise RuntimeError("PI baseline observer identity mismatch")
                _observer_git_dir = observer
                git(root, "cat-file", "-e", baseline + "^{commit}")
        snapshot = _collect(root, baseline)
        if _observer_git_dir:
            snapshot["baseline_observer_used"] = True
        return snapshot
    finally:
        _observer_git_dir = previous


if __name__ == "__main__":
    print(json.dumps(collect(*(sys.argv[1:]), preserve=len(sys.argv) == 1), ensure_ascii=True))
