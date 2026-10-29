"""Full-body passage retrieval experiment. Source/issue only; no target IO."""
import collections
import copy
import math
import issue_program_state as index
from budget_ablation_r7 import clone_with_one_edit
from candidate_research_r7 import header_order


def passage_order(entities, issue):
    """Max BM25 over 128-word passages, stride64, plus entity header.

    Full entity text is scanned, including the tail beyond8192characters.
    These are retrieval documents only; emitted windows remain real source.
    Only query term counts and document lengths are retained in memory.
    """
    q=set(index.words(issue)); docs=[]
    if not q:return []
    for e in entities:
        heading=index.words(e['file']+' '+e['qualified']+' '+e['signature'])
        body=index.words(e['source'])
        for start in range(0,max(1,len(body)),64):
            words=heading+body[start:start+128]
            count=collections.Counter(t for t in words if t in q)
            docs.append((e['entity_id'],len(words),count))
            if start+128>=len(body):break
    # df is number of documents containing a term, not term frequency.
    df=collections.Counter(t for _,_,counts in docs for t in counts)
    average=sum(length for _,length,_ in docs)/max(1,len(docs));scores={}
    for eid,length,counts in docs:
        value=sum(math.log(1+(len(docs)-df[t]+.5)/(df[t]+.5))*tf*2.2/
                  (tf+1.2*(.25+.75*length/max(1,average))) for t,tf in counts.items())
        if value>0:scores[eid]=max(scores.get(eid,0),value)
    byid={e['entity_id']:e for e in entities}
    return [byid[eid] for eid in sorted(scores,key=lambda eid:(-scores[eid],index.digest([byid[eid]['file'],byid[eid]['qualified']])))]


def build(snapshot, issue, *, task_uid, session_id):
    parsed={}
    def parse(path,source):
        if path not in parsed:parsed[path]=index.parse_file(path,source)
        return parsed[path]
    builder=clone_with_one_edit(index.build_initial_index,'selected=ranked[:3]',
        'selected=ranked',{'parse_file':parse,'extract_current_impact':lambda *a,**k:{}})
    original=builder(snapshot,issue,task_uid=task_uid,session_id=session_id)
    ranked=original['focus']; entities=[e for es in parsed.values() for e in es if not e.get('ambiguous')]
    byid={e['entity_id']:e for e in entities}
    headers=header_order(entities,issue);passages=passage_order(entities,issue)
    def fused(channels,anchors):
        scores=collections.Counter()
        for channel in channels:
            for i,e in enumerate(channel):scores[e['entity_id']]+=1/(60+i+1)
        order=sorted(scores,key=lambda eid:(-scores[eid],index.digest([byid[eid]['file'],byid[eid]['qualified']])))
        result=list(ranked[:3]) if anchors else [];used={e['entity_id'] for e in result}
        result.extend(byid[eid] for eid in order if eid not in used)
        return result
    symbols=fused([ranked,headers],True);passage=fused([ranked,headers,passages],True)
    free=fused([ranked,headers,passages],False)
    pools={'symbols12':symbols[:12],'symbols24':symbols[:24],'passage24':passage[:24],'free24':free[:24]}
    ranks={name:{e['entity_id']:i+1 for i,e in enumerate(seq)} for name,seq in
           [('original',ranked),('symbols',symbols),('passage',passage),('free',free)]}
    inventory=[]
    for e in entities:
        # Coordinates are source-derived and frozen before any label access.
        inventory.append(dict(entity_id=e['entity_id'],file=e['file'],start=e['start_line'],end=e['end_line'],
            ranks={name:rank.get(e['entity_id']) for name,rank in ranks.items()}))
    return copy.deepcopy(pools),inventory
