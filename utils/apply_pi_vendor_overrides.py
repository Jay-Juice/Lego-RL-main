"""Install PI trainer overlays into an explicitly prepared private checkout.

Never point this at a shared environment. Unknown source hashes are rejected.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="default is validation/preview only")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "vendor_overrides/manifest.json").read_text())
    for relative, hashes in manifest.items():
        target = root / relative
        if target.is_symlink() or any(p.is_symlink() for p in target.parents if p != root.parent):
            raise RuntimeError("Refusing a symlinked/shared vendor checkout")
        current = hashlib.sha256(target.read_bytes()).hexdigest()
        if current not in hashes.values():
            raise RuntimeError(f"Unrecognized vendor source: {relative}; prepare the documented parent first")
        source = (root / "vendor_overrides" / relative).read_bytes()
        if hashlib.sha256(source).hexdigest() != hashes["new_sha256"]:
            raise RuntimeError("Overlay checksum mismatch")
        print(relative, "already current" if current == hashes["new_sha256"] else "would update")
    if args.apply:
        for relative in manifest:
            (root / relative).write_bytes((root / "vendor_overrides" / relative).read_bytes())


if __name__ == "__main__":
    main()
