"""Actual scorer interfaces: unavailable denominators and source mismatch."""
import pathlib
import sys
import unittest
R=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main/experiments/pi_repair_state_v2_20261015')
sys.path.insert(0,str(R/'ops/icps_bug_coverage_20261023'))
from coordinates import verify_hunks,measure
from evaluate import metrics,paired

class ConfirmationScoring(unittest.TestCase):
    def test_unavailable_kept_in_nominal_not_scored_as_failure(self):
        key='changed_visible_intersect_any'
        rows=[dict(grade='exact_hunk',family='a',metrics={'R0':{'192':{key:False}},'R1':{'192':{key:True}}}),
              dict(grade='exact_hunk',family='b',metrics={})]
        m=metrics(rows,'R1',192)[key]
        self.assertEqual((m['hits'],m['n_evaluable'],m['n_total']),(1,1,2))
        self.assertEqual(m['strict_verified_hit_lower_bound'],.5)
        self.assertEqual(paired(rows,192,key)['n'],1)
    def test_exact_old_side_anchor_and_mismatch(self):
        patch=b'diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,2 @@\n def f():\n-    return 0\n+    return 1\n'
        correct=verify_hunks(patch,{'a.py':'def f():\n    return 0\n'})
        self.assertEqual(correct['status'],'mapped')
        self.assertEqual(correct['hunks'][0]['changed_lines'],[2])
        wrong=verify_hunks(patch,{'a.py':'def f():\n    return 2\n'})
        self.assertEqual(wrong['reason'],'buggy_side_context_anchor_mismatch')
        missing=verify_hunks(patch,{})
        self.assertEqual(missing['reason'],'source_file_not_in_bounded_capture')
    def test_same_target_coverage_interface_for_both_views(self):
        h=[dict(file='a.py',context_lines=[1,2],changed_lines=[2])]
        candidate=[dict(file='a.py',start_line=1,end_line=2)]
        def sm(line):return [dict(file='a.py',path_only_visible=False,pi_emitted_source_spans_W0=[dict(line=line,line_complete=True)])]
        old=measure(candidate,sm(1),{'a.py'},h,[])
        new=measure(candidate,sm(2),{'a.py'},h,[])
        self.assertFalse(old['changed_visible_intersect_any'])
        self.assertTrue(new['changed_visible_intersect_any'])
        self.assertTrue(new['changed_visible_full_any'])
if __name__=='__main__':unittest.main()
