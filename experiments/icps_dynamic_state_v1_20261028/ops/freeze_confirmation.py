"""Identity-only prior-exposure audit and confirmation manifest freezing.

No labels/coordinates are returned or used to rank samples. Exact-hunk grade
is the predeclared eligibility stratum; all eligible identities are retained.
"""
import datetime
import hashlib
import json
import os
import pathlib

B=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
N=B/'experiments/icps_dynamic_state_v1_20261028'
R=B/'experiments/pi_repair_state_v2_20261015'
F=B/'experiments/icps_v11_full97_sao_20261024_r2'
V=N/'.private_confirmation_r4'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2)
def family(t):return t.split('.')[0]

os.umask(0o077)
freeze=read(N/'CANDIDATE_FREEZE_R4.json')
for name,want in freeze['source_SHA'].items():assert sha(N/name)==want,name
oldpath=R/'.private_location_pi_control_20261022/manifests/P0_FROZEN_607_MANIFEST.json'
datapath=F/'preflight/FULL6248_DATA_IDENTITY.json'
locpath=R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json'
old={x['task_id'] for x in read(oldpath)['rows']};assert len(old)==607
tasks=read(datapath)['tasks'];assert len(tasks)==6248
grades={x['instance_id']:x['confidence'] for x in read(locpath)['rows']}
verified={p.parent.name for p in (B/'data/swebench-verified').rglob('task.toml')};assert len(verified)==500
oldfamilies={family(t) for t in old}
available=[t for t in tasks if t['instance_id'] not in old|verified and grades.get(t['instance_id'])=='exact_hunk' and family(t['instance_id']) not in oldfamilies]
assert len(available)==221
ids={t['instance_id'] for t in available}

# Complete label inventories enumerate the training dataset, not used PI
# examples. Record their existence/hash but do not treat catalog membership
# as experimental exposure. Actual view/selection records below are included.
catalog_names={'GOLD_EVIDENCE_SOURCE_V2.json','LOCATION_SOURCE_V2.json'}
included=set();catalogs=[]
for root in sorted(R.glob('.private*')):
    for p in sorted(root.glob('*.json')):
        catalog=(p.name in catalog_names or (root.name=='.private_oracle_pi_20261022' and p.name.startswith('ORACLE_DATA_MANIFEST')))
        if catalog:catalogs.append(dict(path=str(p.relative_to(R)),SHA=sha(p),reason='full dataset provenance/label inventory, not PI-generated sample selection'))
        else:included.add(p)
    for p in root.glob('manifests/*.json'):included.add(p)
    for p in root.glob('live_approved*/*/frozen_execution.json'):included.add(p)

# Additional controlled-Critic manifests may live in ops/logs rather than
# private roots. Only metadata filenames are inspected, never trajectory files.
for parent in [R/'ops',R/'logs',F/'ops',F/'logs']:
    if not parent.exists():continue
    for root in parent.iterdir():
        if not root.is_dir() or not any(s in root.name.lower() for s in ['critic','oracle','icps','fces','packing','calibration']):continue
        for pattern in ['*.json','*/*.json']:
            for p in root.glob(pattern):
                name=p.name.lower()
                if any(s in name for s in ['manifest','selection','split','inventory']) and not any(s in name for s in ['source_manifest','source_sha','deployment','delivery']):included.add(p)

exposed=set();receipts=[];private_reasons={}
for p in sorted(included):
    assert p.stat().st_size<=64*1024**2,('metadata audit bound',str(p))
    text=p.read_text();json.loads(text)  # malformed evidence fails closed
    matched={t for t in ids if t in text or hashlib.sha256(('icps-coverage:'+t).encode()).hexdigest() in text}
    exposed|=matched
    receipts.append(dict(path=str(p.relative_to(B)),SHA=sha(p),bytes=p.stat().st_size,candidate_identity_matches=len(matched)))
    for t in matched:private_reasons.setdefault(t,[]).append(str(p.relative_to(B)))

rows=[]
for t in sorted(available,key=lambda t:t['instance_id']):
    if t['instance_id'] in exposed:continue
    row=dict(t)
    row.update(uid=hashlib.sha256(('dynamic-confirmation-r4:'+t['instance_id']).encode()).hexdigest(),family=family(t['instance_id']))
    rows.append(row)
assert len(rows)>0,'No independent task identities remain; no substitute cohort'
V.mkdir(exist_ok=False)
manifest=dict(created=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=rows,excluded=private_reasons,
    candidate_freeze_SHA=sha(N/'CANDIDATE_FREEZE_R4.json'),plan_SHA=sha(N/'INDEPENDENT_VALIDATION_PLAN.md'),
    identity_sources_SHA={str(p.relative_to(B)):sha(p) for p in [oldpath,datapath,locpath]},
    audited_metadata=receipts,catalogs_not_counted_as_exposure=catalogs,selection='All exact-grade candidate tasks from families absent in607, excluding Verified500 and any historical diagnostic metadata identity match. No outcome-based selection.',
    prior_diagnostics_audited=True,holdout_scored=False)
save(V/'MANIFEST.json',manifest)
public=dict(created=manifest['created'],inventory_candidates=221,excluded_prior_diagnostic_identity=len(exposed),
    frozen_tasks=len(rows),frozen_families=len({t['family'] for t in rows}),manifest_SHA=sha(V/'MANIFEST.json'),
    candidate_freeze_SHA=manifest['candidate_freeze_SHA'],plan_SHA=manifest['plan_SHA'],audited_metadata=receipts,
    catalogs_not_counted_as_exposure=catalogs,selector='flow_expand',holdout_scored=False,
    limitations=['Independent from audited PI design/diagnostic examples, not an untouched pretraining corpus.',
    'All tasks belong to the existing training dataset; metadata provenance catalogs were previously built.',
    'Exposure exclusion is conservative identity matching across recorded manifests; unrecorded external use is not provably absent.'])
save(N/'reports/CONFIRMATION_EXPOSURE_FREEZE_R4.json',public)
print(json.dumps({k:v for k,v in public.items() if k not in {'audited_metadata','catalogs_not_counted_as_exposure'}},indent=2))
