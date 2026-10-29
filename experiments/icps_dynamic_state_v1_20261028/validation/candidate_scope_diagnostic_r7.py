"""Scorer-only aggregate availability ceilings. NEVER used by PI construction.

Reads development labels after frozen generation. No case IDs or target text in
public output; no confirmation inputs. A line's presence is not useful inference.
"""
import collections
import gzip
import json
import sys
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core'),str(N/'validation')]
import development as d
import issue_program_state as index

def main():
    O=N/'reports/candidate_research_r7';V=N/'.private_candidate_research_r7'
    receipt=d.read(O/'GENERATION_RECEIPT.json');assert receipt['count']==607
    audit={r['uid']:r for r in d.read(d.OLD/'PRIVATE_COORDINATE_AND_SOURCE_AUDIT.json')}
    prior={r['uid']:r for r in d.read(d.O11/'ICPS_V11_CPU_COVERAGE_RESULTS.json')['rows']}
    counts=collections.Counter();byrepo=collections.defaultdict(collections.Counter)
    for item in receipt['rows']:
        uid=item['uid'];p=V/f'{uid}.json';assert d.sha(p)==item['SHA'];v=d.read(p)
        a=audit[uid];old=prior[uid]
        hunks=a['label_hunks'] if old['grade']=='exact_hunk' and old['hunk_map_status']=='mapped' else []
        if not hunks:continue
        cap=d.OLD/'captures'/f'{uid}.json.gz';assert d.sha(cap)==v['capture_SHA']
        snapshot=json.load(gzip.open(cap,'rt'))['snapshot'];files=snapshot['files']
        intervals=collections.defaultdict(list)
        for path,source in files.items():
            for e in index.parse_file(path,source):
                if not e.get('ambiguous'):intervals[path].append((e['start_line'],e['end_line']))
        sets=[{(h['file'],line) for line in h['changed_lines']} for h in hunks]
        want=set().union(*sets)
        available={(p,line) for p,line in want if p in files and 1<=line<=len(files[p].splitlines())}
        represented={(p,line) for p,line in available if any(lo<=line<=hi for lo,hi in intervals[p])}
        counter=dict(tasks=1,target_lines=len(want),captured_target_lines=len(available),represented_target_lines=len(represented),
            capture_any=int(bool(available)),entity_any=int(bool(represented)),
            capture_full_any=int(any(s and s<=available for s in sets)),entity_full_any=int(any(s and s<=represented for s in sets)),
            capture_missing_all=int(not available),representation_missing_all_given_capture=int(bool(available) and not represented),
            has_outside_entity_target=int(bool(available-represented)),limited_capture=int(snapshot.get('limited',False)))
        counts.update(counter);byrepo[old['family']].update(counter)
    assert counts['tasks']==366
    d.save(O/'SCOPE_DIAGNOSTIC.json',dict(UTC=d.utc(),status='SCORER_ONLY_DEVELOPMENT_AVAILABILITY_NOT_DEPLOYABLE',
        aggregate=dict(counts),repository_count=len(byrepo),source_SHA=d.sha(Path(__file__)),
        generation_receipt_SHA=d.sha(O/'GENERATION_RECEIPT.json'),
        limitations=['Labels used only to measure aggregate availability, not candidate generation.',
            'All allowed captured source lines is an oracle availability ceiling, not a feasible token-limited selector.',
            'Entity ceiling includes enclosing classes and parse fallbacks; does not prove every line is proposed or fits.',
            'No per-case output and no independent confirmation used.']))
    print(json.dumps(dict(counts),indent=2),flush=True)

if __name__=='__main__':main()
