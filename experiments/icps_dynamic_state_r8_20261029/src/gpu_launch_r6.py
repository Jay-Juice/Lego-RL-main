"""Bounded disposable launcher: existing reviewed evidence, no formal admission.

The human explicitly requested the eight-GPU short test without expanding
transitive dependency audits. Bind the already reviewed PI/native sources and
observed shared-module identities. Do not call this whole-dependency approval.
"""
import json
import os
from pathlib import Path
import sys
import time
from gpu_launch_gate_r6 import (B,N,R,require,file_sha,canonical_sha,collect_resources,
    validate_resources,digest_bytes,verify_manifest)
from gpu_launch_config_r6 import prepare
from gpu_offline_assets_r6 import collect,verify_exact

PINS = {'reports/GPU_PRIVATE_RAY_R6_LIVE_R2.json': '4488452c96c7f91e04655b60369937d36c77a5a67e4e73a358ac5782c60b0a0d', 'reports/GPU_NESTED_RAY_CONFIG_R6_CONTRACTS.json': 'f86b3b880c4d230bde421e8b60e3b2e29357feab1462a007cbc113613e6bde8c', 'reports/GPU_NATIVE_SOURCE_R6_REVIEW.json': '4ec2c71d9674d3c6e6f0a3d663430583106a0af8cb6ae47fc46aba66c597cab3', 'reports/GPU_NATIVE_INVENTORY_R6.json': 'aa92010a05ebfa656e30932bd44d732fa61ac80ebc52d2456f09bf1ab379836c', 'reports/GPU_RANK_AUDIT_R6_CONTRACTS.json': 'ef16bf8332f3d8a4c28fb6dee20663274de31991487d9268b03e535a19da5c05', 'reports/GPU_OFFLINE_ASSETS_R6_REVIEW.json': 'c506def4036fcedca8c44d338380f3923626aafc3a768dba2ede77ab04386e8c', 'reports/GPU_PROBE_R6_HYDRA_PARITY.json': '42d0c0e14303b644e74eef1603da798be63f71c56c928a9739b2fa6b44928208'}
PARENT=B/'experiments/icps_dynamic_state_v1_20261028'
PINS.update({'reports/DYNAMIC_QUALITY_R8.json': '238466bdd5859ea161c2fad8bb40fb02badc78482b408984cf0a7ea8fba02ff4', 'reports/CONTRACTS_R8.json': '3d86301cf6bc5c695d0e3ff31ef74133f06b17741a031e56dd487020bd9c5f99', 'reports/HARBOR_DYNAMIC_R8.json': '4849f9c07bdc208ed7f7f3ac6f30a2277d6358f9a73f69014094d3fc00eb2910'})
PYTHON_ROOT=Path('/home/ubuntu/.local/share/uv/python/cpython-3.12.3-linux-x86_64-gnu')

def verify_evidence(sources):
    for relative,digest in PINS.items():
        require(file_sha(N/relative)==digest, 'review evidence changed: '+relative)
    for p,h in json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())['source_SHA'].items():
        require(sources.get(str(N/p))==h, 'frozen source mismatch')
    for item in json.loads((N/'runtime/SOURCE_DIFF_RECEIPT.json').read_text()).values():
        require(sources.get(str(N/'runtime'/item['file']))==item['candidate_SHA'], 'overlay drift')
    live=json.loads((N/'reports/GPU_PRIVATE_RAY_R6_LIVE_R2.json').read_text())
    require(live['actual_Ray_started'] and live['Ray_shutdown_completed'] and
            live['owned_processes_remaining']==[], 'actual Ray evidence missing')
    require(file_sha(N/'src/gpu_private_ray_r6.py')==live['source_SHA']['src/gpu_private_ray_r6.py'], 'lease changed after actual test')
    rank=json.loads((N/'reports/GPU_RANK_AUDIT_R6_CONTRACTS.json').read_text())
    # Exact source identities are pinned independently below; CPU report is not GPU evidence.
    require(bool(rank), 'rank implementation evidence missing')
    for name,digest in {'src/gpu_rank_audit_r6.py':'ba22fd35f55025fa135d131a35c570173f2ab35b6cfee85d4a6b4bc68eb7f7cb','src/gpu_probe_workers_r6.py':'739124476c796c148d42d943a7255de47750742ff11e4253cade4303eb3bc7ca'}.items():
        require(file_sha(N/name)==digest,'rank implementation changed')

def sources_snapshot():
    inherited=json.loads((PARENT/'logs/gpu_native_inventory_r6/native_source_manifest.json').read_text())
    observed=json.loads((PARENT/'logs/gpu_native_inventory_r6/loaded_modules.json').read_text())
    sources={p:h for p,h in inherited.items() if not Path(p).is_relative_to(PARENT)}
    for row in observed.values():
        p=Path(row['path'])
        if not p.is_relative_to(N) and not p.is_relative_to(PARENT):sources[str(p)]=row['SHA']
    verify_manifest(sources,(R,B/'src',B/'third_party',B/'.venv',PYTHON_ROOT))
    for folder in ('runtime','src','core'):
        for p in (N/folder).rglob('*.py'):sources[str(p)]=file_sha(p)
    for p in (N/'ops/GPU_PROBE_R6.env',N/'ops/gpu_launch_r6.sh',N/'CANDIDATE_FREEZE_R6_SESSION.json',N/'runtime/SOURCE_DIFF_RECEIPT.json'):
        sources[str(p)]=file_sha(p)
    for relative in PINS:sources[str(N/relative)]=file_sha(N/relative)
    verify_evidence(sources)
    return sources

def write(run,name,value):
    with (run/name).open('x') as f:json.dump(value,f,indent=2,allow_nan=False)

def main():
    run=Path(os.environ['ICPS_FORMAL_RUN_DIR'])
    require(run.is_dir() and not (run/'launch_receipt.json').exists(),'new attempt required')
    config,parity=prepare(run)
    sources=sources_snapshot()
    prior=PARENT/'logs/gpu_offline_assets_r6_contracts_r2/offline_asset_manifest.json'
    require(canonical_sha(json.loads(prior.read_text()))=='850361941c94b02d7854e989684b4c1e299c8c69e1b3ef0fcdefa3970d24a3c9','asset identity receipt changed')
    assets,asset_info=collect(config)
    require(assets==json.loads(prior.read_text()),'offline assets changed')
    write(run,'source_manifest.json',sources)
    write(run,'offline_asset_manifest.json',assets)
    write(run,'prepared_config.json',config)
    write(run,'launch_scope.json',dict(source_scope='existing reviewed native/PI sources and observed shared dependencies',
        full_transitive_dependency_review=False,human_requested_bounded_disposable_probe=True,
        evidence_SHA=PINS,source_files=len(sources),assets=asset_info,parity=parity,
        formal_training_admitted=False))
    # Import the actual probe before issuing the fresh receipt; no model is constructed here.
    import gpu_probe_r6
    import ray,torch
    require(not ray.is_initialized(),'unexpected Ray instance')
    # Native import probes CUDA availability; resource checks below still require idle cards.
    write(run,'native_import.json',dict(CUDA_initialized=torch.cuda.is_initialized(),Ray_initialized=False,model_constructed=False))
    resources=collect_resources();validate_resources(resources,time.time())
    receipt=dict(schema='r6-disposable-launch-v1',purpose='disposable_native_sp8_probe',training_admission=False,
        created_at=time.time(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),run=str(run),
        config_SHA=canonical_sha(config),source_manifest_SHA=canonical_sha(sources),offline_asset_manifest_SHA=canonical_sha(assets),
        resources=resources,review=dict(existing_native_PI_evidence_verified=True,
        rank_audit_implementation_reviewed=True,private_ray_lifecycle_reviewed=True,hydra_both_phases_pass=True),
        evidence_SHA=PINS,full_transitive_dependency_review=False)
    write(run,'launch_receipt.json',receipt)
    os.environ['ICPS_R6_LAUNCH_RECEIPT_SHA']=file_sha(run/'launch_receipt.json')
    os.environ['ICPS_R8_GPU_APPROVED_LAUNCH']='1'
    from omegaconf import OmegaConf
    print('R8_GPU launching disposable native SP8 probe '+run.name,flush=True)
    gpu_probe_r6.main.__wrapped__(OmegaConf.create(config))
    require((run/'result.json').is_file(),'native result missing')
    require(not (run/'NEVER_SAVE_CHECKPOINT').exists(),'probe unexpectedly saved checkpoint')
    print('R8_GPU complete '+run.name,flush=True)

if __name__=='__main__':main()
