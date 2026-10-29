"""Check frozen raw-file and transported-text identities separately."""
import hashlib

def verify(issue, raw_sha, capture_sha, witness):
    assert raw_sha == witness['raw_SHA'], 'raw instruction identity'
    assert capture_sha == witness['capture_SHA'], 'capture identity'
    assert hashlib.sha256(issue.encode('utf-8')).hexdigest() == witness['transport_SHA'], 'transport text identity'
    return True
