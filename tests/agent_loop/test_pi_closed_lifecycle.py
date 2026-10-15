import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import unittest
from unittest.mock import patch

from harbor_patch.privileged_state import registry
from verl_patch.agent_loop.vllm_chat_completion_proxy import (
    _VLLMChatCompletionsProxy, _proxy_error_from_exception,
)


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for name, value in [('_providers', {}), ('_closed_sessions', set())]:
            p = patch.object(registry, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.dict('os.environ', {'PI_ENABLE': '1'})
        p.start()
        self.addCleanup(p.stop)

    async def test_live_provider_is_unchanged(self):
        snapshot = {'state_hash': 'same', 'entities': []}
        registry.register('live', AsyncMock(return_value=snapshot))
        assert await registry.capture('live') is snapshot


    async def test_unknown_or_never_registered_still_fails_closed(self):
        registry.unregister('unknown')
        with self.assertRaisesRegex(RuntimeError, 'No pre-action PI provider') as e:
            await registry.capture('unknown')
        assert not isinstance(e.exception, registry.SessionClosedError)


    async def test_close_during_capture_rejects_result(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def provider():
            entered.set()
            await release.wait()
            return {'state_hash': 'stale'}
        registry.register('race', provider)
        task = asyncio.create_task(registry.capture('race'))
        await entered.wait()
        registry.unregister('race')
        release.set()
        with self.assertRaises(registry.SessionClosedError):
            await task


    async def test_re_registration_and_other_sessions(self):
        registry.register('a', AsyncMock(return_value='old'))
        registry.register('b', AsyncMock(return_value='unaffected'))
        registry.unregister('a')
        assert await registry.capture('b') == 'unaffected'
        registry.register('a', AsyncMock(return_value='new'))
        assert await registry.capture('a') == 'new'


    async def check_proxy(self, case):
        proxy = object.__new__(_VLLMChatCompletionsProxy)
        for name in ('_sessions', '_session_state_locks', '_session_generation_locks',
                     '_session_attempts', '_main_initial_messages', '_sub_session_keys'):
            setattr(proxy, name, {})
        proxy._sessions_lock = asyncio.Lock()
        proxy._session_attempt_seq = 0
        proxy._compute_prompt_ids = AsyncMock(return_value=[1, 2, 3])
        proxy._translate_sampling_params = lambda body: {}
        proxy._server_manager = SimpleNamespace(generate=AsyncMock())
        lease = SimpleNamespace(wait_sec=0, release=AsyncMock())
        async def acquire(*args, **kwargs):
            if case == 'closed_while_queued':
                registry.unregister('s')
            return lease
        proxy._session_scheduler = SimpleNamespace(acquire=acquire)
        if case != 'unknown':
            provider = AsyncMock(side_effect=RuntimeError('real capture failure')) if case == 'capture_error' else AsyncMock()
            registry.register('s', provider)
        if case == 'closed_before_request':
            registry.unregister('s')
        with self.assertRaises(RuntimeError) as exc:
            await proxy._generate_assistant_message('s', [{'role': 'user', 'content': 'x'}], None, {})
        state = proxy._sessions['s']
        if case.startswith('closed'):
            assert isinstance(exc.exception, registry.SessionClosedError)
            assert _proxy_error_from_exception(exc.exception).status == 410
            assert not state.get('pi_error')
            assert state['pi_closed_requests'] == 1
        else:
            assert state['pi_error']
            assert not isinstance(exc.exception, registry.SessionClosedError)
        proxy._server_manager.generate.assert_not_awaited()
        lease.release.assert_awaited_once()
        assert not state.get('pi_pending_record')
        assert not state.get('pi_call_records')
        assert not state.get('traj_acc_ids')

    async def test_proxy_closed_before_request(self):
        await self.check_proxy('closed_before_request')

    async def test_proxy_closed_while_queued(self):
        await self.check_proxy('closed_while_queued')

    async def test_proxy_unknown(self):
        await self.check_proxy('unknown')

    async def test_proxy_capture_error(self):
        await self.check_proxy('capture_error')
