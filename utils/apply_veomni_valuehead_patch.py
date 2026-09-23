#!/usr/bin/env python3
"""Make VeOmni able to build a value model (critic) at all.

veomni is installed from a wheel (requirements.txt), not a managed checkout, so
this edits site-packages and is LOST on every `pip install`/venv rebuild/machine
switch. scripts/setup_env.sh runs it once after installing, and
scripts/train/train.sh re-runs it before any CRITIC_ENABLE=True veomni launch. The optional verl half patches ONLY the
`VeOmniEngineWithValueHead` module that `import verl` resolves to (or an explicit
`VERL_TRANSFORMER_IMPL` / `VERL_DIR`). It will not walk a hardcoded checkout, and a
missing verl is a warning, not a failed launch -- worker nodes often have veomni
but not a verl tree. Run after any veomni (re)install before a critic.enable=True
config.

THE BUG. verl's VeOmniEngineWithValueHead does the right thing: it rewrites the HF
config to `architectures=["Qwen3MoeForTokenClassification"]`, num_labels=1, dropout 0
(verl/workers/engine/veomni/transformer_impl.py:1029-1047). VeOmni then resolves that
name through `MODELING_REGISTRY[model_type](arch_name)` (veomni/models/loader.py:142),
and the per-family registration function dispatched on substrings:

    if   "ForCausalLM"          in architecture: return Qwen3MoeForCausalLM
    elif "ForQuestionAnswering" in architecture: return Qwen3MoeForQuestionAnswering
    elif "Model"                in architecture: return Qwen3MoeModel
    else:                                        return Qwen3MoeForCausalLM

"Qwen3MoeForTokenClassification" matches NONE of the three -- note "Moe" is not
"Model" -- so it fell through to the else and the critic was silently built as a
LANGUAGE MODEL. No error, no warning. The class Qwen3MoeForTokenClassification exists
and is exported by the same patched module; it was simply never imported here.

HOW IT SURFACED. 3-node SAO smoke, 2026-08-11 11:17, first training step:
    core_algos.py:306 in _gae
      delta = token_level_rewards[:, t] + gamma * nextvalues - values[:, t]
    RuntimeError: The size of tensor a (8) must match the size of tensor b (151936)
                  at non-singleton dimension 1
151936 is Qwen3's vocab size: the "values" were lm_head logits. Had GAE happened to
broadcast, this would instead have been a run that trains happily on a garbage critic.

WHAT IT PATCHES:
  1. qwen3_moe/__init__.py -- add the ForTokenClassification import + dispatch branch,
     AND add the class to the _create_checkpoint_tensor_converter tuple. The second
     half is load-bearing and easy to miss: that converter carries the MoE expert
     tensor layout (keyed on config.num_experts), and the value model has the exact
     same MoE body as the CausalLM -- without it, Qwen3-30B-A3B expert weights load
     wrong into the critic.
  2. qwen3/__init__.py -- same dispatch fix for the dense family. No converter there.

Ordering follows veomni's own seed_oss/__init__.py, the one family upstream got right:
specific For* branches before the generic "Model" branch.

Qwen3.5 dense and MoE have no generated ForTokenClassification classes. This
script copies their sidecars from src/verl_patch/models/ next to each VeOmni
family and dispatches to them. It also patches VeOmniEngineWithValueHead so a
missing AutoModel mapping falls back to rewriting ForConditionalGeneration,
rather than raising (or, worse, building a language model).

Idempotent: skipped if the family already dispatches ForTokenClassification.
Run with `--check` to report status without writing.

Usage:
    python utils/apply_veomni_valuehead_patch.py            # apply
    python utils/apply_veomni_valuehead_patch.py --check    # report only
    python utils/apply_veomni_valuehead_patch.py --verify   # dispatch self-test only
"""

from __future__ import annotations

import os
import sys


def _veomni_dir() -> str:
    # Locate without importing: importing veomni registers the *unpatched*
    # per-family dispatch functions, and the in-process verify below would then
    # test stale module objects instead of the files we just rewrote.
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.find_spec("veomni")
    if spec is None or not spec.origin:
        sys.exit("[veomni-valuehead] cannot locate veomni (not installed in this interpreter)")
    return os.path.dirname(os.path.abspath(spec.origin))


QWEN3_MOE = "models/transformers/qwen3_moe/__init__.py"
QWEN3 = "models/transformers/qwen3/__init__.py"
QWEN3_5 = "models/transformers/qwen3_5/__init__.py"
QWEN3_5_SIDECAR = "models/transformers/qwen3_5/token_classification.py"
QWEN3_5_GPU_MODELING = "models/transformers/qwen3_5/generated/patched_modeling_qwen3_5_gpu.py"
QWEN3_5_NPU_MODELING = "models/transformers/qwen3_5/generated/patched_modeling_qwen3_5_npu.py"
QWEN3_5_MOE = "models/transformers/qwen3_5_moe/__init__.py"
QWEN3_5_MOE_SIDECAR = "models/transformers/qwen3_5_moe/token_classification.py"

_MOE_FIND = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_moe_npu import (
            Qwen3MoeForCausalLM,
            Qwen3MoeForQuestionAnswering,
            Qwen3MoeModel,
        )
    else:
        from .generated.patched_modeling_qwen3_moe_gpu import (
            Qwen3MoeForCausalLM,
            Qwen3MoeForQuestionAnswering,
            Qwen3MoeModel,
        )

    for model_cls in (Qwen3MoeForCausalLM, Qwen3MoeForQuestionAnswering, Qwen3MoeModel):
        model_cls._create_checkpoint_tensor_converter = staticmethod(create_qwen3_moe_checkpoint_tensor_converter)

    if "ForCausalLM" in architecture:
        return Qwen3MoeForCausalLM
    elif "ForQuestionAnswering" in architecture:
        return Qwen3MoeForQuestionAnswering
    elif "Model" in architecture:
        return Qwen3MoeModel
    else:
        return Qwen3MoeForCausalLM'''

_MOE_REPLACE = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_moe_npu import (
            Qwen3MoeForCausalLM,
            Qwen3MoeForQuestionAnswering,
            Qwen3MoeForTokenClassification,
            Qwen3MoeModel,
        )
    else:
        from .generated.patched_modeling_qwen3_moe_gpu import (
            Qwen3MoeForCausalLM,
            Qwen3MoeForQuestionAnswering,
            Qwen3MoeForTokenClassification,
            Qwen3MoeModel,
        )

    # Qwen3MoeForTokenClassification shares the MoE body, so it needs the expert-layout
    # converter exactly as much as the CausalLM does.
    for model_cls in (
        Qwen3MoeForCausalLM,
        Qwen3MoeForQuestionAnswering,
        Qwen3MoeForTokenClassification,
        Qwen3MoeModel,
    ):
        model_cls._create_checkpoint_tensor_converter = staticmethod(create_qwen3_moe_checkpoint_tensor_converter)

    if "ForCausalLM" in architecture:
        return Qwen3MoeForCausalLM
    elif "ForQuestionAnswering" in architecture:
        return Qwen3MoeForQuestionAnswering
    elif "ForTokenClassification" in architecture:
        return Qwen3MoeForTokenClassification
    elif "Model" in architecture:
        return Qwen3MoeModel
    else:
        return Qwen3MoeForCausalLM'''

_DENSE_FIND = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_npu import (
            Qwen3ForCausalLM,
            Qwen3ForSequenceClassification,
            Qwen3Model,
        )
    else:
        from .generated.patched_modeling_qwen3_gpu import (
            Qwen3ForCausalLM,
            Qwen3ForSequenceClassification,
            Qwen3Model,
        )

    if "ForCausalLM" in architecture:
        return Qwen3ForCausalLM
    elif "ForSequenceClassification" in architecture:
        return Qwen3ForSequenceClassification
    elif "Model" in architecture:
        return Qwen3Model
    else:
        return Qwen3ForCausalLM'''

_DENSE_REPLACE = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_npu import (
            Qwen3ForCausalLM,
            Qwen3ForSequenceClassification,
            Qwen3ForTokenClassification,
            Qwen3Model,
        )
    else:
        from .generated.patched_modeling_qwen3_gpu import (
            Qwen3ForCausalLM,
            Qwen3ForSequenceClassification,
            Qwen3ForTokenClassification,
            Qwen3Model,
        )

    if "ForCausalLM" in architecture:
        return Qwen3ForCausalLM
    elif "ForSequenceClassification" in architecture:
        return Qwen3ForSequenceClassification
    elif "ForTokenClassification" in architecture:
        return Qwen3ForTokenClassification
    elif "Model" in architecture:
        return Qwen3Model
    else:
        return Qwen3ForCausalLM'''

_Q35_DENSE_FIND = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_5_npu import Qwen3_5ForConditionalGeneration, Qwen3_5Model
    else:
        from .generated.patched_modeling_qwen3_5_gpu import Qwen3_5ForConditionalGeneration, Qwen3_5Model

    if "ForConditionalGeneration" in architecture:
        return Qwen3_5ForConditionalGeneration
    elif "Model" in architecture:
        return Qwen3_5Model
    else:
        return Qwen3_5ForConditionalGeneration'''

_Q35_DENSE_REPLACE = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_5_npu import Qwen3_5ForConditionalGeneration, Qwen3_5Model
    else:
        from .generated.patched_modeling_qwen3_5_gpu import Qwen3_5ForConditionalGeneration, Qwen3_5Model

    from .token_classification import Qwen3_5ForTokenClassification

    if "ForTokenClassification" in architecture:
        return Qwen3_5ForTokenClassification
    elif "ForConditionalGeneration" in architecture:
        return Qwen3_5ForConditionalGeneration
    elif "Model" in architecture:
        return Qwen3_5Model
    else:
        return Qwen3_5ForConditionalGeneration'''

_Q35_MOE_FIND = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_5_moe_npu import (
            Qwen3_5MoeForCausalLM,
            Qwen3_5MoeForConditionalGeneration,
        )
    else:
        from .generated.patched_modeling_qwen3_5_moe_gpu import (
            Qwen3_5MoeForCausalLM,
            Qwen3_5MoeForConditionalGeneration,
        )

    if "ForCausalLM" in architecture:
        return Qwen3_5MoeForCausalLM
    elif "ForConditionalGeneration" in architecture:
        return Qwen3_5MoeForConditionalGeneration
    else:
        return Qwen3_5MoeForCausalLM'''

_Q35_MOE_REPLACE = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_5_moe_npu import (
            Qwen3_5MoeForCausalLM,
            Qwen3_5MoeForConditionalGeneration,
        )
    else:
        from .generated.patched_modeling_qwen3_5_moe_gpu import (
            Qwen3_5MoeForCausalLM,
            Qwen3_5MoeForConditionalGeneration,
        )

    from .token_classification import Qwen3_5MoeForTokenClassification

    if "ForTokenClassification" in architecture:
        return Qwen3_5MoeForTokenClassification
    elif "ForCausalLM" in architecture:
        return Qwen3_5MoeForCausalLM
    elif "ForConditionalGeneration" in architecture:
        return Qwen3_5MoeForConditionalGeneration
    else:
        return Qwen3_5MoeForCausalLM'''

_Q35_TEXT_FIND = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_5_moe_npu import Qwen3_5MoeForCausalLM
    else:
        from .generated.patched_modeling_qwen3_5_moe_gpu import Qwen3_5MoeForCausalLM

    return Qwen3_5MoeForCausalLM'''

_Q35_TEXT_REPLACE = '''    if IS_NPU_AVAILABLE:
        from .generated.patched_modeling_qwen3_5_moe_npu import Qwen3_5MoeForCausalLM
    else:
        from .generated.patched_modeling_qwen3_5_moe_gpu import Qwen3_5MoeForCausalLM

    # qwen3_5_moe_text refuses TokenClassification (needs Qwen3_5MoeConfig)
    if "ForTokenClassification" in architecture:
        raise ValueError(
            "qwen3_5_moe_text has no value-head class; use model_type=qwen3_5_moe"
        )
    return Qwen3_5MoeForCausalLM'''

# Already-applied text-family dispatch from the first Qwen3.5 revision. Upgraded
# in place so a re-run does not keep returning the multimodal class for a
# text-only config (that class reads config.text_config and would AttributeError).
_Q35_TEXT_UPGRADE_FIND = '''    from .token_classification import Qwen3_5MoeForTokenClassification

    # qwen3_5_moe_text ForTokenClassification
    if "ForTokenClassification" in architecture:
        return Qwen3_5MoeForTokenClassification
    return Qwen3_5MoeForCausalLM'''

_VERL_FIND = '''        token_cls = AutoModelForTokenClassification._model_mapping.get(type(config), None)
        if token_cls is None:
            raise ValueError(f"No ForTokenClassification class in transformers for {type(config).__name__}.")
        config.architectures = [token_cls.__name__]
        return config'''

_VERL_REPLACE = '''        token_cls = AutoModelForTokenClassification._model_mapping.get(type(config), None)
        if token_cls is None:
            # Qwen3.5-MoE is ForConditionalGeneration and has no HF TokenClassification
            # mapping. Rewrite the suffix so VeOmni's MODELING_REGISTRY can dispatch
            # to the sidecar class instead of raising (or falling through to CausalLM).
            # A checkpoint that is already *ForTokenClassification (e.g. a merged
            # warm-start critic) passes through unchanged.
            arch = (getattr(config, "architectures", None) or [type(config).__name__])[0]
            if not arch.endswith("ForTokenClassification"):
                for suffix in ("ForConditionalGeneration", "ForCausalLM"):
                    if suffix in arch:
                        arch = arch.replace(suffix, "ForTokenClassification")
                        break
                else:
                    raise ValueError(
                        f"No ForTokenClassification class in transformers for {type(config).__name__}."
                    )
            config.architectures = [arch]
            return config
        config.architectures = [token_cls.__name__]
        return config'''

_VERL_NESTED_FIND = '''            elif isinstance(tensor, torch.Tensor) and tensor.is_nested:
                tensor_lst = tensor.unbind()  # for performance
                selected_tensors = [tensor_lst[idx] for idx in indices]
                data_dict[key] = nested_tensor_from_tensor_list(
                    selected_tensors, ragged_idx=getattr(tensor, "_ragged_idx", tensor.dim() - 1)
                )'''

_VERL_NESTED_REPLACE = '''            elif isinstance(tensor, torch.Tensor) and tensor.is_nested:
                # PyTorch unbind is broken for 3D+ jagged tensors whose ragged
                # dimension is not the first sample dimension (for example
                # Qwen3.5 mRoPE position_ids with per-sample shape [4, seq]).
                # Select rows directly from the packed values using offsets.
                # This works for both ordinary 2D NJTs and mRoPE NJTs and avoids
                # the split_with_sizes-on-the-wrong-dimension failure.
                ragged_idx = getattr(tensor, "_ragged_idx", tensor.dim() - 1)
                offsets = tensor.offsets()
                values = tensor.values()
                selected_tensors = []
                for idx in indices.tolist():
                    start = int(offsets[idx].item())
                    length = int((offsets[idx + 1] - offsets[idx]).item())
                    selected_tensors.append(values.narrow(ragged_idx - 1, start, length))
                data_dict[key] = nested_tensor_from_tensor_list(selected_tensors, ragged_idx=ragged_idx)'''

_Q35_VISION_DUMMY_FIND = "elif get_parallel_state().fsdp_enabled:"
_Q35_VISION_DUMMY_REPLACE_V1 = '''elif (
            get_parallel_state().fsdp_enabled
            and not getattr(self, "_skip_vision_dummy_forward", False)
        ):'''
_Q35_VISION_DUMMY_REPLACE_V2 = '''elif (
            get_parallel_state().fsdp_enabled
            and any(parameter.requires_grad for parameter in self.visual.parameters())
            and not getattr(self, "_skip_vision_dummy_forward", False)
        ):'''
_Q35_VISION_DUMMY_REPLACE = '''elif (
            get_parallel_state().fsdp_enabled
            and any(parameter.requires_grad for parameter in self.visual.parameters())
            and not getattr(self, "_skip_vision_dummy_forward", False)
            and __import__("os").environ.get("VEOMNI_QWEN35_TEXT_ONLY", "0").lower()
            not in ("1", "true", "yes", "on")
        ):'''

_VERL_NESTED_REPLACE_V1 = _VERL_NESTED_REPLACE
_VERL_NESTED_REPLACE = '''            elif isinstance(tensor, torch.Tensor) and tensor.is_nested:
                # PyTorch unbind is broken for 3D+ jagged tensors. Qwen3.5
                # mRoPE position_ids can also arrive in two valid packed layouts:
                # offsets may describe sequence lengths (values [4, sum_seq]) or,
                # for a single sample, the four coordinate channels themselves
                # (values [4, seq], offsets [0, 4]). Infer the packed storage
                # dimension from offsets instead of trusting the logical NJT dim.
                offsets = tensor.offsets()
                values = tensor.values()
                packed_size = int(offsets[-1].item())
                ragged_idx = getattr(tensor, "_ragged_idx", tensor.dim() - 1)
                storage_dim = ragged_idx - 1
                if storage_dim >= values.dim() or values.shape[storage_dim] != packed_size:
                    matching_dims = [dim for dim, size in enumerate(values.shape) if size == packed_size]
                    if len(matching_dims) != 1:
                        raise RuntimeError(
                            f"Cannot identify packed jagged dimension for key {key!r}: "
                            f"values_shape={tuple(values.shape)}, offsets_last={packed_size}, "
                            f"ragged_idx={ragged_idx}, matching_dims={matching_dims}"
                        )
                    storage_dim = matching_dims[0]
                    ragged_idx = storage_dim + 1
                selected_tensors = []
                for idx in indices.tolist():
                    start = int(offsets[idx].item())
                    length = int((offsets[idx + 1] - offsets[idx]).item())
                    selected_tensors.append(values.narrow(storage_dim, start, length))
                data_dict[key] = nested_tensor_from_tensor_list(selected_tensors, ragged_idx=ragged_idx)'''

# (name, marker, find, replace). marker -> already-applied detection.
# "ForTokenClassification" appears nowhere in either unpatched qwen3 file, so it is
# an unambiguous marker there. Qwen3.5 uses more specific markers because both
# register functions live in one file.
PATCHES: dict[str, list[tuple[str, str, str, str]]] = {
    QWEN3_MOE: [
        (
            "ForTokenClassification dispatch + expert-layout converter",
            "ForTokenClassification",
            _MOE_FIND,
            _MOE_REPLACE,
        ),
    ],
    QWEN3: [
        (
            "ForTokenClassification dispatch",
            "ForTokenClassification",
            _DENSE_FIND,
            _DENSE_REPLACE,
        ),
    ],
    QWEN3_5: [
        (
            "qwen3_5 dense ForTokenClassification dispatch",
            "return Qwen3_5ForTokenClassification",
            _Q35_DENSE_FIND,
            _Q35_DENSE_REPLACE,
        ),
    ],
    QWEN3_5_MOE: [
        (
            "qwen3_5_moe ForTokenClassification dispatch",
            "return Qwen3_5MoeForTokenClassification",
            _Q35_MOE_FIND,
            _Q35_MOE_REPLACE,
        ),
    ],
}


def _patch_q35_text_family(veomni_root: str, check_only: bool) -> int:
    """Keep qwen3_5_moe_text from returning the multimodal value-head class."""
    path = os.path.join(veomni_root, QWEN3_5_MOE)
    if not os.path.isfile(path):
        print(f"  [MISSING FILE] {QWEN3_5_MOE}")
        return 1
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "qwen3_5_moe_text refuses TokenClassification" in content:
        print(f"  [already]  {QWEN3_5_MOE} :: qwen3_5_moe_text refuses TokenClassification")
        return 0
    if _Q35_TEXT_UPGRADE_FIND in content:
        find = _Q35_TEXT_UPGRADE_FIND
    elif _Q35_TEXT_FIND in content:
        find = _Q35_TEXT_FIND
    else:
        print(f"  [!! NOT FOUND] {QWEN3_5_MOE} :: qwen3_5_moe_text TokenClassification guard")
        return 1
    print(f"  [{'WOULD' if check_only else 'APPLY'}]  {QWEN3_5_MOE} :: qwen3_5_moe_text refuses TokenClassification")
    if check_only:
        return 1
    content = content.replace(find, _Q35_TEXT_REPLACE, 1)
    tmp = f"{path}.vhtmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)
    return 0


def _patch_q35_text_only_vision_dummy(veomni_root: str, check_only: bool) -> int:
    """Let explicit text-only Qwen3.5 jobs skip VeOmni's ViT dummy forwards.

    Qwen3.5's multimodal wrapper contains one no-media FSDP dummy branch for
    images and another for videos.  The dense value-head sidecar keeps the full
    wrapper for checkpoint compatibility, but its SWE-bench inputs are text-only
    and its vision tower is frozen. Actor training uses the same wrapper, so the
    explicit VEOMNI_QWEN35_TEXT_ONLY switch covers both models. Both no-media
    branches therefore need the opt-out.
    """
    bad = 0
    marker = '_skip_vision_dummy_forward'
    for rel in (QWEN3_5_GPU_MODELING, QWEN3_5_NPU_MODELING):
        path = os.path.join(veomni_root, rel)
        if not os.path.isfile(path):
            print(f"  [MISSING FILE] {rel}")
            bad += 1
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        current_count = content.count(_Q35_VISION_DUMMY_REPLACE)
        if current_count == 2:
            print(f"  [already]  {rel} :: text-only Qwen3.5 skips ViT dummy forwards")
            continue
        old = None
        for candidate in (_Q35_VISION_DUMMY_REPLACE_V2, _Q35_VISION_DUMMY_REPLACE_V1):
            if content.count(candidate) == 2:
                old = candidate
                break
        if old is not None:
            print(f"  [{'WOULD UPGRADE' if check_only else 'UPGRADE'}]  {rel} :: explicit text-only ViT dummy guard")
            if check_only:
                bad += 1
                continue
            content = content.replace(old, _Q35_VISION_DUMMY_REPLACE)
            tmp = f"{path}.vhtmp.{os.getpid()}"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)
            continue
        marker_count = content.count(marker)
        if marker_count:
            print(f"  [!! PARTIAL] {rel} :: expected 2 ViT dummy guards, found {marker_count}")
            bad += 1
            continue
        find_count = content.count(_Q35_VISION_DUMMY_FIND)
        if find_count != 2:
            print(f"  [!! NOT FOUND] {rel} :: expected 2 unguarded ViT dummy branches, found {find_count}")
            bad += 1
            continue
        print(f"  [{'WOULD' if check_only else 'APPLY'}]  {rel} :: explicit text-only ViT dummy guard")
        if check_only:
            bad += 1
            continue
        content = content.replace(_Q35_VISION_DUMMY_FIND, _Q35_VISION_DUMMY_REPLACE)
        tmp = f"{path}.vhtmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    return bad


def _repo_sidecar_path() -> str:
    # utils/apply_veomni_valuehead_patch.py -> repo root
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "src/verl_patch/models/qwen3_5_moe_token_classification.py")


def _repo_dense_sidecar_path() -> str:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "src/verl_patch/models/qwen3_5_token_classification.py")


def _install_q35_dense_sidecar(veomni_root: str, check_only: bool) -> int:
    src = _repo_dense_sidecar_path()
    dst = os.path.join(veomni_root, QWEN3_5_SIDECAR)
    if not os.path.isfile(src):
        print(f"  [!! NOT FOUND] sidecar source {src}")
        return 1
    if os.path.isfile(dst) and open(dst, encoding="utf-8").read() == open(src, encoding="utf-8").read():
        print(f"  [already]  {QWEN3_5_SIDECAR}")
        return 0
    print(f"  [{'WOULD' if check_only else 'APPLY'}]  {QWEN3_5_SIDECAR}")
    if check_only:
        return 1
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = f"{dst}.vhtmp.{os.getpid()}"
    with open(src, encoding="utf-8") as f:
        content = f.read()
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, dst)
    return 0


def _install_q35_sidecar(veomni_root: str, check_only: bool) -> int:
    src = _repo_sidecar_path()
    dst = os.path.join(veomni_root, QWEN3_5_MOE_SIDECAR)
    if not os.path.isfile(src):
        print(f"  [!! NOT FOUND] sidecar source {src}")
        return 1
    if os.path.isfile(dst) and open(dst, encoding="utf-8").read() == open(src, encoding="utf-8").read():
        print(f"  [already]  {QWEN3_5_MOE_SIDECAR}")
        return 0
    print(f"  [{'WOULD' if check_only else 'APPLY'}]  {QWEN3_5_MOE_SIDECAR}")
    if check_only:
        return 1
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = f"{dst}.vhtmp.{os.getpid()}"
    with open(src, encoding="utf-8") as f:
        content = f.read()
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, dst)
    return 0


def _verl_transformer_impl_path() -> str | None:
    """Only the verl this process would actually import, plus explicit overrides.

    Do not fall back to a machine-local checkout: that can patch a tree the
    trainer never loads, while workers without that path would fail launch.
    """
    try:
        import verl.workers.engine.veomni.transformer_impl as impl  # noqa: PLC0415

        return os.path.abspath(impl.__file__)
    except Exception:
        pass
    explicit = os.environ.get("VERL_TRANSFORMER_IMPL", "")
    if explicit and os.path.isfile(explicit):
        return explicit
    verl_dir = os.environ.get("VERL_DIR", "")
    if verl_dir:
        candidate = os.path.join(verl_dir, "verl/workers/engine/veomni/transformer_impl.py")
        if os.path.isfile(candidate):
            return candidate
    return None


def _patch_verl_valuehead(check_only: bool) -> int:
    path = _verl_transformer_impl_path()
    if path is None:
        print(
            "  [skip] verl not importable -- not patching a checkout. "
            "Qwen3.5 critic needs the ForConditionalGeneration fallback in the "
            "verl the trainer imports; export PYTHONPATH/VERL_DIR if this process "
            "will be the one that builds the critic."
        )
        return 0
    rel = path
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "ForConditionalGeneration" in content and "No ForTokenClassification class" in content:
        # already has the fallback (the raise string remains as the else branch)
        if "for suffix in (\"ForConditionalGeneration\", \"ForCausalLM\")" in content:
            print(f"  [already]  {rel} :: ForConditionalGeneration value-head fallback")
            return 0
    if _VERL_FIND in content:
        print(f"  [{'WOULD' if check_only else 'APPLY'}]  {rel} :: ForConditionalGeneration value-head fallback")
        if check_only:
            return 1
        content = content.replace(_VERL_FIND, _VERL_REPLACE, 1)
        tmp = f"{path}.vhtmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
        return 0
    if "for suffix in (\"ForConditionalGeneration\", \"ForCausalLM\")" in content:
        print(f"  [already]  {rel} :: ForConditionalGeneration value-head fallback")
        return 0
    print(f"  [!! NOT FOUND] {rel} :: VeOmniEngineWithValueHead lookup (verl version mismatch?)")
    return 1


def _verl_tensordict_utils_path() -> str | None:
    try:
        import verl.utils.tensordict_utils as utils  # noqa: PLC0415

        return os.path.abspath(utils.__file__)
    except Exception:
        pass
    verl_dir = os.environ.get("VERL_DIR", "")
    if verl_dir:
        candidate = os.path.join(verl_dir, "verl/utils/tensordict_utils.py")
        if os.path.isfile(candidate):
            return candidate
    return None


def _patch_verl_nested_index_select(check_only: bool) -> int:
    """Avoid PyTorch's broken unbind for Qwen3.5 mRoPE jagged tensors."""
    path = _verl_tensordict_utils_path()
    if path is None:
        print("  [skip] verl not importable -- not patching nested-tensor row selection")
        return 0
    with open(path, encoding="utf-8") as f:
        content = f.read()
    marker = "packed_size = int(offsets[-1].item())"
    if marker in content:
        print(f"  [already]  {path} :: mRoPE jagged index_select")
        return 0
    if _VERL_NESTED_REPLACE_V1 in content:
        find = _VERL_NESTED_REPLACE_V1
    elif _VERL_NESTED_FIND in content:
        find = _VERL_NESTED_FIND
    else:
        print(f"  [!! NOT FOUND] {path} :: nested index_select (verl version mismatch?)")
        return 1
    print(f"  [{'WOULD' if check_only else 'APPLY'}]  {path} :: mRoPE jagged index_select")
    if check_only:
        return 1
    content = content.replace(find, _VERL_NESTED_REPLACE, 1)
    tmp = f"{path}.vhtmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)
    return 0


def _verify(root: str) -> int:
    """Import the registry and assert every architecture resolves to its own class.

    Substring dispatch is exactly the kind of thing that looks right and is not, so
    check the previously-working branches too, not just the new one.
    """
    try:
        from veomni.models.loader import MODELING_REGISTRY  # noqa: PLC0415
    except Exception as e:
        print(f"[veomni-valuehead] verify SKIPPED (cannot import registry: {e!r})")
        return 0

    cases = [
        ("qwen3_moe", "Qwen3MoeForTokenClassification"),
        ("qwen3_moe", "Qwen3MoeForCausalLM"),
        ("qwen3_moe", "Qwen3MoeForQuestionAnswering"),
        ("qwen3_moe", "Qwen3MoeModel"),
        ("qwen3", "Qwen3ForTokenClassification"),
        ("qwen3", "Qwen3ForCausalLM"),
        ("qwen3", "Qwen3ForSequenceClassification"),
        ("qwen3", "Qwen3Model"),
        ("qwen3_5", "Qwen3_5ForTokenClassification"),
        ("qwen3_5", "Qwen3_5ForConditionalGeneration"),
        ("qwen3_5", "Qwen3_5Model"),
        ("qwen3_5_moe", "Qwen3_5MoeForTokenClassification"),
        ("qwen3_5_moe", "Qwen3_5MoeForCausalLM"),
        ("qwen3_5_moe", "Qwen3_5MoeForConditionalGeneration"),
        ("qwen3_5_moe_text", "Qwen3_5MoeForCausalLM"),
    ]
    bad = 0
    for family, arch in cases:
        try:
            got = MODELING_REGISTRY[family](arch).__name__
        except Exception as e:
            print(f"  [ERROR] {family:10} {arch:32} -> {e!r}")
            bad += 1
            continue
        ok = got == arch
        bad += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {family:10} {arch:32} -> {got}")

    try:
        MODELING_REGISTRY["qwen3_5_moe_text"]("Qwen3_5MoeForTokenClassification")
        print("  [FAIL] qwen3_5_moe_text Qwen3_5MoeForTokenClassification should raise")
        bad += 1
    except ValueError:
        print("  [ok] qwen3_5_moe_text Qwen3_5MoeForTokenClassification raises")
    except Exception as e:
        print(f"  [ERROR] qwen3_5_moe_text Qwen3_5MoeForTokenClassification -> {e!r}")
        bad += 1

    try:
        from veomni.models.transformers.qwen3_moe.generated.patched_modeling_qwen3_moe_gpu import (  # noqa: PLC0415
            Qwen3MoeForTokenClassification,
        )

        has_conv = hasattr(Qwen3MoeForTokenClassification, "_create_checkpoint_tensor_converter")
        bad += not has_conv
        print(f"  [{'ok' if has_conv else 'FAIL'}] expert-layout converter attached to the MoE value head: {has_conv}")
    except Exception as e:
        print(f"  [ERROR] converter check: {e!r}")
        bad += 1

    try:
        import torch  # noqa: PLC0415
        from tensordict import TensorDict  # noqa: PLC0415
        from verl.utils.tensordict_utils import index_select_tensor_dict  # noqa: PLC0415

        rows = [torch.arange(12).reshape(4, 3), torch.arange(20).reshape(4, 5)]
        nt = torch.nested.nested_tensor_from_jagged(
            values=torch.cat(rows, dim=1), offsets=torch.tensor([0, 3, 8])
        )
        nt._ragged_idx = 2
        selected = index_select_tensor_dict(TensorDict({"position_ids": nt}, batch_size=[2]), [1, 0])
        got = selected["position_ids"]
        ok = tuple(got.values().shape) == (4, 8) and got.offsets().tolist() == [0, 5, 8]
        bad += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] verl mRoPE jagged index_select")

        single_row = torch.arange(24).reshape(4, 6)
        channel_ragged = torch.nested.as_nested_tensor([single_row], layout=torch.jagged)
        selected = index_select_tensor_dict(
            TensorDict({"position_ids": channel_ragged}, batch_size=[1]), [0]
        )["position_ids"]
        ok = tuple(selected.values().shape) == (4, 6) and selected.offsets().tolist() == [0, 4]
        bad += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] verl single-row mRoPE jagged index_select")
    except Exception as e:
        print(f"  [ERROR] verl mRoPE jagged index_select -> {e!r}")
        bad += 1
    return bad


def main() -> int:
    check_only = "--check" in sys.argv
    root = _veomni_dir()
    if "--verify" in sys.argv:
        # Fresh-interpreter verification entry point (see the apply path below).
        return 3 if _verify(root) else 0
    print(f"[veomni-valuehead] veomni at: {root}")
    total_applied = total_skipped = total_missing = 0
    total_missing += _install_q35_dense_sidecar(root, check_only)
    total_missing += _install_q35_sidecar(root, check_only)
    total_missing += _patch_q35_text_only_vision_dummy(root, check_only)
    verl_status = _patch_verl_valuehead(check_only)
    if verl_status:
        total_missing += verl_status
    nested_status = _patch_verl_nested_index_select(check_only)
    if nested_status:
        total_missing += nested_status

    for rel, patches in PATCHES.items():
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            print(f"  [MISSING FILE] {rel}")
            total_missing += len(patches)
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        changed = False
        for name, marker, find, replace in patches:
            if marker in content:
                print(f"  [already]  {rel} :: {name}")
                total_skipped += 1
            elif find in content:
                content = content.replace(find, replace, 1)
                changed = True
                total_applied += 1
                print(f"  [{'WOULD' if check_only else 'APPLY'}]  {rel} :: {name}")
            else:
                total_missing += 1
                print(f"  [!! NOT FOUND] {rel} :: {name} (veomni version mismatch? patch the find-string)")
        if changed and not check_only:
            # Atomic write, same reason as the R3 script: a shared venv can be patched
            # from several nodes at once and must never be observed half-written.
            tmp = f"{path}.vhtmp.{os.getpid()}"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)

    total_missing += _patch_q35_text_family(root, check_only)

    print(
        f"[veomni-valuehead] applied={total_applied} already={total_skipped} "
        f"not_found={total_missing}{' (check only)' if check_only else ''}"
    )
    if total_missing:
        print(
            "[veomni-valuehead] WARNING: some patches did not match -- a veomni critic "
            "will be silently built as a CausalLM. Update the find-strings in this script."
        )
        return 2

    if not check_only:
        # Verify in a fresh interpreter: the verl value-head patch step above may
        # already have imported veomni here, and MODELING_REGISTRY would keep the
        # pre-patch dispatch functions bound (false "FAIL" right after "[APPLY]").
        import subprocess  # noqa: PLC0415

        print("[veomni-valuehead] verifying dispatch (fresh interpreter):")
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--verify"], check=False).returncode
        if rc:
            print("[veomni-valuehead] VERIFY FAILED -- do not run a veomni critic.")
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
