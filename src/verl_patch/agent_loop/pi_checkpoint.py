"""Checkpoint completion gate; never changes model or optimizer initialization."""
import json
import os
from pathlib import Path


def required_files(world_size):
    return ["data.pt"] + [f"{role}/{kind}_world_size_{world_size}_rank_{rank}.pt"
                         for role in ("actor", "critic")
                         for kind in ("model", "optim", "extra_state")
                         for rank in range(world_size)]


def publish_complete(folder, experiment, step, world_size):
    folder = Path(folder)
    if folder.name != f"global_step_{step}" or folder.parent.name != experiment:
        raise ValueError("Checkpoint identity mismatch")
    if (folder / "PI_COMPLETE.json").exists():
        raise FileExistsError("Complete checkpoint must not be overwritten")
    sizes = {}
    for relative in required_files(world_size):
        size = (folder / relative).stat().st_size
        if size <= 0: raise ValueError(f"Empty checkpoint shard: {relative}")
        sizes[relative] = size
    payload = {"schema": 1, "experiment": experiment, "global_step": step,
               "world_size": world_size, "files": sizes,
               "pi_format": os.environ.get("PI_FORMAT"),
               "source_revision": os.environ.get("PI_SOURCE_REVISION", "unrecorded"),
               "integrity_scope": "required nonempty shard inventory and sizes; deserialization remains fail-closed"}
    pending = folder / "PI_COMPLETE.json.pending"
    with pending.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.flush(); os.fsync(handle.fileno())
    pending.replace(folder / "PI_COMPLETE.json")


def validate_complete(folder, experiment):
    folder = Path(folder).resolve()
    payload = json.loads((folder / "PI_COMPLETE.json").read_text(encoding="utf-8"))
    if payload["experiment"] != experiment or folder.parent.name != experiment:
        raise ValueError("Refusing checkpoint from another experiment")
    if folder.name != f"global_step_{payload['global_step']}":
        raise ValueError("Checkpoint step mismatch")
    if payload["pi_format"] != os.environ.get("PI_FORMAT"):
        raise ValueError("Checkpoint PI format mismatch")
    if set(payload["files"]) != set(required_files(payload["world_size"])):
        raise ValueError("Incomplete checkpoint manifest")
    for relative, size in payload["files"].items():
        if size <= 0 or (folder / relative).stat().st_size != size:
            raise ValueError(f"Missing or truncated checkpoint shard: {relative}")
    return payload
