"""Development-only calibrated window relevance; pure issue/current-source inputs.

Same candidates, seeds, exact token costs, diversity, expansion and source maps.
No learned parameters, labels, IO or runtime mutation. RRF is a heuristic.
"""
import collections
import inspect
import math
import textwrap
from window_research_r7 import serialize as original
from window_serializer import terms, query
from dense_state import proposals


def relevance(props, issue):
    q, explicit = query(issue)
    # Each seed is a document. Duplicate overlapping seeds affect IDF equally
    # for all arms; this is lexical calibration, not semantic understanding.
    docs = [collections.Counter(t for line in w['code'].splitlines() for t in terms(line)) for w in props]
    df = collections.Counter(t for doc in docs for t in doc)
    avg = sum(sum(doc.values()) for doc in docs) / max(1, len(docs))
    scores = []
    for w, doc in zip(props, docs):
        length = sum(doc.values()); score = 0.0
        for term in sorted(q):
            tf = doc[term]
            if tf:
                idf = math.log(1 + (len(docs) - df[term] + .5) / (df[term] + .5))
                score += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / max(1, avg)))
        # Weak identity context, with most weight on actual rendered source.
        score += .25 * len(terms(w['file'] + ' ' + w['qualified']) & q)
        scores.append(score)
    return scores


def serialize(candidates, snapshot, issue, tokenizer, *, budget=256, variant='fused'):
    if budget not in (256, 384) or variant not in ('fused', 'anchored'):
        raise ValueError('predeclared relevance arms only')
    props = proposals(candidates, snapshot, issue, variant='flow_expand')
    lexical = relevance(props, issue)
    native_order = sorted(range(len(props)), key=lambda i: (-props[i]['score']/math.sqrt(1+props[i]['rank']), i))
    lexical_order = sorted(range(len(props)), key=lambda i: (-lexical[i], i))
    native_rank = {i:r for r,i in enumerate(native_order)}
    lexical_rank = {i:r for r,i in enumerate(lexical_order)}
    lookup = {(w['entity_id'],w['start'],w['end']):i for i,w in enumerate(props)}
    def adjusted(w, chosen):
        if variant == 'anchored' and not chosen:
            return w['score']
        i = lookup[(w['entity_id'],w['start'],w['end'])]
        # 2:1 native/relevance fusion, rank constant20. Cancel the downstream
        # candidate rank factor, already represented in native_rank.
        return (2/(20+native_rank[i]+1) + 1/(20+lexical_rank[i]+1))*math.sqrt(1+w['rank'])
    source = textwrap.dedent(inspect.getsource(original))
    edits = {
        'not budget == 256': 'budget not in (256,384)',
        "props = proposals(candidates, snapshot, issue, variant='flow_expand')": 'props = fixed_props',
        "marginal_score(w['score'],features,seen,trial_cost-prior_cost,variant)": 'marginal_score(adjusted(w,chosen),features,seen,trial_cost-prior_cost,variant)',
    }
    for before, after in edits.items():
        assert source.count(before)==1, 'reference changed'
        source=source.replace(before,after)
    namespace=dict(original.__globals__, fixed_props=props, adjusted=adjusted)
    exec(compile(source, '<R7-relevance-only>', 'exec'), namespace)
    return namespace['serialize'](candidates,snapshot,issue,tokenizer,budget=budget,variant='diverse6')
