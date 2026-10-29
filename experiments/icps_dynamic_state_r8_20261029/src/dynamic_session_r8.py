"""Independent R8: unchanged R7 W0, source-only changed-unit updates."""
from budget_ablation_r7 import clone_with_one_edit
from dynamic_session_r6_r2 import R6DynamicSessionR2
from dynamic_session_r7_probe import initial, serialize_state as initial_serializer
from changed_units_r8 import serialize


def dispatch(candidates,snapshot,issue,tokenizer,*,budget,delta,variant,facts,status):
    if status=='initial':
        return initial_serializer(candidates,snapshot,issue,tokenizer,budget=budget,
            delta=delta,variant=variant,facts=facts,status=status)
    return serialize(snapshot,delta,issue,tokenizer,budget=budget,facts=facts)


class R8DynamicSession(R6DynamicSessionR2):
    capture=clone_with_one_edit(R6DynamicSessionR2.capture,
        '192 if first else 128','1024 if first else 128',
        {'build_initial_index':initial,'serialize_state':dispatch,
         'dynamic_candidates':lambda initial,snapshot,delta,issue:[]})
