import asyncio
import copy
import json
import unittest

import test_dense_state as base
from dynamic_session_r6_r2 import R6DynamicSessionR2
import dynamic_runtime_r6 as bridge


class BridgeContracts(unittest.TestCase):
    def setUp(self):
        self.tok = base.Tok()
        self.issue = 'function f returns an integer'
        self.meta = {}

    def snapshot(self, source, seq):
        return dict(session_id='s', state_seq=seq, state_hash='capture',
                    captured_at_start_ns=seq*10, captured_at_end_ns=seq*10+1,
                    pre_action=True, **{bridge.CONTEXT: dict(
                        issue=self.issue, task_uid='t', snapshot=source)})

    def call(self, source, seq, logical=None):
        return bridge.proxy_fields(self.snapshot(source, seq), self.tok, self.meta,
                                   logical_call_id=str(seq) if logical is None else logical)

    def test_frozen_direct_payload_exact_across_events(self):
        direct = R6DynamicSessionR2(self.issue, self.tok, 't', 's')
        initial = base.snap()
        added = base.snap(**{'b.py': 'def g(x):\n    return x-3\n'})
        edit = base.snap('def f(x):\n    return x+2\n')
        sequence = [initial, initial, added, edit, initial,
                    dict(files={}, stable=True, limited=False)]
        for i, source in enumerate(sequence):
            want = direct.capture(source, task_uid='t', session_id='s',
                                  logical_call_id=str(i), seq=i)
            got = self.call(source, i)
            for key, value in want.items():
                self.assertEqual(value, got[key], key)
            self.assertEqual(direct.remaining, self.meta[bridge.CACHE]['state']['remaining'])

    def test_capture_keeps_new_files_and_full_bounded_representation(self):
        source = base.snap(**{'b.py': 'def g():\n    return 2\n'})
        source['scope'] = 'bounded'
        async def scan(): return source
        c = bridge.Capture(self.issue, 't', 's', scan)
        first = asyncio.run(c.capture())
        self.assertEqual(first[bridge.CONTEXT]['snapshot'], source)
        source['files']['c.py'] = 'def h():\n    return 3\n'
        second = asyncio.run(c.capture())
        self.assertIn('c.py', second[bridge.CONTEXT]['snapshot']['files'])
        self.assertNotIn('c.py', first[bridge.CONTEXT]['snapshot']['files'])

    def test_retry_same_full_fields_and_no_charge(self):
        first = self.call(base.snap(), 0)
        cache = copy.deepcopy(self.meta)
        retry = self.call(base.snap(), 1, '0')
        self.assertEqual(first, retry)
        self.assertEqual(cache, self.meta)

    def test_changed_retry_rejected_transactionally(self):
        self.call(base.snap(), 0)
        before = copy.deepcopy(self.meta)
        with self.assertRaisesRegex(ValueError, 'retry'):
            self.call(base.snap('def f(x):\n    return x+2\n'), 1, '0')
        self.assertEqual(before, self.meta)

    def test_issue_and_session_mismatch_rejected(self):
        self.call(base.snap(), 0)
        for key in ['issue', 'session_id']:
            snap = self.snapshot(base.snap(), 1)
            if key == 'issue': snap[bridge.CONTEXT][key] = 'different'
            else: snap[key] = 'other'
            with self.assertRaises(ValueError):
                bridge.proxy_fields(snap, self.tok, self.meta, logical_call_id='1')

    def test_private_context_and_cache_scrub(self):
        snap = self.snapshot(base.snap(), 0)
        fields = self.call(base.snap(), 0)
        pending = {**bridge.public_snapshot(snap), **fields}
        self.assertNotIn(bridge.CONTEXT, pending)
        self.assertNotIn('files', pending)
        self.assertNotIn(self.issue, json.dumps(pending))
        self.assertNotIn(bridge.CACHE, bridge.release_session(self.meta))
        json.dumps(self.meta)

    def test_source_and_tokenizer_not_stored_by_reference(self):
        source = base.snap()
        self.call(source, 0)
        source['files']['a.py'] = 'mutated outside capture'
        state = self.meta[bridge.CACHE]['state']
        self.assertNotEqual(state['previous']['a.py'], source['files']['a.py'])
        self.assertNotIn('tokenizer', state)
        self.assertNotIn('issue', state)

    def test_invalid_snapshot_does_not_advance_provider(self):
        async def bad(): return dict(files={}, stable=False)
        c = bridge.Capture(self.issue, 't', 's', bad)
        with self.assertRaises(ValueError): asyncio.run(c.capture())
        self.assertEqual(c.seq, 0)


if __name__ == '__main__': unittest.main()
