"""Invoke existing CPU assertions without installing pytest in production.

Only removes pytest import/decorators and selects tests not using pytest helpers.
This is a selected assertion audit, not a full pytest run or distributed test.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
import ast, pathlib, json
root=pathlib.Path('/media/ubuntu/D1/zsj/Lego-RL-main')
files=['third_party/verl/tests/trainer/ppo/test_sao_on_cpu.py',
       'third_party/verl/tests/experimental/agent_loop/test_reward_placement_on_cpu.py',
       'third_party/verl/tests/trainer/ppo/test_value_loss_normalization_on_cpu.py']
results=[]
for f in files:
    tree=ast.parse((root/f).read_text())
    namespace={'__name__':'audit_direct_test_invocation','__file__':str(root/f)}
    candidates=[];body=[]
    for node in tree.body:
        if isinstance(node,ast.Import):
            node.names=[n for n in node.names if n.name!='pytest']
            if not node.names:continue
        if isinstance(node,ast.FunctionDef):
            node.decorator_list=[]
            if node.name.startswith('test_'):
                if 'pytest.' in ast.unparse(node):continue
                if not node.args.args:candidates.append((node.name,()))
                elif node.name=='test_skip_observation_gae_matches_paper_recursion':
                    candidates.extend([(node.name,(.95,)),(node.name,(1.,))])
                elif node.name=='test_partition_invariance_with_global_normalization':
                    candidates.extend((node.name,(p,)) for p in ['one-pack','micro-bsz-1','balanced-packs','unbalanced-packs'])
        body.append(node)
    tree.body=body;ast.fix_missing_locations(tree)
    exec(compile(tree,f,'exec'),namespace)
    for name,args in candidates:
        try:
            namespace[name](*args)
            results.append({'test':name,'args':args,'ok':True})
        except Exception as e:
            results.append({'test':name,'args':args,'ok':False,'exception':str(e)})
print('AUDIT_JSON='+json.dumps({'checks':results,'passed':sum(x['ok'] for x in results),
 'scope':'Selected existing CPU tests invoked directly; no pytest installation, no production source modifications; not a distributed GPU integration test.'}))
