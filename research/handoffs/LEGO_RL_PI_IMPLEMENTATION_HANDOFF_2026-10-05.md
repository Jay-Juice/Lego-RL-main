# Lego-RL / SAO 基线结项与 PI 接入 handoff

> GitHub归档副本：本文保留工作站/服务器操作路径。本文所述外层SAO_RESEARCH目录在本归档中位于同级；`Lego-RL-main/`源码前缀在Git仓库根下应省略。机器状态是交接时快照，不是启动授权。

更新日期：2026-10-05，Asia/Shanghai。供下一位实现 PI（Privileged Information / Privileged Critic）的 agent 使用。

## 0. 接手先读：当前状态与用户意图

- 用户最新要求：把当前工作交接，下一步另开 agent 实现 PI 信息问题。本轮只整理，不实现 PI、不启动训练/评测，不创建新 agent。
- 训练已在新 batch64 实验 **step70 完整保存后因空间不足停止**。不是完成97步；不要自动恢复。
- 新 batch64 的20/30/40/50/60/70评测，以及用户追加的原始step0重测，全部完成。
- 自动化 `lego-rl-batch64` **PAUSED**，保留规则 `RRULE:FREQ=MINUTELY;INTERVAL=150`；不要依据旧heartbeat重新启用或重复跑历史队列。
- 本次交接只读核验：GPU compute processes为空；D1剩 **102.07 GiB**；六份checkpoint Actor/Critic各24个非空 `.pt`，每份 `data.pt=7316 bytes`。这是非空/数量检查，不是重新加载全分片或逐张量验证。
- 完整checkpoint约177 GiB，当前空间不够再保存一份。**新checkpoint全部保留；旧删除授权不能套用到新实验。** 实现PI可以先做源码/CPU验证，训练前必须重新核对资源与用户实验范围。
- 详细实录：`LEGO_RL_SWE_HANDOFF_2026-09-24.md`，最新§148；此文件优先概括当前状态，旧实录中的后续节覆盖前面过时指令。
- 本次快照：`SAO_RESEARCH_2026-09-29/handoff_snapshot_20261005.json`，含六份最终审计摘要/SHA与资源状态。

## 1. 路径、操作方式与安全约束

| 项目 | 路径/值 |
|---|---|
| Windows外层工作区 | `D:\ai project\RL学习\Lego-RL-main` |
| Windows实际源码根 | `D:\ai project\RL学习\Lego-RL-main\Lego-RL-main` |
| 服务器SSH别名 | `A800`，已可 `ssh -o BatchMode=yes A800` |
| 服务器项目根 | `/media/ubuntu/D1/zsj/Lego-RL-main` |
| 原始模型 | 远端根下 `Qwen3.5-9B` |
| 项目Python | 远端根下 `.venv/bin/python` |
| Windows Python | `D:/anaconda/anaconda3/python.exe` |
| CUDA启动包装器 | `/home/ubuntu/.local/bin/lego-cuda12-run` |
| 训练短TMPDIR | `/tmp/lego-b64-v6`，指向D1的短符号链接 |
| 评测短TMPDIR | `/media/ubuntu/D1/zsj/tmp-e64` |

Windows源码权威：先改Windows，针对变更文件做WSL/rsync dry-run、精确同步和SHA核验，不能全目录覆盖服务器。服务器 `third_party/verl` 与 `third_party/vllm` 有项目补丁，不要重装或重置工作树。

只处理有明确本run归属的进程/容器。禁止全局 `ray stop` / Docker prune、共享Docker重启、按泛化进程名批量kill、停止他人任务、修改共享环境、GPU reset。所有大文件、模型、轨迹、临时大文件仅D1，不放系统盘。长TMPDIR曾两次导致UNIX socket路径超过107字节，不能恢复旧长路径。

不要因日志出现题目正文自带的Traceback就判训练故障；核对真实 `result.exception_info`、正式指标、进程退出及上下文。

## 2. PI设计的来源、边界与尚未完成的工作

**当前稳定SAO实验不等于已经实现PI。** 以下来自已有研究设计，不是本轮已经通过的实现，也不是已选定的唯一方案。

必读：

1. `Lego-RL-main/research/LEGO_RL_SWE_PRIVILEGED_CRITIC_RESEARCH_2026-09-19.md`：当前框架接入点、SWE状态定义、token映射难点。其服务器状态、模型建议和数据准备状态是9月19日历史，已被本handoff更新，不能照旧操作。
2. `D:\ai project\RL学习\Agent-R1\privileged_critic_agentic_rl_idea.md`：原始AAC研究意图，已确认该文件存在。
3. `SWE_AGENT_LIGHTNING_COMPLETE_HANDOFF_2026-09-19.md`：此前Lightning工作结项。旧模块路径是线索，需定位当前文件；本轮未确认旧 `agentlightning/privileged_state` 实际位置。
4. 上述9月19日研究报告列出的旧CAPO/P1/PI-v2资料：可参考边界和失败教训，不把旧PPO代码直接当SAO实现。

### 必须守住的信息边界

- Actor使用部署可见历史 `H_t`；训练Critic额外使用当前状态 `Z_t`，即 `V(H_t,Z_t)`。Actor输入、old/ref logprob和部署推理接口不能混入PI。
- `Z_t`在**对应model call生成之前**采集，同一call所有动作token使用这一生成前状态。不能把本次动作执行后的文件变化、下一call快照或终局信息灌给当前value。
- 候选信息：沙箱工作区当前净变化、进程/socket状态等。Delta为相对 prepared buggy初态 `S_0` 的净变化；改后恢复的文件应消失，不是无限追加事件日志。
- 不用reference/oracle patch、未来轨迹、终局reward或动作后hidden test verdict充当当前baseline的输入。修数据时的bug/oracle控制证据不能被当作PI特征来源。
- SWE不少状态原则上可由Actor工具查询；研究表述是额外状态可见性/减少重建成本，不声称所有PI永远无法被Actor观测。
- 记录快照范围、开始结束时间、失败/截断/一致性标志；后台进程仍会写文件，不能凭单时间戳声称跨文件原子快照。

### 接线入口与关键难点

当前路径：parquet → `BuiltinSWEAgentLoop` → Harbor Trial/沙箱 → model-call proxy → token/mask/logprob轨迹 → verifier → verl batch → values/GAE → Actor/Critic。

重点文件（内层源码根相对路径）：

- `src/verl_patch/agent_loop/builtin_swe_agent_loop.py`：Trial生命周期、结果有效性、整轨迹组装。
- `src/verl_patch/agent_loop/vllm_chat_completion_proxy.py`：真正生成边界、token归档、历史重写与logprob对齐；已有重建前缀logprob逻辑，不能粗暴拼接PI破坏其合约。
- `src/harbor_patch/environments/remote_docker.py`：状态采集adapter；评测另用guarded环境，不要混淆。
- `src/harbor_patch/agents/`：OpenHands SDK调用/工具生命周期。
- `patches/verl_7aed6b23.patch`、`patches/verl_sao_7aed6b23.patch`及远端 `third_party/verl` 实际实现：value forward/update、GAE、loss与dispatch。
- `scripts/train/lib/hydra_args.sh`、训练config：显式配置和最终Hydra差异检查。

Lego训练行是整条多轮轨迹，不是旧Lightning每call一行。**不能在整轨迹开头拼接所有未来PI。** 9月19日设计给出两个待评估方案：

1. Critic独立序列按时间插入 `H0,Z0,A0,O1,Z1,A1,...`；保存Actor→Critic token索引，value gather回原Actor response形状后GAE。
2. Critic按真实call `(Ht,Zt,At)` 独立前向再映射回整轨迹；注意重复历史成本和拆分后的loss权重等价性。

需要明确 `episode_id/sandbox_id/logical_call_id/attempt_id/state_seq/snapshot_hash/action_token_span`，并处理历史重写、context compaction、partial retry、多session。PI/observation/padding不能被误当动作监督token。value在token前/后的位置移位、response_mask与终局reward落点必须按实际SAO代码验证。

建议新agent先给出可审计的数据合约和实现计划，再做有针对性的验证：空PI退化等价、Actor张量不变、未来状态隔离、call/token映射、截断/缺失快照、正常和异常batch同schema、value前向与update一致、固定batch梯度/loss对照、真实Harbor生成前快照。以上是接手建议，未执行。

PI实验应命名为SAO vs PI-SAO（若沿用现有配方），不要把SAO自动称作普通PPO。起点从base还是已有checkpoint、PI内容/预算和具体方案尚无本轮新决定，不应凭本handoff擅自开长训练。

## 3. 当前可恢复训练基线

实验：`sao-qwen35-9b-swesmith-b64-w32-v6d-20260930`，从原始Qwen3.5-9B启动，计划97步，实际停在70。

checkpoint根：

`checkpoints/sao-qwen35-9b-swesmith/sao-qwen35-9b-swesmith-b64-w32-v6d-20260930`

保留 `global_step_20/30/40/50/60/70`。每份Actor/Critic包含model/optim/extra_state各8rank，共各24pt，加data.pt。不要从基准测速权重恢复。

生产config：`scripts/train/configs/sao_b64_resume20_tokens_20261001.env`，SHA `731a2dc64e38c81f16d6b6605474b3417da45ec829cb0fb93ff055d57c29bb91`，source原v6d配置。旧生产日志 `logs/sao_b64_resume20_tokens_20261001_{launcher,train,vllm}.log`；旧screen已停止，不重启旧命令。

| 参数 | 实际设置 |
|---|---|
| 总batch / prompt batch / mini | 64 / 64 / 64，Actor与Critic mini均显式64 |
| rollout worker | 总32，不是每GPU32 |
| SP | 8 |
| Actor/Critic epochs | 1 / 2 |
| LR | Actor1e-6、Critic5e-6（最终展开为准） |
| Actor/Critic动态更新token预算 | step20后16384 / 45056；之前14336 / 20480 |
| ref/rollout logprob token预算 | 显式保留14336 |
| 学习response / 模型context / turns | 65536 / 98304 / 128 |
| 数据 | `data/swesmith_python_full_v7_verdict_v6_20260930.parquet`，6248题 |
| 保存 / 训练内测试 / keep | 10 / 0 / 1000；所有新checkpoint保留 |
| Critic预热 | `critic_warmup=20`：1–19仅Critic，20首次Actor更新 |

冻结ray_trainer把保存放在Actor分支内，因此step10不会保存，第一份为20。这不是checkpoint丢失。

用户要求保持原作者空批次实现：**没有部署** `apply_verdict_empty_batch_guard.py`，不要执行它。不能声称局部全mask必然NaN；实际全局分母使局部空微批次可为正常零梯度。

独立于Actor冻结预热，还有 `critic.optim.lr_warmup_steps=10` 未被实际VeOmni读取的问题：实际读取ratio=0，初始LR直接5e-6。已记录、未修，不能暗改后声称同基线。

## 4. 适配修复、验证边界与不能回滚的内容

- 早期本地SWE-Smith适配把含内嵌测试的业务源码当payload整文件删除/评分时恢复，可能覆盖模型修复；已通过固定bug/oracle对照确认属于我们的适配问题。不是SAO算法错误。
- 补了verifier子进程PATH、可信内嵌测试归一与防篡改、限定业务收集失败判分、Git blob提取、任务特定离线依赖/兼容等。最终恢复原AL v7 **6248题**，不使用6075隔离候选。
- 最后四题Tldextract/Patsy/Pyquery/Conan真实控制通过；Conan下载基础镜像缺CMake，使用离线CMake补齐，不是模型业务bug。其他三题需根据候选源码+具体测试证据识别业务失败，不把任意pytest exit2/4都判0。
- Redbot因自动 `harbor-baseline` tag破坏版本解析；专用 `agent_loop_config_oh_docker_b64_v6.yaml` 改成 `harborbaseline`，真实bug0/oracle1通过。
- 6248不是全量动态认证；不要把专项/抽样通过写成所有任务无缺陷。
- 原AL排除67训练题仍不在6248里：55依赖在线服务、9纯测试变异、3空补丁通过；Python范围之外Go任务另算，详见恢复报告。
- 两次metadata/schema缺字段退出属于本地改动遗漏：reward_extra_info的verifier_unresolved，以及metrics的agent_timeout。均已修；正常/超时/未决/empty真实DataProto合并120排列通过。
- loop最新已部署SHA `e8d81f5a1737a8d1655ed38c5051737ca579819586e8898ffeca9d42b9d13594`，不要用旧cdad manifest覆盖。以后修改应重新生成证据，不把此SHA当永久不可编辑。
- 训练轨迹前缀截断配完整reward风险仍在：学习response含工具观察，100条风险加权重建中约30条超64K，但非精确原始token审计、非全量比例。PI不能再把它加重或掩盖。

相关报告目录 `SAO_RESEARCH_2026-09-29/`：
`SAO_IMPLEMENTATION_AND_REGRESSION_ANALYSIS.md`、`DATA_TRAJECTORY_AND_BATCH64_AUDIT.md`、`SWESMITH_ADAPTER_FIX_V3.md`、`SWESMITH_RECOVERY_AND_AL_FILTERS_2026-09-30.md`、`SWESMITH_FINAL_FOUR_FIX_2026-09-30.md`、`BATCH64_START_AND_ENVIRONMENT_EVIDENCE_2026-09-30.md`。按日期/实录后续修正阅读，旧“未部署”不代表最终状态。

## 5. 评测最终结果：新batch64与原始base

所有分母500。用户展示口径允许未决计失败，但原始reward/未决证据不改。

| 模型 | 已验证通过 | 已验证失败 | 未决 | 未决计失败口径 |
|---|---:|---:|---:|---:|
| 历史原始base | 279 | 221 | 0 | 55.8% |
| 本次原始base重测 | 266 | 234 | 0 | 53.2% |
| 新batch64 step20 | 262 | 238 | 0 | 52.4% |
| 新batch64 step30 | 286 | 213 | 1 | 57.2% |
| 新batch64 step40 | 291 | 208 | 1 | 58.2% |
| 新batch64 step50 | 293 | 207 | 0 | 58.6% |
| 新batch64 step60 | 282 | 218 | 0 | 56.4% |
| 新batch64 step70 | 286 | 214 | 0 | 57.2% |

不能从单次采样分数宣布统计显著提升。尤其历史base与重测资源不同、有超时影响。

远端结果通用路径：

`logs/eval-qwen35-9b-verified-full/b64-v6d-step{step}-20261004-v2-n32-threads/summary_audited_verdict_v2.json`

base重测run：`base0-recheck-20261005-v1-n32-threads`，同结果根。已合并模型：`merged_models/b64-v6d-step{step}-20261004`。新分片：`data/verified-b64-step{step}-20261004`。

逐题结果：`harbor_trials/eval-qwen35-9b-verified-full-{run}-s{0..7}/*/result.json`；原补丁 `artifacts/predict_patch.diff`；轨迹 `agent/trajectory.json`。verifier完成时间在顶层 `verifier.finished_at`，不是 `verifier_result.finished_at`。

审计要求：500唯一/无重复遗漏/8shard exit0、reward有限二值、reward.txt一致、verifier finished。AgentTimeoutError或NonZeroAgentExitCodeError之后仍可能有完整verdict，不能仅凭Agent异常否定结果。无verdict保留未决，不能写0。

最终审计脚本 `SAO_RESEARCH_2026-09-29/audit_b64_eval_20261004.py` SHA `bfc8b1651d08bd3a14cc075e5623beefdff582158ca5837bf1db5907331ca4de`。旧 `summary_audited.json`曾误拒所有Agent异常，不沿用；使用verdict_v2版本。

未决与比较限制：

- 新30 Django15128：VerifierTimeout6000秒；原补丁while循环重算不变candidate，条件成立可能无限循环，非最终正式reward。patch SHA `29ba51836c0572ef71896aafd164a9ad24e9ed8a33655eaf5a92da9dfb64941d`。旧实录把单次多条ok误说持续进展，§143已纠正。
- 新40 Sphinx7985：长验证后精确停止验证进程组，无reward，保留未决。诊断 `logs/step40_bounded_diagnostics_20261005`。
- 新40 Django14539：手工停止旧验证后Harbor自动重新跑了Agent，随后reward1；不是固定补丁复验，比较必须披露，不能称全程无重生成。

## 6. 旧batch16历史仅作参考，不能混同名step

base279；20=272；25=262；30误删未测；40=254；50=246；60=205且2未决；70=240且2未决；80=254；90=226；100=222；110=221；120=240（固定原补丁补正）；130=237且1未决，均/500。

旧原始checkpoint40/50/60/70及后来80–130已经按当时明确授权删除；旧30误删要如实披露。旧HF和评测结果保留，不要把该删除范围应用新batch64。训练中期评分适配、预算/资源变化意味着历史前后并非完全相同配方。

## 7. 当前快速全量评测协议（已完成，不重新执行）

入口 `scripts/eval/run_qwen35_verified_threads_8gpu.sh`，每GPU独立TP1 vLLM，每卡32并发；完整同500题。

temp0.7、context262144、input200000、单次output32768、Agent200轮/7200秒、2CPU/8GB、相同SDK/runtime/verifier预算；显式172.16.240.0/20池下/29网络。只verifier设置OMP2、BLAS/MKL等1与进程组guard，不改Agent语义。

guard解决验证超时子进程残留；scikit曾2CPU配额却启动127线程，限线程后固定原补丁测试迅速结束。Sphinx模型补丁逻辑死锁是另一类问题，不都归因环境。复验只固定原补丁，不替模型改答案、不择优重生成。

旧评测队列root v1/v2/continue60/continue30/continue20均为历史。最后base等待器 `logs/base0_recheck_20261005` 状态complete、exit0。不要重启 `gate.py` 或旧screen。新实验需新run、新结果目录，不能覆盖历史。

## 8. 慢速根因调查：最新结论与撤回的推断

用户明确“先别跑新实验”；最后几轮只读现有数据。

- 新base完整500耗时168.25分钟，新20为159.38，旧batch16 step80快测51.58；450题完成已分别135.21/134.74/36.76分钟，慢不是仅最后一题。
- 旧快测step80是不同训练模型，不能当相同原始base的速度基线。
- 找回历史原始base的精确互补来源：`20260923-123439-missing362`（362题、每卡2并发）+`20260923-015414-retry2`（138题、每卡8并发），无交集且500齐全。
- 同469题完整轨迹：历史base/本次base的平均轮数78.74/79.46、input363万/359万、终端调用61.50/62.88，几乎一致。**原始模型不是这次才变重。** 旧80同题59.64轮/input180万/终端25.88次，行为本来更短；不代表更准确。
- 三组run_agent.py SHA均 `8cac001a02313237e2aeb70427e515488af65906354ea61e8a7b5410e0d6d117`，系统prompt、工具定义、chat template一致；原始模型的终端返回内容前后均约9.35万字符，旧80约2.84万。
- 原始base历史n2/n8/本次n32在Running>0样本中的prefix均97.90/96.32/68.72%，KV峰值16.1/32.4/91.8%。同原始模型长历史一直存在，n32加重同时竞争，支持cache复用恶化/prefill竞争的解释；历史子集和单次采样不同，不能宣称受控最佳并发测试已做。
- 当前vLLM源码说明prefix命中是最近约1000请求的滑动token统计；KV占用只反映非free块，free队列可含缓存历史，重新分配会淘汰。没有OOM/preemption不等于没有缓存驱逐。
- 旧“KV70%是性能临界点”未被证明，只有相关性；没有逐请求驱逐/完整HTTP输入记录，无法把所有miss归因容量，也未完全排除消息重写贡献。
- vLLM版本和配置记录相同：0.19.1.dev0+g2a69949bd.d20260920，prefill budget8192、Mamba align、KV54.76GiB/448272 tokens、TP1、eager/FA2。版本号不保证源码全同；已查到5个未提交变更，R3buffer在未启用的return_routed_experts分支，另为显式探针utility，未找到直接导致慢速证据。不要重置这些补丁。

证据本地：`SAO_RESEARCH_2026-09-29/base0_recheck_performance_20261005.json`、`historical_base_matched_analysis_20261005.json`；远端 `logs/base0_recheck_20261005/` 下相应JSON和deep_trajectory_summary。完整来源/限制见旧实录§146–148。

## 9. 已完成性能试验，避免新agent重跑

固定64条输入3315031 attention tokens，各候选从原20独立恢复，未把基准更新混入生产。用户取消完整基线/预热，主要为单次冷测，历史时间不同输入不算严格提速。

- SP8 Critic40960：35.15min，总显存62.10GiB；45056：33.42min、54.36GiB，成功。
- SP8 Actor28672 OOM；20480 25.97min/79.14GiB，17408 29.86min/78.67GiB，虽成功但余量不足。用户最终明确直接用16384生产，已训练至70。
- SP4 Actor14336因最长73127 > 14336×4断言退出，不是OOM，不可绕断言或截掉样本；SP4 Critic45056 29.65min/66.18GiB，用户决定回SP8。
- workers64 rollout18.64min；同口径trial区间32为16.71、64为18.51，随机输出和一次重试不同，无确定提速证据，生产留32。batch64至多64活跃任务，不盲试128。
- 证据 `logs/token_budget_benchmark_20261001`、`logs/token_budget_benchmark_sp4_20261001`、`logs/worker64_benchmark_v2_20261001`。fixed_batch SHA `9ccd52cbe5f871eefc7604b96117e5de24f17bf95c4161c9e2ccc8adaa240772`，不覆盖。

## 10. 给下一位agent的最小启动顺序

1. 读本文件、PI研究报告和用户新指令；区分研究设计与已验证代码，不继续旧监控任务。
2. 只读确认当前目录、源码版本/差异、资源、checkpoint和数据；PI基于当前v6数据适配，不回滚到早期6242/6075。
3. 沿真实proxy→batch→critic forward/update追踪，选定PI时序/状态内容/映射合约；检查是否已有其他agent新增实现，避免覆盖。
4. 保持Actor与SAO优化合约不变，先隔离CPU/固定小样本验证，再真实Harbor验证；旧全maskguard不属于此次PI范围。
5. 在可审计变更和验证结果基础上，再确定新实验起点、数据/配置差异与空间方案。当前未获授权删除新checkpoint或自动恢复70。

### 可直接给新agent的任务开头

> 先读 `LEGO_RL_PI_IMPLEMENTATION_HANDOFF_2026-10-05.md` 和其中的PI研究设计，在当前Lego-RL/SAO基线之上实现训练期Privileged Critic信息通路。先核对源码与数据流，严格确保生成前快照、仅Critic可见、Actor token/logprob不受污染、跨call和token映射对齐。不自动启动旧训练/评测，不删除资产；先完成实现和针对性验证，再报告需要确定的实验起点、PI预算和空间安排。旧实验与监控目前都停止。
