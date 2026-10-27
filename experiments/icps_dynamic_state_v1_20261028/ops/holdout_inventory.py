"""Availability only. Does not score/open patch coordinates or select PI windows."""
import collections,hashlib,json,pathlib
B=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
N=B/'experiments/icps_dynamic_state_v1_20261028'
R=B/'experiments/pi_repair_state_v2_20261015'
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def family(task):return task.split('.')[0]
oldpath=R/'.private_location_pi_control_20261022/manifests/P0_FROZEN_607_MANIFEST.json'
datapath=B/'experiments/icps_v11_full97_sao_20261024_r2/preflight/FULL6248_DATA_IDENTITY.json'
locpath=R/'.private_oracle_pi_admission_followup_20261022_r2/LOCATION_SOURCE_V2.json'
old={x['task_id'] for x in read(oldpath)['rows']};assert len(old)==607
tasks=read(datapath)['tasks'];assert len(tasks)==6248
loc={x['instance_id']:x['confidence'] for x in read(locpath)['rows']}
evalroot=B/'data/swebench-verified';verified={p.parent.name for p in evalroot.rglob('task.toml')}
assert len(verified)==500,('verified identity unavailable',len(verified))
oldfamilies={family(t) for t in old}
available=[t for t in tasks if t['instance_id'] not in old|verified and loc.get(t['instance_id'])=='exact_hunk']
unseen=[t for t in available if family(t['instance_id']) not in oldfamilies]
out=dict(candidate_tasks=len(available),candidate_families=len({family(t['instance_id']) for t in available}),
         previously_unseen_families=len({family(t['instance_id']) for t in unseen}),tasks_in_unseen_families=len(unseen),
         by_family_sizes=sorted(collections.Counter(family(t['instance_id']) for t in available).values()),
         source_SHA={p.name:digest(p) for p in [oldpath,datapath,locpath]},verified_exclusion_count=len(verified),
         inputs_only_metadata=True,windows_generated=0,labels_scored=0,holdout_not_frozen_yet=True)
with (N/'reports/HOLDOUT_AVAILABILITY.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
