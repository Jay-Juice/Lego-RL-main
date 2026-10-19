"""SDK alias composition must preserve the original ordered tool partition."""
import copy
import unittest
from verl_patch.agent_loop import privileged_critic_builder as b


class SplitAliasTests(unittest.TestCase):
    def case(self):
        old = {'role': 'assistant', 'content': 'reason', 'tool_calls': [
            {'id': 'first', 'type': 'function', 'function': {'name': 'terminal', 'arguments': {}}},
            {'id': 'second', 'type': 'function', 'function': {'name': 'command', 'arguments': {'command': 'printf ok'}}}]}
        parts = [dict(old, tool_calls=[copy.deepcopy(old['tool_calls'][0])]),
                 dict(old, content='', tool_calls=[copy.deepcopy(old['tool_calls'][1])])]
        parts[1]['tool_calls'][0]['function']['name'] = 'terminal'
        rec = {'message_key': b.message_key(old), 'call_index': 0, 'state_hash': 'same',
               'pi_insertion_key': 'capture', 'pi_ids': [7, 8], 'actor_response_start_abs': 1,
               'actor_response_end_abs': 3, 'logical_call_id': 'original'}
        return old, parts, rec

    def run_case(self, old, parts, rec):
        before = copy.deepcopy((old, parts, rec))
        result = b.remap_rebuilt_records([rec], [(b.message_key(m), 1+i, 2+i) for i,m in enumerate(parts)],
                                        old_messages=[old], new_messages=parts)
        self.assertEqual((old, parts, rec), before)
        return result

    def test_split_alias_preserves_causal_pi_and_single_insertion(self):
        old, parts, rec = self.case()
        out = self.run_case(old, parts, rec)
        self.assertEqual([r['call_index'] for r in out], [0, 0])
        self.assertEqual([r['logical_call_id'] for r in out], ['original', 'original'])
        self.assertEqual([r['pi_ids'] for r in out], [[7,8], [7,8]])
        self.assertEqual(b.interleave([10,11,12], 1, [1,1], out), ([10,7,8,11,12], [2,3], [0,1,1,0,0]))

    def test_reject_mutated_fields(self):
        for field in ('content','command','id','name','extra','type'):
            old, parts, rec = self.case()
            p = parts[1];t = p['tool_calls'][0]
            if field == 'content': p['content'] = 'later reasoning'
            elif field == 'command': t['function']['arguments']['command'] = 'different'
            elif field == 'id': t['id'] = 'different'
            elif field == 'name': t['function']['name'] = 'unknown'
            elif field == 'extra': t['function']['arguments']['extra'] = 1
            else: t['type'] = 'different'
            with self.subTest(field=field), self.assertRaises(RuntimeError): self.run_case(old,parts,rec)

    def test_reject_first_content_change(self):
        old,parts,rec = self.case();parts[0]['content'] += 'changed'
        with self.assertRaises(RuntimeError):self.run_case(old,parts,rec)

    def test_reject_missing_fragment(self):
        old,parts,rec = self.case()
        with self.assertRaises(RuntimeError):self.run_case(old,parts[:1],rec)

    def test_reject_reordered_fragments(self):
        old,parts,rec = self.case()
        with self.assertRaises(RuntimeError):self.run_case(old,parts[::-1],rec)

    def test_reject_duplicate_partition(self):
        old,parts,rec = self.case()
        with self.assertRaises(RuntimeError):self.run_case(old,parts+copy.deepcopy(parts),rec)

    def test_reject_duplicate_original_ids(self):
        old,parts,rec = self.case();old['tool_calls'][1]['id']='first';parts[1]['tool_calls'][0]['id']='first';rec['message_key']=b.message_key(old)
        with self.assertRaises(RuntimeError):self.run_case(old,parts,rec)

    def test_reject_unproven_original_hash(self):
        old,parts,rec = self.case();rec['message_key']='wrong'
        with self.assertRaises(RuntimeError):self.run_case(old,parts,rec)

    def test_alias_without_split_uses_full_hash(self):
        old,parts,rec = self.case();new=copy.deepcopy(old);new['tool_calls'][1]['function']['name']='terminal'
        out=b.remap_rebuilt_records([rec],[(b.message_key(new),1,3)],old_messages=[new],new_messages=[new])
        self.assertEqual(out[0]['pi_ids'],rec['pi_ids'])
        new['content']='changed'
        with self.assertRaises(RuntimeError):b.remap_rebuilt_records([rec],[(b.message_key(new),1,3)],old_messages=[new],new_messages=[new])

    def test_compose_editor_alias_and_split(self):
        old,parts,rec = self.case()
        old['tool_calls'][1]['function']={'name':'str_replace','arguments':{'path':'/a','old_str':'x','new_str':'y'}}
        parts[1]['tool_calls'][0]['function']={'name':'file_editor','arguments':{'command':'str_replace','path':'/a','old_str':'x','new_str':'y'}}
        rec['message_key']=b.message_key(old)
        self.assertEqual(len(self.run_case(old,parts,rec)),2)


if __name__ == '__main__':unittest.main()
