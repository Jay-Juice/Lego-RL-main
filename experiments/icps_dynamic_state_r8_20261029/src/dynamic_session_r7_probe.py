"""Probe-only R7 W0 / preserved R6 update composition. Not deployed runtime.

1024 initial,128 update,4096 episode. Retain the R6 transition/rollback/retry
implementation, replace only initial candidate builder, serializer and cap.
"""
from budget_ablation_r7 import clone_with_one_edit
from dynamic_session_r6_r2 import R6DynamicSessionR2, serialize_state as old_serialize
from recall_windows_r7_r2 import build
from entity_evidence_r7 import serialize, MeteredCache


def initial(snapshot, issue, *, task_uid, session_id):
    pools, _ = build(snapshot, issue, task_uid=task_uid, session_id=session_id, baseline=[])
    return {'focus': pools['passage24']}


def serialize_state(candidates, snapshot, issue, tokenizer, *, budget, delta, variant, facts, status):
    if status == 'initial' and not delta and not facts:
        if budget != 1024:
            raise ValueError('R7 probe initial budget must be1024')
        return serialize(candidates, snapshot, issue, MeteredCache(tokenizer), arm='cached1024_8')
    return old_serialize(candidates, snapshot, issue, tokenizer, budget=budget,
                         delta=delta, variant=variant, facts=facts, status=status)


class R7DynamicProbe(R6DynamicSessionR2):
    capture = clone_with_one_edit(R6DynamicSessionR2.capture,
        '192 if first else 128', '1024 if first else 128',
        {'build_initial_index': initial, 'serialize_state': serialize_state})
