"""Recover all nine Pyquery controls using the AL frozen HTTP fixture."""
import concurrent.futures as cf
import json
from pathlib import Path
import shutil
import repair_swesmith_embedded_assets as repair
from swesmith_http_fixture import SHA


def main():
    repair.TARGET = repair.ROOT/'data/swesmith_pyquery_http_recovered_v4b_20260930'
    repair.OUT = repair.ROOT/'logs/swesmith_pyquery_http_recovered_v4b_20260930'
    repair.TARGET.mkdir(exist_ok=False)
    repair.OUT.mkdir(exist_ok=False)
    fixture = Path('/media/ubuntu/D1/zsj/agent-lightning-runtime/data/swe-smith-training/http-fixtures-v1')
    assert repair.audit.sha(fixture/'ru-wikipedia-main.html') == SHA
    original = repair.RUN_TESTS
    start = original.index('        result = subprocess.run(')
    end = original.index('        (LOGS.parent / "test_output.log")', start)
    chunk = original[start:end]
    repair.RUN_TESTS = original[:start] + '        from swesmith_http_fixture import recorded_http\n        with recorded_http(config, TESTS):\n' + ''.join('    '+line if line.strip() else line for line in chunk.splitlines(keepends=True)) + original[end:]
    original_copytree = shutil.copytree
    def copytree(src, dst, *args, **kwargs):
        result = original_copytree(src, dst, *args, **kwargs)
        if Path(dst).parent == repair.TARGET:
            shutil.copy2(Path(__file__).with_name('swesmith_http_fixture.py'), Path(dst)/'tests/swesmith_http_fixture.py')
            original_copytree(fixture, Path(dst)/'tests/http_fixture')
        return result
    repair.shutil.copytree = copytree
    old = json.loads((repair.ROOT/'logs/swesmith_embedded_repair_v4b_20260930/summary.json').read_text())
    ids = {x['instance_id'] for x in old['results'] if x['instance_id'].startswith('gawel__pyquery.') and not x['control_pass']}
    rows = [x for x in json.loads((repair.SOURCE/'manifest.json').read_text())['tasks'] if x['instance_id'] in ids]
    assert len(rows) == 9
    results = []
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        for future in cf.as_completed([pool.submit(repair.run, row) for row in rows]):
            result = future.result(); results.append(result)
            print(json.dumps({'iid': result['instance_id'], 'pass':result['control_pass'], 'bug':result.get('bug',{}).get('reward'), 'oracle':result.get('oracle',{}).get('reward'), 'error':result.get('error')}), flush=True)
    repair.audit.dump(repair.OUT/'summary.json', {'total':len(results), 'passed':sum(x['control_pass'] for x in results), 'results':results, 'fixture_sha256':SHA, 'fixture_provenance':json.loads((fixture/'manifest.json').read_text())})


if __name__ == '__main__':
    main()
