import unittest
from capacity_score_r2 import assert_retention,KEYS

class Contracts(unittest.TestCase):
    def test_unmapped_rows_have_no_changed_metrics(self):
        assert_retention({'file_hit1':True},{'file_hit1':False})
    def test_mapped_gain_and_retention(self):
        assert_retention(dict.fromkeys(KEYS,False),dict.fromkeys(KEYS,True))
        assert_retention(dict.fromkeys(KEYS,True),dict.fromkeys(KEYS,True))
    def test_actual_loss_still_rejected(self):
        with self.assertRaisesRegex(AssertionError,'lost'):assert_retention(dict.fromkeys(KEYS,True),dict.fromkeys(KEYS,False))
    def test_inconsistent_partial_or_nonbool_rejected(self):
        for a,b in [({},dict.fromkeys(KEYS,False)),({KEYS[0]:False},{KEYS[0]:False}),(dict.fromkeys(KEYS,0),dict.fromkeys(KEYS,False))]:
            with self.assertRaises(AssertionError):assert_retention(a,b)
if __name__=='__main__':unittest.main()
