"""Full-message proof for the two observed SDK aliases; no fuzzy matching."""
import copy
import unittest
from verl_patch.agent_loop import privileged_critic_builder as b

class ProvenAliasTests(unittest.TestCase):
    def pair(self, edit=False):
        args={'command':'str_replace','path':'/a','old_str':'x','new_str':'y'} if edit else {'command':'view','path':'/a','view_range':'[340, 380]'}
        old={'role':'assistant','content':'reason','tool_calls':[{'id':'unique','type':'function','function':{'name':'str_replace' if edit else 'file_editor','arguments':args}}]}
        new=copy.deepcopy(old)
        if edit:new['tool_calls'][0]['function']['name']='file_editor'
        else:new['tool_calls'][0]['function']['arguments']['view_range']=[340,380]
        return old,new
    def record(self,m):return {'message_key':b.message_key(m),'call_index':7,'state_hash':'original','pi_ids':[17,18],'pi_insertion_key':'capture-7','actor_response_start_abs':2,'actor_response_end_abs':3}
    def remap(self,old,new):
        records=[self.record(old)];saved=copy.deepcopy(records)
        out=b.remap_rebuilt_records(records,[(b.message_key(new),5,8)],old_messages=[new],new_messages=[new])
        self.assertEqual(records,saved)
        self.assertEqual(out[0]['pi_ids'],[17,18]);self.assertEqual(out[0]['call_index'],7)
        self.assertEqual(out[0]['pi_insertion_key'],'capture-7')
        return out
    def test_view_alias(self):self.remap(*self.pair())
    def test_editor_name_alias(self):self.remap(*self.pair(True))
    def test_unchanged_path_exact(self):
        old,_=self.pair();self.remap(old,copy.deepcopy(old))
    def test_mutations_fail_closed(self):
        for field in ('content','path','id','name','range','extra','type'):
            with self.subTest(field=field):
                old,new=self.pair();f=new['tool_calls'][0]
                if field=='content':new['content']='different'
                elif field=='path':f['function']['arguments']['path']='/b'
                elif field=='id':f['id']='other'
                elif field=='name':f['function']['name']='unknown'
                elif field=='range':f['function']['arguments']['view_range']=[341,380]
                elif field=='extra':new['unexpected']=1
                else:f['type']='unknown'
                with self.assertRaises(RuntimeError):self.remap(old,new)
    def test_duplicate_alias_ambiguous(self):
        old,new=self.pair()
        with self.assertRaises(RuntimeError):b.remap_rebuilt_records([self.record(old)],[(b.message_key(new),5,8)],old_messages=[new,new],new_messages=[new])
    def test_bool_range_not_integer(self):
        old,new=self.pair();old['tool_calls'][0]['function']['arguments']['view_range']='[true, 380]';new['tool_calls'][0]['function']['arguments']['view_range']=[True,380]
        with self.assertRaises(RuntimeError):self.remap(old,new)
    def test_order_and_count_unchanged(self):
        old,new=self.pair()
        for m in (old,new):
            m['tool_calls'].append({'id':'second','type':'function','function':{'name':'terminal','arguments':{'command':'pwd'}}})
        self.remap(old,new)
        new['tool_calls'].reverse()
        with self.assertRaises(RuntimeError):self.remap(old,new)
    def test_alias_search_bounded(self):
        old,new=self.pair()
        for m in (old,new):
            m['tool_calls']=[{**copy.deepcopy(m['tool_calls'][0]),'id':str(i)} for i in range(5)]
        with self.assertRaises(RuntimeError):self.remap(old,new)
if __name__=='__main__':unittest.main()
