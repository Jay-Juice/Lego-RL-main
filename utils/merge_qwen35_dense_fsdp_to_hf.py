#!/usr/bin/env python3
"""Merge a Qwen3.5 dense VeOmni actor checkpoint without HF key rewriting.

The FSDP shards already use Hugging Face key names. Calling the stock merger's
save_pretrained() path adds extra language_model nesting, so write safetensors
directly after checking the gathered keys and shapes against the base model.
"""

import argparse
import glob
import json
import os
import shutil
from pathlib import Path

from safetensors import safe_open
from safetensors.torch import save_file
from verl.model_merger.base_model_merger import ModelMergerConfig
from verl.model_merger.fsdp_model_merger import FSDPModelMerger

SHARD_BYTES = 5 * 1024**3
FSDP_MESH_NAMES = {("fsdp",), ("dp_shard_sp",), ("dp_shard",)}


def calculate_shards(self, mesh, mesh_dim_names):
    names = tuple(mesh_dim_names)
    if names not in FSDP_MESH_NAMES:
        raise ValueError(f"Unsupported FSDP mesh: {names}")
    return mesh.shape[-1], (mesh.shape[-1],)


FSDPModelMerger._calculate_shard_configuration = calculate_shards


def base_shapes(base_dir):
    shapes = {}
    for filename in sorted(glob.glob(os.path.join(base_dir, "*.safetensors"))):
        with safe_open(filename, framework="pt") as handle:
            for key in handle.keys():
                if key in shapes:
                    raise ValueError(f"Duplicate base-model key: {key}")
                shapes[key] = tuple(handle.get_slice(key).get_shape())
    if not shapes:
        raise ValueError(f"No base-model safetensors in {base_dir}")
    return shapes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local_dir", required=True, help="global_step_N/actor")
    parser.add_argument("--target_dir", required=True, help="new HF output directory")
    parser.add_argument("--base_dir", required=True, help="base Qwen3.5 dense HF model")
    args = parser.parse_args()

    target = Path(args.target_dir)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")

    config = ModelMergerConfig(
        operation="merge",
        backend="fsdp",
        local_dir=args.local_dir,
        target_dir=args.target_dir,
        hf_model_config_path=os.path.join(args.local_dir, "huggingface"),
        use_cpu_initialization=True,
    )
    merger = FSDPModelMerger(config)
    world_size = merger._get_world_size()
    rank_zero = merger._load_rank_zero_state_dict(world_size)
    mesh, names = merger._extract_device_mesh_info(rank_zero, world_size)
    total, shape = merger._calculate_shard_configuration(mesh, names)
    print(f"[dense merge] gathering {total} model shards from {args.local_dir}", flush=True)
    state = merger._load_and_merge_state_dicts(world_size, total, shape, names)

    shapes = base_shapes(args.base_dir)
    if any(".experts." in key for key in state):
        raise ValueError("Checkpoint contains experts; use the Qwen3.5 MoE merger")
    unexpected = set(state) - set(shapes)
    wrong_shape = {key for key in state if key in shapes and tuple(state[key].shape) != shapes[key]}
    missing = set(shapes) - set(state)
    if unexpected or wrong_shape or any(not key.startswith("mtp.") for key in missing):
        raise ValueError(
            f"Checkpoint key mismatch: unexpected={sorted(unexpected)[:4]}, "
            f"wrong_shape={sorted(wrong_shape)[:4]}, missing={sorted(missing)[:4]}"
        )

    # VeOmni does not train the speculative MTP head. Restore its base weights
    # so the output is a complete HF model, while preserving all trained keys.
    for filename in sorted(glob.glob(os.path.join(args.base_dir, "*.safetensors"))):
        with safe_open(filename, framework="pt") as handle:
            for key in missing.intersection(handle.keys()):
                state[key] = handle.get_tensor(key)
    if set(state) != set(shapes):
        raise ValueError(f"MTP backfill incomplete: {sorted(set(shapes) - set(state))[:4]}")
    print(f"[dense merge] checked {len(state)} keys; backfilled {len(missing)} MTP tensors", flush=True)

    target.mkdir(parents=True)
    shards = []
    current = {}
    current_bytes = 0
    for key, tensor in sorted(state.items()):
        tensor = tensor.contiguous()
        size = tensor.numel() * tensor.element_size()
        if current and current_bytes + size > SHARD_BYTES:
            shards.append(current)
            current = {}
            current_bytes = 0
        current[key] = tensor
        current_bytes += size
    if current:
        shards.append(current)

    weight_map = {}
    total_size = 0
    for index, shard in enumerate(shards, 1):
        filename = f"model-{index:05d}-of-{len(shards):05d}.safetensors"
        print(f"[dense merge] writing {filename} ({len(shard)} tensors)", flush=True)
        save_file(shard, str(target / filename), metadata={"format": "pt"})
        for key, tensor in shard.items():
            weight_map[key] = filename
            total_size += tensor.numel() * tensor.element_size()
    with (target / "model.safetensors.index.json").open("w", encoding="utf-8") as handle:
        json.dump({"metadata": {"total_size": total_size}, "weight_map": weight_map}, handle, indent=2)

    source_assets = Path(args.local_dir) / "huggingface"
    for source in source_assets.iterdir():
        if source.is_file() and not source.name.endswith((".safetensors", ".bin")):
            shutil.copy2(source, target / source.name)
    print(f"[dense merge] saved complete HF model to {target}", flush=True)


if __name__ == "__main__":
    main()
