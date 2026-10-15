"""Read-only checksum gate for the isolated repair-state deployment."""
import hashlib
import json
from pathlib import Path


root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "VERSION_SOURCE_SHA256.json").read_text())
for relative, expected in manifest.items():
    actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Source drift: {relative}")
print(f"Verified {len(manifest)} runtime source files")
