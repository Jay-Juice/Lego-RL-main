import hashlib,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'validation'))
from instruction_transport import verify

class TransportTests(unittest.TestCase):
    def test_line_endings_preserve_separate_identity(self):
        for raw in [b'a\nb\n',b'a\r\nb\r\n',b'a\rb\r']:
            text=raw.decode().replace('\r\n','\n').replace('\r','\n')
            h=hashlib.sha256(raw).hexdigest()
            w=dict(raw_SHA=h,transport_SHA=hashlib.sha256(text.encode()).hexdigest(),capture_SHA='capture')
            self.assertTrue(verify(text,h,'capture',w))
    def test_text_change_rejected(self):
        w=dict(raw_SHA='raw',capture_SHA='cap',transport_SHA=hashlib.sha256(b'a\n').hexdigest())
        with self.assertRaises(AssertionError):verify('b\n','raw','cap',w)
    def test_raw_identity_change_rejected(self):
        w=dict(raw_SHA='raw',capture_SHA='cap',transport_SHA=hashlib.sha256(b'a\n').hexdigest())
        with self.assertRaises(AssertionError):verify('a\n','different','cap',w)
    def test_capture_change_rejected(self):
        w=dict(raw_SHA='raw',capture_SHA='cap',transport_SHA=hashlib.sha256(b'a\n').hexdigest())
        with self.assertRaises(AssertionError):verify('a\n','raw','different',w)
