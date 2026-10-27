"""Read-only verification of the archived runtime; no launch/deploy/install."""
import hashlib,json
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'ICPS_SOURCE_MANIFEST.json').read_text())
    for item in manifest['files']:
        p=root/item['path']
        if not p.is_file() or p.is_symlink():raise ValueError(item['path'])
        if p.stat().st_size!=item['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Archive mismatch: '+item['path'])
    print(json.dumps(dict(passed=True,files=len(manifest['files']),base_commit=manifest['base_commit'],deployment=False)))

if __name__=='__main__':main()
