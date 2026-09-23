"""Qwen3.5 dense value head for PPO/SAO critics.

HuggingFace and VeOmni currently ship sequence-classification and generation
heads for Qwen3.5, but no per-token ``ForTokenClassification`` model.  A value
critic needs one scalar for every token, so mirror
``Qwen3_5ForConditionalGeneration`` with the language-model head replaced by a
linear score head.

The body comes from VeOmni's patched Qwen3.5 modeling rather than stock
Transformers.  Qwen3.5 contains GatedDeltaNet layers, and the VeOmni patches are
what bind the varlen/sequence-parallel kernels used by the training engine.
"""

from __future__ import annotations

import sys
from typing import Any

import torch
from torch import nn
from transformers.modeling_outputs import TokenClassifierOutput
from transformers.utils import can_return_tuple

try:
    from veomni.utils.device import IS_NPU_AVAILABLE
except Exception:  # pragma: no cover - veomni missing in utility-only processes
    IS_NPU_AVAILABLE = False

if IS_NPU_AVAILABLE:
    from veomni.models.transformers.qwen3_5.generated.patched_modeling_qwen3_5_npu import (
        Qwen3_5Model,
        Qwen3_5PreTrainedModel,
    )
else:
    from veomni.models.transformers.qwen3_5.generated.patched_modeling_qwen3_5_gpu import (
        Qwen3_5Model,
        Qwen3_5PreTrainedModel,
    )

# VeOmni binds kernels by scanning the module that defines the selected model
# class.  Re-export the patched modeling module's shared OpSlot objects here so
# the sidecar receives the same bindings as the generation model.
from veomni.ops.dispatch import OpSlot as _OpSlot

_modeling_module = sys.modules[Qwen3_5Model.__module__]
_op_slot_names = [
    name
    for name in dir(_modeling_module)
    if isinstance(getattr(_modeling_module, name, None), _OpSlot)
]
if not _op_slot_names:
    raise ImportError(
        f"No OpSlot instances found in {Qwen3_5Model.__module__}; "
        "the dense Qwen3.5 critic would be built without VeOmni kernels."
    )
for _name in _op_slot_names:
    globals()[_name] = getattr(_modeling_module, _name)


class Qwen3_5ForTokenClassification(Qwen3_5PreTrainedModel):
    """Per-token scalar value model for dense Qwen3.5 checkpoints."""

    _keys_to_ignore_on_load_unexpected = [r"^lm_head.*", r"^mtp.*"]
    accepts_loss_kwargs = False
    _no_split_modules = ["Qwen3_5DecoderLayer", "Qwen3_5VisionBlock"]

    def __init__(self, config):
        super().__init__(config)
        self.num_labels = int(getattr(config, "num_labels", 1) or 1)
        self.model = Qwen3_5Model(config)
        # SWE-bench trajectories are text-only and the vision tower is frozen for
        # the critic.  VeOmni normally runs a dummy ViT forward whenever FSDP is
        # enabled, even when every rank has no image/video.  Mark this value model
        # so the companion site-packages patch can skip that unnecessary path.
        # Keeping the full multimodal body preserves checkpoint names and FSDP
        # wrapping; only the no-media dummy computation is bypassed.
        self.model._skip_vision_dummy_forward = True
        text_config = getattr(config, "text_config", None)
        hidden_size = (
            text_config.hidden_size if text_config is not None else config.hidden_size
        )
        dropout = getattr(config, "classifier_dropout", None)
        if dropout is None:
            dropout = getattr(config, "hidden_dropout", 0.0) or 0.0
        try:
            dropout = float(dropout)
        except (TypeError, ValueError):
            dropout = 0.0
        self.dropout = nn.Dropout(dropout)
        self.score = nn.Linear(hidden_size, self.num_labels)
        self.post_init()

    def get_input_embeddings(self):
        return self.model.get_input_embeddings()

    def set_input_embeddings(self, value):
        self.model.set_input_embeddings(value)

    @can_return_tuple
    def forward(
        self,
        input_ids: torch.LongTensor | None = None,
        attention_mask: torch.Tensor | None = None,
        position_ids: torch.LongTensor | None = None,
        past_key_values: Any = None,
        inputs_embeds: torch.FloatTensor | None = None,
        labels: torch.LongTensor | None = None,
        use_cache: bool | None = None,
        **kwargs,
    ) -> TokenClassifierOutput:
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            **kwargs,
        )
        sequence_output = self.dropout(outputs.last_hidden_state)
        logits = self.score(sequence_output)
        loss = None
        if labels is not None and hasattr(self, "loss_function"):
            loss = self.loss_function(logits, labels, self.config)
        return TokenClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=getattr(outputs, "hidden_states", None),
            attentions=getattr(outputs, "attentions", None),
        )


def register_qwen3_5_token_classification() -> None:
    """Register the dense Qwen3.5 critic with the HF AutoModel mapping."""

    try:
        from transformers import AutoModelForTokenClassification
        from transformers.models.qwen3_5.configuration_qwen3_5 import Qwen3_5Config
    except Exception:
        return

    AutoModelForTokenClassification.register(
        Qwen3_5Config, Qwen3_5ForTokenClassification, exist_ok=True
    )


register_qwen3_5_token_classification()
