"""Audit raw-file identity versus universal-newline transport, without labels."""
import gzip,hashlib,json,pathlib
N=pathlib.Path(__file__).resolve().parents[1]
V=N/'.private_confirmation_r6'
def read(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
manifest=read(V/'MANIFEST.json');receipt=read(V/'CAPTURE_RECEIPT.json')
assert receipt['manifest_SHA']==sha((V/'MANIFEST.json').read_bytes())
refs={r['uid']:r for r in receipt['rows']};rows=[];counts=dict(complete=0,raw_hash_mismatch=0,capture_text_mismatch=0,normalized_hash_differs=0,crlf_files=0,bare_cr_files=0)
for row in manifest['rows']:
    ref=refs[row['uid']]
    if ref['status']!='COMPLETE':continue
    p=V/'captures'/f"{row['uid']}.json.gz"
    assert sha(p.read_bytes())==ref['capture_SHA']
    cap=json.load(gzip.open(p,'rt'))
    raw=(pathlib.Path(row['task'])/'instruction.md').read_bytes()
    text=raw.decode('utf-8').replace('\r\n','\n').replace('\r','\n')
    counts['complete']+=1;counts['raw_hash_mismatch']+=sha(raw)!=row['instruction_SHA']
    counts['capture_text_mismatch']+=text!=cap['issue']
    counts['normalized_hash_differs']+=sha(text.encode())!=row['instruction_SHA']
    counts['crlf_files']+=b'\r\n' in raw
    counts['bare_cr_files']+=b'\r' in raw.replace(b'\r\n',b'')
    assert cap['issue_SHA']==row['instruction_SHA']
    rows.append(dict(uid=row['uid'],raw_SHA=sha(raw),transport_SHA=sha(text.encode()),capture_SHA=ref['capture_SHA']))
assert counts['raw_hash_mismatch']==counts['capture_text_mismatch']==0,counts
private=dict(rows=rows,manifest_SHA=sha((V/'MANIFEST.json').read_bytes()),capture_receipt_SHA=sha((V/'CAPTURE_RECEIPT.json').read_bytes()),normalization='UTF8 universal newlines matching capture pathlib.read_text; no generator input edits')
with (V/'INSTRUCTION_TRANSPORT.json').open('x') as f:json.dump(private,f,indent=2)
public=dict(counts=counts,manifest_SHA=private['manifest_SHA'],capture_receipt_SHA=private['capture_receipt_SHA'],transport_receipt_SHA=sha((V/'INSTRUCTION_TRANSPORT.json').read_bytes()),labels_read=False,score_read=False,source_method_changed=False)
with (N/'reports/R6_INSTRUCTION_TRANSPORT_AUDIT.json').open('x') as f:json.dump(public,f,indent=2)
print(json.dumps(public,indent=2))
