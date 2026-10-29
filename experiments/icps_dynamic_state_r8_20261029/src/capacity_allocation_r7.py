"""Development-only budget x slot intervention; no new relevance score.

Append mode retains all original256 windows exactly, including their context.
It chooses up to three additional windows with the original marginal utility.
New windows alone may expand. This is not a runtime budget/format change.
"""
import copy
import inspect
import textwrap
from budget_ablation_r7 import clone_with_one_edit
from joint_windows_r7 import budget_control
from window_research_r7 import serialize as original
import rank_windows_r6
import dense_state

ARMS = {
    'base256_3': (256, 3, False),
    'base384_3': (384, 3, False),
    'base512_3': (512, 3, False),
    'base768_3': (768, 3, False),
    'breadth384_6': (384, 6, False),
    'breadth512_6': (512, 6, False),
    'breadth768_6': (768, 6, False),
    'append512_6': (512, 6, True),
    'append768_6': (768, 6, True),
}


class TokenCache:
    """Exact real-tokenizer memoization, reset for each input task."""
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.cache = {}

    def encode(self, text, *, add_special_tokens=False):
        assert add_special_tokens is False
        if text not in self.cache:
            self.cache[text] = tuple(self.tokenizer.encode(text, add_special_tokens=False))
        return list(self.cache[text])

    def decode(self, ids, **kwargs):
        return self.tokenizer.decode(ids, **kwargs)


def serialize(candidates, snapshot, issue, tokenizer, *, arm):
    if arm not in ARMS:
        raise ValueError('predeclared development arm only')
    budget, slots, append = ARMS[arm]
    baseline = budget_control()(candidates, snapshot, issue, tokenizer,
                                budget=256, variant='diverse6') if append else None
    seed = copy.deepcopy(baseline['windows']) if append else []
    # Preserve the fallback's original algorithm while permitting diagnostic caps.
    fallback = clone_with_one_edit(dense_state.serialize, 'budget>192', 'budget>768')
    old_fallback = clone_with_one_edit(rank_windows_r6.serialize,
        'budget <= 192', 'budget <= 768', {'frozen_serialize': fallback})
    source = textwrap.dedent(inspect.getsource(original))
    edits = {
        'not budget == 256': 'budget not in (256,384,512,768)',
        'chosen = []': 'chosen = copy.deepcopy(initial)',
        'q, _ = query(issue); seen = set()':
            "q, _ = query(issue); seen = set().union(*(terms(w['code']) & q for w in chosen))",
        'while len(chosen) < 3:': 'while len(chosen) < slots:',
        'for i, w in enumerate(chosen):':
            'for i, w in enumerate(chosen):\n            if i < len(initial): continue',
    }
    for before, after in edits.items():
        assert source.count(before) == 1, 'reference source changed'
        source = source.replace(before, after)
    ns = dict(original.__globals__, initial=seed, slots=slots,
              experimental_serializer=lambda: old_fallback)
    exec(compile(source, '<R7-capacity-allocation>', 'exec'), ns)
    result = ns['serialize'](candidates, snapshot, issue, tokenizer,
                             budget=budget, variant='diverse6')
    if append:
        assert result['windows'][:len(seed)] == seed
        # With a nonempty original payload, appended rendering preserves bytes.
        if seed:
            assert result['pi_text'].startswith(baseline['pi_text'])
    return result
