#!/usr/bin/env python3
"""Create a new, disjoint grading version with auditable task quarantine."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
from prepare_swesmith_harbor import RUN_TESTS, TEST_SH, is_dedicated_test_path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-tasks', type=Path, required=True)
    parser.add_argument('--source-parquet', type=Path, required=True)
    parser.add_argument('--output-tasks', type=Path, required=True)
    parser.add_argument('--output-parquet', type=Path, required=True)
    parser.add_argument('--quarantine-file', type=Path,
                        help='JSON object mapping exact instance IDs to evidence/reasons')
    args = parser.parse_args()
    source = args.source_tasks.resolve()
    target = args.output_tasks.resolve()
    if target.exists() or args.output_parquet.exists():
        raise FileExistsError('New asset paths must not exist')
    if source == target or source in target.parents or target in source.parents:
        raise ValueError('Source and target must be disjoint')
    frame = pd.read_parquet(args.source_parquet)
    manifest = json.loads((source / 'manifest.json').read_text())
    ids = [row['extra_info']['instance_id'] for _, row in frame.iterrows()]
    assert len(ids) == len(set(ids)) > 0
    assert set(ids) == {x['instance_id'] for x in manifest['tasks']}
    quarantine = json.loads(args.quarantine_file.read_text()) if args.quarantine_file else {}
    if not isinstance(quarantine, dict) or not set(quarantine).issubset(ids):
        raise ValueError('Quarantine must map IDs in this source dataset to reasons')
    excluded = []
    for iid in ids:
        config = json.loads((source/iid/'tests/config.json').read_text())
        paths = {node.split('::', 1)[0] for node in config['FAIL_TO_PASS'] + config['PASS_TO_PASS']}
        unsafe = sorted(path for path in paths if not is_dedicated_test_path(path))
        if unsafe or iid in quarantine:
            excluded.append({'instance_id': iid, 'reason': 'source_boundary_or_failed_control',
                             'unsafe_restore_paths': unsafe, 'control_evidence': quarantine.get(iid)})
    excluded_ids = {row['instance_id'] for row in excluded}
    kept_ids = [iid for iid in ids if iid not in excluded_ids]
    if not kept_ids:
        raise ValueError('No eligible tasks remain')
    frame = frame.loc[[iid not in excluded_ids for iid in ids]].copy()
    target.mkdir()
    audit = []
    for index, row in frame.iterrows():
        iid = row['extra_info']['instance_id']
        old = source / iid
        assert old.is_dir() and old.resolve().parent == source
        new = target / iid
        assert Path(row['extra_info']['harbor_task_path']).resolve() == old.resolve()
        shutil.copytree(old, new)
        scripts = {'tests/run_tests.py': RUN_TESTS, 'tests/test.sh': TEST_SH}
        for relative, content in scripts.items():
            (new / relative).write_text(content, encoding='utf-8', newline='\n')
        unchanged = {}
        for file in old.rglob('*'):
            if not file.is_file():
                continue
            relative = file.relative_to(old).as_posix()
            if relative not in scripts:
                assert sha(file) == sha(new / relative)
                unchanged[relative] = sha(file)
        prompt = [dict(x) for x in row['prompt']]
        assert len(prompt) == 1 and Path(prompt[0]['content']).resolve() == old.resolve()
        prompt[0]['content'] = str(new)
        extra = dict(row['extra_info'])
        extra['harbor_task_path'] = str(new)
        frame.at[index, 'prompt'] = prompt
        frame.at[index, 'extra_info'] = extra
        audit.append({'instance_id': iid, 'unchanged_files': unchanged})
    manifest['tasks'] = [dict(row, controls=None) for row in manifest['tasks'] if row['instance_id'] not in excluded_ids]
    manifest['excluded'] = manifest.get('excluded', []) + excluded
    manifest['grading_protocol_version'] = 'dedicated-tests-verdict-v3-20260929'
    manifest['previous_manifest_sha256'] = sha(source / 'manifest.json')
    manifest['previous_parquet_sha256'] = sha(args.source_parquet)
    manifest['generator_sha256'] = sha(Path(__file__).with_name('prepare_swesmith_harbor.py'))
    manifest['versioning_script_sha256'] = sha(Path(__file__))
    manifest['row_order_preserved'] = True
    manifest['membership_preserved'] = not excluded
    manifest['source_task_count'] = len(ids)
    manifest['new_quarantine_count'] = len(excluded)
    manifest['quarantine_file_sha256'] = sha(args.quarantine_file) if args.quarantine_file else None
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (target / 'asset_integrity.json').write_text(json.dumps(audit, indent=2) + '\n')
    (target / 'quarantine.json').write_text(json.dumps(excluded, indent=2) + '\n')
    args.output_parquet.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output_parquet, index=False)
    assert [x['instance_id'] for x in pd.read_parquet(args.output_parquet).extra_info] == kept_ids
    print(json.dumps({'tasks': len(kept_ids), 'quarantined': len(excluded),
                      'parquet_sha256': sha(args.output_parquet), 'target': str(target)}))


if __name__ == '__main__':
    main()
