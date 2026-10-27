"""Inactive R6 host bridge. Frozen selector files and Actor inputs are untouched.

The caller must hold the existing per-session generation lock. Raw snapshots,
issue text and state cache are private and must be stripped by proxy integration.
No training dispatch is enabled by importing this module.
"""
import base64
import copy
import hashlib
import json
import os
import pathlib
import shlex
import time

from dense_state import validate, digest
from dynamic_session_r6_r2 import R6DynamicSessionR2

FORMAT = 'icps_dynamic_v1'
CONTEXT = 'dynamic_r6_context'
CACHE = 'dynamic_r6_runtime_cache'


class Capture:
    def __init__(self, issue, task, session, scanner):
        self.issue, self.task, self.session = issue, task, session
        self.scanner, self.seq = scanner, 0

    async def capture(self):
        start = time.time_ns()
        snapshot = await self.scanner()
        validate(snapshot)
        # Keep the same complete bounded snapshot accepted by CPU confirmation.
        # In particular, do not prefilter by initial candidate file names.
        snapshot = copy.deepcopy(snapshot)
        seq = self.seq
        self.seq += 1
        return dict(session_id=self.session, state_seq=seq,
                    state_hash=digest([self.session, seq]),
                    captured_at_start_ns=start, captured_at_end_ns=time.time_ns(),
                    pre_action=True,
                    **{CONTEXT: dict(issue=self.issue, task_uid=self.task,
                                    snapshot=snapshot)})


def proxy_fields(snapshot, tokenizer, sess, *, logical_call_id):
    c = snapshot[CONTEXT]
    identity = (c['task_uid'], snapshot['session_id'])
    issue_hash = hashlib.sha256(c['issue'].encode()).hexdigest()
    a = R6DynamicSessionR2(c['issue'], tokenizer, *identity)
    cache = sess.get(CACHE)
    if cache is not None:
        if cache['identity'] != identity or cache['issue_hash'] != issue_hash:
            raise ValueError('cross-task or changed-issue cache')
        for key, value in cache['state'].items():
            setattr(a, key, copy.deepcopy(value))
    previous = a.previous
    retry = bool(a.retry and a.retry[0] == logical_call_id)
    # Work on a reconstructed state: rejected calls cannot partly mutate cache.
    fields = a.capture(c['snapshot'], task_uid=identity[0], session_id=identity[1],
                       logical_call_id=logical_call_id, seq=snapshot['state_seq'])
    if retry:
        # capture above still validates identity/workspace before accepting retry.
        return copy.deepcopy(cache['last_fields'])
    fields.update(
        changed_files=sorted({w['file'] for w in fields['windows']})
                      if previous is not None and fields['pi_ids'] else [],
        parse_failure_count=sum(w['syntax'] != 'valid' for w in fields['windows']),
        captured_at_start_ns=snapshot['captured_at_start_ns'],
        captured_at_end_ns=snapshot['captured_at_end_ns'])
    state = {key: copy.deepcopy(value) for key, value in vars(a).items()
             if key not in {'issue', 'tokenizer', 'identity', 'variant'}}
    sess[CACHE] = dict(identity=identity, issue_hash=issue_hash,
                       state=state, last_fields=copy.deepcopy(fields))
    return fields


def public_snapshot(snapshot):
    """Only capture coordinates may enter pending records, never raw context."""
    return {key: snapshot[key] for key in
            ('session_id', 'state_seq', 'state_hash', 'captured_at_start_ns',
             'captured_at_end_ns', 'pre_action')}


def release_session(meta):
    meta.pop(CACHE, None)
    return meta


async def install_provider(environment, registry):
    if os.environ.get('PI_FORMAT') != FORMAT:
        return False
    path = pathlib.Path(environment.environment_dir).resolve().parent / 'instruction.md'
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 262144:
        raise ValueError('instruction identity')
    # Use this experiment's frozen reader, never an inherited mutable source path.
    reader = pathlib.Path(__file__).resolve().parents[1] / 'core/workspace_read.py'
    script = reader.read_bytes()
    command = '"${HARBOR_VERIFIER_PYTHON:-python3}" -B -c ' + shlex.quote(
        'import base64;exec(base64.b64decode(' +
        repr(base64.b64encode(script).decode()) + '))')

    async def scanner():
        result = await environment.exec(command=command, timeout_sec=45)
        if result.return_code:
            raise RuntimeError('dynamic source reader failed')
        if len(result.stdout.encode()) > 16 * 1024**2:
            raise ValueError('reader output limit')
        return json.loads(result.stdout)

    capture = Capture(path.read_text(), digest(['icps_task', path.parent.name]),
                      environment.session_id, scanner)
    registry.register(environment.session_id, capture.capture)
    return True
