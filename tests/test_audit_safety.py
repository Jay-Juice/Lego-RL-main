"""CPU-only regression tests for audit fixes; no model or remote job required."""
import ast
import asyncio
import contextlib
import importlib.util
import io
import json
import logging
import os
import subprocess
import sys
import shutil
import types
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def workspace_temp():
    # Python 3.13 TemporaryDirectory uses mode 0700 on Windows, which removes
    # the sandbox account's inherited access. Use normal workspace inheritance.
    path = ROOT / ('audit-test-' + uuid4().hex)
    path.mkdir()
    try:
        yield str(path)
    finally:
        if path.resolve().parent != ROOT.resolve():
            raise ValueError('Unexpected test cleanup path')
        shutil.rmtree(path)


def load(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VerifierTests(unittest.TestCase):
    def run_verifier(self, result):
        tree = ast.parse((ROOT / 'utils/prepare_swesmith_harbor.py').read_text(encoding='utf-8-sig'))
        code = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'RUN_TESTS' for t in n.targets))
        ns = {'__name__': 'verifier_test'}
        exec(compile(code, '<generated verifier>', 'exec'), ns)
        with workspace_temp() as temp:
            root = Path(temp)
            for name in ['testbed', 'tests/payload', 'logs/verifier']:
                (root / name).mkdir(parents=True)
            ns.update(TESTBED=root/'testbed', TESTS=root/'tests', LOGS=root/'logs/verifier')
            (root/'tests/config.json').write_text(json.dumps({'FAIL_TO_PASS':['test_x.py::test_x'], 'PASS_TO_PASS':[]}))
            (root/'tests/payload/test_x.py').write_text('def test_x(): assert True\n')
            reward = root/'logs/verifier/reward.txt'
            reward.write_text('1\n')  # stale results must not survive an error
            def invoke(*args, **kwargs):
                if isinstance(result, Exception):
                    raise result
                body = '<failure message="assertion"/>' if result == 1 else ''
                (root/'logs/verifier/pytest-report.xml').write_text(f'<testsuites><testsuite><testcase>{body}</testcase></testsuite></testsuites>')
                return types.SimpleNamespace(returncode=result, stdout='test output')
            args = {'side_effect':invoke}
            with patch.object(ns['subprocess'], 'run', **args), patch.object(ns['importlib'].util, 'find_spec', return_value=None), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc = ns['main']()
            return rc, reward.read_text().strip() if reward.exists() else None, json.loads((root/'logs/verifier/grading_status.json').read_text())

    def test_real_pass_and_failure(self):
        for code, expected in [(0,'1'),(1,'0')]:
            with self.subTest(code=code):
                rc, reward, status = self.run_verifier(code)
                self.assertEqual((rc,reward,status['status']), (0,expected,'scored'))

    def test_infrastructure_codes_and_timeout_have_no_reward(self):
        for error in [2,3,4,5,subprocess.TimeoutExpired('pytest',300)]:
            with self.subTest(error=str(error)):
                rc,reward,status = self.run_verifier(error)
                self.assertNotEqual(rc,0)
                self.assertIsNone(reward)
                self.assertEqual(status['status'],'unresolved')


class ModelCheckTests(unittest.TestCase):
    def setUp(self):
        self.module = load('utils/verify_merged_hf_keys.py')

    def test_empty_directories_fail_without_loading_dependencies(self):
        with workspace_temp() as temp:
            self.assertEqual(self.module.main([temp,temp]),1)
        self.assertFalse(self.module.compare_shapes({}, {})[0])

    def test_shapes_and_explicit_mtp_exception(self):
        b={'model.weight':(2,3),'mtp.weight':(3,)}
        self.assertTrue(self.module.compare_shapes(b,b)[0])
        self.assertFalse(self.module.compare_shapes(b,{'model.weight':(2,3)})[0])
        self.assertTrue(self.module.compare_shapes(b,{'model.weight':(2,3)},allow_missing_mtp=True)[0])
        self.assertFalse(self.module.compare_shapes(b,{'model.weight':(3,2)},allow_missing_mtp=True)[0])

    def test_duplicate_keys_and_wrong_index(self):
        class Handle:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def keys(self): return ['weight']
            def get_slice(self,key): return types.SimpleNamespace(get_shape=lambda:[2])
        fake = types.SimpleNamespace(safe_open=lambda *a,**kw:Handle())
        with workspace_temp() as temp, patch.dict(sys.modules,{'safetensors':fake}):
            d=Path(temp);(d/'a.safetensors').touch();(d/'b.safetensors').touch()
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                self.module.keys_and_shapes(d)
            (d/'b.safetensors').unlink()
            (d/'model.safetensors.index.json').write_text(json.dumps({'weight_map':{'weight':'missing.safetensors'}}))
            with self.assertRaisesRegex(ValueError,'index'):
                self.module.keys_and_shapes(d)


class LoopVerdictTests(unittest.TestCase):
    def test_binary_verdict(self):
        helper=load('src/verl_patch/agent_loop/verdict.py').binary_verifier_reward
        for reward in [0,1,'0','1']:
            self.assertEqual(helper(types.SimpleNamespace(rewards={'reward':reward})),float(reward))
        for value in [None,{}, {'reward':None},{'reward':float('nan')},{'reward':float('inf')},{'reward':2}]:
            self.assertIsNone(helper(types.SimpleNamespace(rewards=value)))

    def run_trial(self, results):
        # Execute the actual trial control-flow AST with external Harbor/proxy
        # replaced. This does not claim to exercise verl/Ray integration.
        tree=ast.parse((ROOT/'src/verl_patch/agent_loop/builtin_swe_agent_loop.py').read_text(encoding='utf-8'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BuiltinSWEAgentLoop')
        method=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='_run_harbor_trial')
        class Trial:
            @classmethod
            async def create(cls,cfg): return cls()
            async def run(self): return results.pop(0)
        class Proxy:
            def session_url(self,s):return 'http://localhost'
            def session_anthropic_base(self,s):return 'http://localhost'
            async def open_session(self,*a,**kw): pass
            async def pop_session(self,*a):return {'traj_acc_ids':[1,2], 'initial_prompt_token_len':1,'traj_response_mask':[1], 'traj_response_logprobs':[-.2]}
        ns=dict(Path=Path, deepcopy=deepcopy, os=os, json=json, uuid4=uuid4, logger=logging.getLogger('test'), Trial=Trial, TrialConfig=types.SimpleNamespace(model_validate=lambda x:x), _safe_session_slug=lambda x:'task', inject_harness_endpoint=lambda *a,**kw:None, binary_verifier_reward=load('src/verl_patch/agent_loop/verdict.py').binary_verifier_reward, TerminationReason=types.SimpleNamespace(AGENT_COMPLETED='agent_completed',TIMEOUT='timeout',OVERLONG='overlong'))
        status_keys=next(n for n in tree.body if isinstance(n,ast.Assign)
                         and any(getattr(t,'id','')=='_TRIAL_STATUS_METRIC_KEYS' for t in n.targets))
        mod=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),status_keys,method],type_ignores=[])
        exec(compile(ast.fix_missing_locations(mod),'<actual trial method>','exec'),ns)
        with workspace_temp() as temp:
            loop=types.SimpleNamespace(base_trials_dir=temp,max_retries=len(results),_collect_harbor_timings=lambda *a:None,_assign_proxy_metrics_from_session=lambda *a:None)
            selection=types.SimpleNamespace(definition=types.SimpleNamespace(name='openhands_sdk',protocol='openai',harbor_cfg={}),source='test')
            metrics={}
            reward,reason,meta=asyncio.run(ns['_run_harbor_trial'](loop,'/tasks/x',1,{},Proxy(),metrics,harness_selection=selection))
            return reward,meta,metrics

    def test_nonzero_exit_without_verdict_and_exhausted_retries_are_dropped(self):
        for results in [[types.SimpleNamespace(exception_info=types.SimpleNamespace(exception_type='NonZeroAgentExitCodeError',exception_message='bad'),verifier_result=None)], [types.SimpleNamespace(exception_info=None,verifier_result=None)]*2]:
            reward,meta,metrics=self.run_trial(results)
            self.assertTrue(meta['disable_proxy_trajectory'])
            self.assertTrue(meta['verifier_unresolved'])
            self.assertEqual(metrics['verifier_unresolved'],1)

    def test_valid_zero_is_kept_and_retry_success_is_kept(self):
        for results in [[types.SimpleNamespace(exception_info=None,verifier_result=types.SimpleNamespace(rewards={'reward':0}))],[types.SimpleNamespace(exception_info=None,verifier_result=None),types.SimpleNamespace(exception_info=None,verifier_result=types.SimpleNamespace(rewards={'reward':1}))]]:
            reward,meta,metrics=self.run_trial(results)
            self.assertFalse(meta.get('verifier_unresolved',False))
            self.assertEqual(metrics['verifier_unresolved'],0)


class SummaryTests(unittest.TestCase):
    def test_exact_500_and_binary_rewards_required(self):
        module=load('utils/summarize_verified_shards.py')
        with workspace_temp() as temp:
            root=Path(temp); jobs=root/'jobs'; shards=root/'shards'; files=[]
            for i in range(500):
                task=f'task-{i}'
                data=shards/f'shard_{i%8}'/task;data.mkdir(parents=True)
                (data/'task.toml').write_text('')
                job=jobs/f'eval-qwen35-9b-verified-full-test-s{i%8}'
                reward=job/(task+'__trial')/'verifier'/'reward.txt'
                reward.parent.mkdir(parents=True)
                reward.write_text('1');files.append(reward)
                (job/'result.json').write_text('{}')
            argv=['summary','--jobs-root',str(jobs),'--shards-root',str(shards),'--run-id','test','--output',str(root/'summary.json')]
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(),0)
                for bad in ['nan','inf','2','garbage']:
                    files[0].write_text(bad)
                    self.assertEqual(module.main(),2)
                files[0].write_text('1')
                (shards/'shard_0/task-0/task.toml').unlink()
                files[0].unlink()
                self.assertEqual(module.main(),2)
                self.assertEqual(json.loads((root/'summary.json').read_text())['expected_tasks'],499)

    def test_composite_run_rejects_invalid_reward(self):
        module=load('utils/merge_verified_runs.py')
        with workspace_temp() as temp:
            root=Path(temp);dataset=root/'data';jobs=root/'jobs'
            for i in range(500):
                d=dataset/f'task-{i}';d.mkdir(parents=True);(d/'task.toml').write_text('')
                p=jobs/'eval-qwen35-9b-verified-full-test-s0'/f'task-{i}__trial'/'verifier'/'reward.txt'
                p.parent.mkdir(parents=True);p.write_text('1')
            argv=['merge','--dataset-root',str(dataset),'--jobs-root',str(jobs),'--run-id','test','--output',str(root/'summary.json')]
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(),0)
                p.write_text('nan')
                self.assertEqual(module.main(),2)
                self.assertEqual(len(json.loads((root/'summary.json').read_text())['invalid_reward_files']),1)


if __name__=='__main__':unittest.main()
