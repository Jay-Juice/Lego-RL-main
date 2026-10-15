"""Local audit artifacts only; never fed back into Actor or PI collection."""
import os
from pathlib import Path


def archive_batch(batch, step, config):
    directory = os.environ.get("PI_BATCH_AUDIT_DIR")
    if not directory:
        return
    import torch
    from omegaconf import OmegaConf
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"step_{step:04d}.pt"
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite PI batch audit: {target}")
    # Keep the actual accepted/filtered row order and the loss inputs. No optimizer
    # step, RNG operation, or mutation of live tensors is performed here.
    payload = {"global_step": step,
               "tensors": {key: value.detach().cpu().clone() for key, value in batch.batch.items()},
               "non_tensor": batch.non_tensor_batch,
               "meta": batch.meta_info,
               "config": OmegaConf.to_container(config, resolve=True),
               "source_revision": os.environ.get("PI_SOURCE_REVISION", "unrecorded")}
    pending = target.with_suffix(".pt.pending")
    with pending.open("xb") as handle:
        torch.save(payload, handle)
        handle.flush(); os.fsync(handle.fileno())
    pending.replace(target)
