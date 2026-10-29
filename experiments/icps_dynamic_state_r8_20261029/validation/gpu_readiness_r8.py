import json,sys
from pathlib import Path
N=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(N/'src'),str(N/'core')]
from gpu_launch_config_r6 import prepare
from gpu_launch_r6 import sources_snapshot
from gpu_probe_r6 import cpu_contracts
from transformers import AutoTokenizer
import torch,ray

config,parity=prepare(N/'runs/gpu-r6-0000000000000000')
sources=sources_snapshot()
tok=AutoTokenizer.from_pretrained(N.parents[1]/'Qwen3.5-9B',local_files_only=True)
checks=cpu_contracts(tok)
assert not ray.is_initialized() and not torch.cuda.is_initialized()
report=dict(status='passed',config_parity=parity,fixture=checks,source_files=len(sources),
            GPU=False,Ray=False,model=False,production_receipt=False,training_admission=False)
(N/'reports/GPU_READINESS_R8.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
