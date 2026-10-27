"""Frozen R6 W0 selection composed with unchanged R4 session transitions.

No IO, global patches or training integration. Capture is copied from the frozen
R4 implementation, with only a local serializer dispatch. Parity is AST-tested.
"""
import copy
from dense_state import (validate, digest, build_initial_index, changes,
    dynamic_candidates, status_facts, serialize as r4_serialize)
from rank_windows_r6 import serialize as r6_serialize

def serialize_state(candidates,snapshot,issue,tokenizer,*,budget,delta,variant,facts,status):
    if variant != 'flow_expand': raise ValueError('frozen update variant')
    if status == 'initial' and not delta and not facts:
        return r6_serialize(candidates,snapshot,issue,tokenizer,
                            budget=budget,variant='novelty_cost_expand')
    return r4_serialize(candidates,snapshot,issue,tokenizer,budget=budget,
                        delta=delta,variant='flow_expand',facts=facts,status=status)

def session_semantic(out,snapshot,first,facts):
    # Normalize only the clean R6 W0 digest to the existing R4 lifecycle schema.
    # The frozen W0 serialized dictionary, text, IDs and budgets remain intact.
    if first and not facts:
        return digest([[(w['file'],w['qualified'],w['code'],w['unit'],w['syntax'])
                        for w in out['windows']],[],False,snapshot.get('limited',False)])
    return out['semantic_hash']

class R6DynamicSessionR2:
    """Bounded private pre-action cache. Never serialized into training records."""
    def __init__(self,issue,tokenizer,task_uid,session_id,variant='flow_expand'):
        if variant != 'flow_expand': raise ValueError('frozen update variant')
        self.issue=issue;self.tokenizer=tokenizer;self.identity=(task_uid,session_id);self.variant=variant
        self.initial=None;self.previous=None;self.remaining=4096;self.last=-1;self.seen=set();self.retry=None
        self.last_visible=None;self.exhausted=False
    def capture(self,snapshot,*,task_uid,session_id,logical_call_id,seq):
        validate(snapshot)
        if self.identity!=(task_uid,session_id):raise ValueError('cross-session')
        workspace=digest([snapshot['files'],snapshot.get('limited',False)])
        if self.retry and logical_call_id==self.retry[0]:
            if workspace!=self.retry[1]:raise ValueError('retry state changed')
            return copy.deepcopy(self.retry[2])
        if logical_call_id in self.seen or seq<=self.last:raise ValueError('nonmonotonic or late call')
        if len(self.seen)>=512:raise ValueError('logical call bound')
        first=self.initial is None
        if first:self.initial=build_initial_index(snapshot,self.issue,task_uid=task_uid,session_id=session_id)['focus']
        delta={} if first else changes(self.previous,snapshot['files'])
        candidates=self.initial if first else dynamic_candidates(self.initial,snapshot,delta,self.issue)
        facts=status_facts(self.initial,snapshot,delta)
        empty=dict(pi_text='',pi_ids=[],pi_raw_tokens=0,token_cap=0,source_map=[],windows=[],unknown=self.exhausted,omitted=self.exhausted,pi_truncated=self.exhausted)
        if self.exhausted or (not first and not delta and facts==getattr(self,'last_facts',None)):
            out=empty
        else:
            marker='[PI D1 exhausted current_state=unknown]\n';mids=self.tokenizer.encode(marker,add_special_tokens=False)
            if self.remaining<len(mids):raise ValueError('exhaustion reserve violated')
            budget=min(192 if first else 128,self.remaining-len(mids))
            minimum=len(self.tokenizer.encode('[PI D1 unknown no_window_fits]\n',add_special_tokens=False))
            if budget<minimum:
                out=dict(empty,pi_text=marker,pi_ids=mids,pi_raw_tokens=len(mids),unknown=True,omitted=True,pi_truncated=True)
                self.exhausted=True
            else:
                out=serialize_state(candidates,snapshot,self.issue,self.tokenizer,budget=budget,delta=delta,
                              variant=self.variant,facts=facts,status='initial' if first else 'current_change')
                visible=session_semantic(out,snapshot,first,facts)
                if visible==self.last_visible:out=empty
                else:self.last_visible=visible
            self.remaining-=len(out['pi_ids'])
        self.previous=dict(snapshot['files']);self.last_facts=facts;self.last=seq;self.seen.add(logical_call_id)
        key=digest([self.last_visible,self.exhausted])
        out.update(session_id=session_id,state_seq=seq,state_hash=key,pi_insertion_key=key,
                   pre_action=True,valid=True,pi_format='icps_dynamic_v1',logical_call_id=logical_call_id)
        self.retry=(logical_call_id,workspace,copy.deepcopy(out))
        return out
