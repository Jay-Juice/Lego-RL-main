"""CPU import/source inventory, never construct a model or approve a launch."""
import importlib
import inspect
import json
from pathlib import Path
import sys

N = Path(__file__).resolve().parents[1]
B = N.parents[1]
R = B/'experiments/pi_repair_state_v2_20261015'
F = B/'experiments/icps_v11_full97_sao_20261024_r2'
from gpu_launch_gate_r6 import file_sha, canonical_sha

queue = N/'logs/gpu_native_inventory_r6'
modules = ['verl.trainer.main_ppo', 'verl.workers.engine_workers',
    'verl.workers.engine.veomni.transformer_impl', 'verl.workers.utils.losses',
    'verl.trainer.ppo.core_algos', 'verl.trainer.ppo.reward',
    'verl.trainer.ppo.trajectory_filter', 'verl_patch.models.qwen3_5_token_classification']
for name in modules:
    importlib.import_module(name)
from verl_patch.models import qwen3_5_token_classification as head
from transformers import AutoModelForTokenClassification
from transformers.models.qwen3_5.configuration_qwen3_5 import Qwen3_5Config
import torch
import ray
assert not torch.cuda.is_initialized() and not ray.is_initialized()
assert AutoModelForTokenClassification._model_mapping[Qwen3_5Config] is head.Qwen3_5ForTokenClassification
assert Path(inspect.getfile(head)).resolve() == R/'src/verl_patch/models/qwen3_5_token_classification.py'
assert file_sha(Path(inspect.getfile(head))) == file_sha(B/'src/verl_patch/models/qwen3_5_token_classification.py')
body = sys.modules[head.Qwen3_5Model.__module__]
slot_names = head._op_slot_names
assert slot_names and all(getattr(head, k) is getattr(body, k) for k in slot_names)
head_origins = []
for cls in (head.Qwen3_5ForTokenClassification, head.Qwen3_5Model, head.Qwen3_5PreTrainedModel):
    path = Path(inspect.getfile(cls)).resolve()
    head_origins.append(dict(class_name=cls.__name__, module=cls.__module__,
        source=str(path), SHA=file_sha(path)))

# Every Python/YAML file under the native source roots is compared, including
# files not loaded by the CPU import. Differences are recorded, not excused.
trees = []
native_manifest = {}
for relative in ('src', 'third_party/verl/verl', 'third_party/harbor/src'):
    current, baseline = R/relative, B/relative
    assert current.is_dir() and baseline.is_dir(), relative
    def inventory(root):
        return {str(p.relative_to(root)): file_sha(p) for p in sorted(root.rglob('*'))
                if p.is_file() and p.suffix in ('.py', '.yaml', '.yml') and '__pycache__' not in p.parts}
    a, b = inventory(current), inventory(baseline)
    changes = [dict(relative=p, inherited_SHA=a.get(p), SAO_SHA=b.get(p))
               for p in sorted(a.keys() | b.keys()) if a.get(p) != b.get(p)]
    trees.append(dict(root=relative, inherited_files=len(a), SAO_files=len(b),
        equal_files=sum(a[p] == b.get(p) for p in a), differences=changes,
        inherited_tree_SHA=canonical_sha(a), SAO_tree_SHA=canonical_sha(b)))
    native_manifest.update({str(current/p):h for p,h in a.items()})

# Import closure is an observed lower bound. Lazy runtime/native libraries are
# not claimed covered by a CPU-only import trace.
loaded = {}
for name, module in list(sys.modules.items()):
    source = vars(module).get('__file__') if module is not None else None
    if not isinstance(source, str) or not source:
        continue
    path = Path(source).resolve()
    if path.is_file() and path.suffix in ('.py', '.so', '.pyd'):
        loaded[name] = dict(path=str(path), SHA=file_sha(path))
shared = B/'.venv/lib/python3.12/site-packages'
shared_roots = sorted({str(Path(v['path']).relative_to(shared).parts[0]) for v in loaded.values()
                       if Path(v['path']).is_relative_to(shared)})
overlay = json.loads((N/'runtime/SOURCE_DIFF_RECEIPT.json').read_text())
overlay_rows = []
for name, item in overlay.items():
    path = N/'runtime'/item['file']
    assert file_sha(path) == item['candidate_SHA'], name
    imported = sys.modules.get(name)
    if imported is not None:
        assert Path(inspect.getfile(imported)).resolve() == path
    overlay_rows.append(dict(module=name, path=str(path), SHA=file_sha(path),
                             observed_import=imported is not None))
for p,h in json.loads((N/'CANDIDATE_FREEZE_R6_SESSION.json').read_text())['source_SHA'].items():
    assert file_sha(N/p) == h
old = json.loads((N/'PROVENANCE.json').read_text())['source_files_SHA256']
for p,h in old.items():
    assert file_sha(F/p.replace('\\','/')) == h
for filename, data in [('native_source_manifest.json', native_manifest), ('loaded_modules.json', loaded)]:
    with (queue/filename).open('x') as out:
        json.dump(data, out, indent=2)
report = dict(status='NATIVE_SOURCE_INVENTORY_REVIEW_PENDING',
    head_mapping_is_native=True, head_class_origins=head_origins,
    shared_OpSlot_identity=True, OpSlot_names=slot_names,
    source_trees=trees, overlay_origins=overlay_rows,
    native_source_manifest_SHA=canonical_sha(native_manifest),
    loaded_modules_SHA=canonical_sha(loaded), loaded_module_count=len(loaded),
    observed_shared_top_level=shared_roots,
    shared_site_packages=str(shared), Python_executable=str(Path(sys.executable).resolve()),
    CPU_import_only=True, model_constructed=False, CUDA_initialized=False,
    Ray_initialized=False, optimizer_steps=0, source_review_complete=False,
    production_receipt_created=False, training_admitted=False,
    frozen_sources_exact=7, old_sources_exact=len(old),
    source_SHA={p:file_sha(N/p) for p in ['validation/gpu_native_inventory_r6.py',
                                        'ops/gpu_native_inventory_r6.sh']},
    limitations=['Imports and exact tree comparison do not approve unexplained changes.',
      'CPU import closure is a lower bound: lazy/native runtime dependencies still need manifest coverage.',
      'Native head registration/class origins/OpSlot identity inspected without model construction.',
      'Installed shared dependencies are read-only and used by both recipes; historical binary identity not inferred.',
      'No source-review approval, launch receipt, Ray instance, GPU or optimizer update.'])
with (N/'reports/GPU_NATIVE_INVENTORY_R6.json').open('x') as out:
    json.dump(report, out, indent=2, allow_nan=False)
print(json.dumps(dict(status=report['status'], imported=len(loaded),
    tree_differences=[dict(root=t['root'], files=t['inherited_files'], differences=len(t['differences'])) for t in trees])))
