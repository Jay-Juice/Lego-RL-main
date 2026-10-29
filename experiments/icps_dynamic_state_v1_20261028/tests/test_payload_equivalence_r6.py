import copy,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'validation'))
from payload_equivalence_r6 import assert_equivalent
class PayloadTests(unittest.TestCase):
    def setUp(self):self.p=dict(serialized=dict(S1=dict(wall_seconds=.1,CPU_seconds=.1,pi_ids=[1],pi_text='x'),r6_session=dict(pi_ids=[2],state_hash='s')))
    def test_only_old_elapsed_is_excluded(self):
        b=copy.deepcopy(self.p);b['serialized']['S1'].update(wall_seconds=.9,CPU_seconds=.8)
        assert_equivalent(self.p,b)
    def test_pi_token_and_state_drift_rejected(self):
        for mode,key,val in [('S1','pi_ids',[7]),('S1','pi_text','y'),('r6_session','pi_ids',[7]),('r6_session','state_hash','t')]:
            b=copy.deepcopy(self.p);b['serialized'][mode][key]=val
            with self.assertRaises(AssertionError):assert_equivalent(self.p,b)
    def test_other_telemetry_and_bad_time_not_excluded(self):
        b=copy.deepcopy(self.p);b['serialized']['r6_session']['wall_seconds']=.2
        with self.assertRaises(AssertionError):assert_equivalent(self.p,b)
        b=copy.deepcopy(self.p);b['serialized']['S1']['wall_seconds']=float('nan')
        with self.assertRaises(AssertionError):assert_equivalent(self.p,b)
