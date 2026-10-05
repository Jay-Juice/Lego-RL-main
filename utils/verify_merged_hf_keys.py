"""Validate HF structure; optionally scan for NaN/Inf. Not source equivalence."""
import argparse
import json
from pathlib import Path


def keys_and_shapes(directory, *, check_finite=False):
    directory = Path(directory)
    files = sorted(directory.glob('*.safetensors'))
    if not directory.is_dir() or not files:
        raise ValueError(f'No safetensors weights found in {directory}')
    from safetensors import safe_open
    shapes, weight_map = {}, {}
    for file in files:
        with safe_open(str(file), framework='pt') as handle:
            for key in handle.keys():
                if key in shapes:
                    raise ValueError(f'Duplicate tensor key: {key}')
                shapes[key] = tuple(handle.get_slice(key).get_shape())
                weight_map[key] = file.name
                if check_finite:
                    import torch
                    tensor = handle.get_tensor(key)
                    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
                        raise ValueError(f'Non-finite tensor: {key}')
                    del tensor
    if not shapes:
        raise ValueError(f'Empty checkpoint in {directory}')
    index = directory / 'model.safetensors.index.json'
    if index.exists():
        declared = json.loads(index.read_text(encoding='utf-8')).get('weight_map')
        if declared != weight_map:
            raise ValueError(f'Weight index does not match actual tensor files: {index}')
    elif len(files) > 1:
        raise ValueError(f'Missing weight index for sharded checkpoint: {directory}')
    return shapes


def compare_shapes(base, merged, *, allow_missing_mtp=False):
    missing = sorted(base.keys() - merged.keys())
    unexpected = sorted(merged.keys() - base.keys())
    mismatch = sorted(k for k in base.keys() & merged.keys() if base[k] != merged[k])
    allowed = allow_missing_mtp and all(k.startswith('mtp.') for k in missing)
    ok = bool(base) and bool(merged) and not unexpected and not mismatch and (not missing or allowed)
    return ok, missing, unexpected, mismatch


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('merged')
    parser.add_argument('base')
    parser.add_argument('--allow-missing-mtp', action='store_true')
    parser.add_argument('--check-finite', action='store_true', help='CPU scan; may be slow for large models')
    args = parser.parse_args(argv)
    try:
        base = keys_and_shapes(args.base)
        merged = keys_and_shapes(args.merged, check_finite=args.check_finite)
        ok, missing, unexpected, mismatch = compare_shapes(base, merged, allow_missing_mtp=args.allow_missing_mtp)
        print(f'base keys: {len(base)}; merged keys: {len(merged)}')
        print(f'MISSING {len(missing)}: {missing[:8]}')
        print(f'UNEXPECTED {len(unexpected)}: {unexpected[:8]}')
        print(f'SHAPE MISMATCH {len(mismatch)}: {mismatch[:8]}')
        print('PASS - key/shape/index checks only; source weight equivalence not checked' if ok else 'FAIL - checkpoint mismatch')
        return 0 if ok else 1
    except (ValueError, OSError, ImportError) as exc:
        print(f'FAIL - {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
