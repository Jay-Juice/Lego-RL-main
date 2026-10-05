# Agent Lightning SWE PPO 全量工作 Handoff

更新时间：2026-09-19 18:29 CST
用途：把当前仓库、A800 运行状态、已完成修改、实验结论和下一步建议交给新的仓库或新对话继续处理。本文件是总入口；需要复核细节时再读取文末索引的专题报告。

## 1. 当前结论

当前已经建立的是一套可恢复、评分证据较完整的 Agent Lightning 多轮 SWE PPO baseline 工程链路。训练不再因为已知评分依赖、checkpoint 或 episode 合约问题直接崩溃，但还没有证明 PPO 能稳定提高修复率。

最新 A/B 在 step40 的完整验证均为 68/470。A 为默认 Critic head，B 为零初始化 Critic head；截至本文件刷新时，两组均已至少完成 step45，训练日志仍在前进，没有 `run.exit`。零 head 没有形成持续在线优势，当前最大的学习侧疑点是 Critic 在线拟合偏弱，以及 Actor/Critic minibatch 同时从 32 放大到 128 后两者的更新次数都下降。

已经逐元素验证 step32 保存张量：终局二值奖励确实传播到同一 episode 的此前动作，`returns == episode reward`，`raw_advantages == reward - values`，最大误差均为 0。没有发现“只有最后一次提交获得 advantage”的实现错误。

最新发现的 `reliability/success/*`、`reliability/failure/*` 分组错误只影响诊断日志：旧实现把终局 call 当作成功、把成功 episode 的早期 call 错标成失败。修复已进入 GitHub 最新提交，但没有热部署到正在运行的 A/B，也不影响既有 PPO reward、GAE、loss 或验证分数。

## 2. 权威代码与路径

### Windows / GitHub

- 项目总目录：`D:\ai project\RL学习\agent-lightning-main`
- 当前 baseline V2 权威工作树：`D:\ai project\RL学习\agent-lightning-main\agent-lightning-baseline-v2-20260917`
- GitHub：`https://github.com/Jay-Juice/agent-lightning`
- 分支：`experiment/swe-baseline-v2-reliability-20260917`
- 最新提交：`de5e78a Fix episode outcome diagnostics and document PPO learning audit`
- 远端分支已经推送到 `de5e78a`。
- 工作树中的已跟踪文件干净；`research/` 下仍有若干未跟踪的历史清理计划、执行证据及临时同步清单。不要使用 `git add -A`，应逐文件选择是否纳入。

### A800

- SSH：Windows OpenSSH，host `A800`，用户 `ubuntu`
- 部署源码：`/media/ubuntu/D1/zsj/agent-lightning-baseline-v2-20260917`
- runtime：`/media/ubuntu/D1/zsj/agent-lightning-runtime`
- Python：`/media/ubuntu/D1/zsj/agent-lightning-runtime/envs/agent-lightning-d1/bin/python`
- 环境激活：`source /media/ubuntu/D1/zsj/agent-lightning-runtime/admin/activate-agent-lightning-d1.sh`
- 日志根：`/media/ubuntu/D1/zsj/agent-lightning-runtime/logs`
- 2026-09-19 18:29 D1 可用约 292 GiB，总盘使用率 98%。

Windows 源是权威源。源码修改应先在 Windows 完成，再用 WSL `rsync` dry-run 后 apply；不要直接修改 A800 源码，不使用 `--delete`。详细规则见 `A800/AGENTS.md` 和 `A800_ENVIRONMENT_AND_USAGE.md`。

## 3. 当前正在运行的两组实验

### A：默认 Critic head

- tag：`training-capo-swe-v2-full-default-4b-gpu0123-resume20-20260919-02`
- GPU：0–3
- screen：`agl-full-v2-A-gpu03-20260919-02`
- 端口：18531
- Ray 临时目录：`ray-ab-a-0919`
- 日志：`/media/ubuntu/D1/zsj/agent-lightning-runtime/logs/training-capo-swe-v2-full-default-4b-gpu0123-resume20-20260919-02`
- checkpoint 根：`/media/ubuntu/D1/zsj/agent-lightning-runtime/logs/training-capo-swe-v2-mini128-default-4b-gpu47-20260918-03/checkpoints`

### B：零初始化 Critic head

- tag：`training-capo-swe-v2-full-zero-4b-gpu4567-resume20-20260919-02`
- GPU：4–7
- screen：`agl-full-v2-B-gpu47-20260919-02`
- 端口：18541
- Ray 临时目录：`ray-ab-b-0919`
- 日志：`/media/ubuntu/D1/zsj/agent-lightning-runtime/logs/training-capo-swe-v2-full-zero-4b-gpu4567-resume20-20260919-02`
- checkpoint 根：`/media/ubuntu/D1/zsj/agent-lightning-runtime/logs/training-capo-swe-v2-mini128-zero-4b-gpu47-20260918-03/checkpoints`

18:29 只读检查：两个 screen 均存活，日志持续更新，均无 `run.exit`。两组 checkpoint 根当前都列出到 `global_step_45`；保留程序会让旧目录只剩 metadata，目录存在不等于仍有完整权重。最近明确读取的训练指标进度为 A45、B47；刷新时 A 在随后一批 rollout，B 在随后一批 Actor/Critic 更新。

旧 `research/run_ab_continuation.sh` 硬编码从 step20 恢复，而 step20 完整权重已经被保留策略轮换。以后绝不能直接重新运行这个脚本。若当前任务故障，必须先找各组最新完整 checkpoint，核对 Actor/Critic 四个 rank 的 model、optim、extra_state、`data.pt`、完成标记和期望下一批，再生成新的恢复入口。

## 4. 当前训练配方

- 模型：`Qwen3-4B-Instruct-2507`
- 数据：6248 train / 470 validation
- 计划：累计 784 global steps，4 epochs
- task batch：32 个独立任务，每题 1 条 trajectory
- Actor call minibatch：128
- Critic call minibatch：128
- microbatch：每 GPU 2
- Actor LR：`1e-6`
- Critic LR：`1e-5`
- reference KL loss coefficient：`.001`
- `gamma=1`，`lambda=1`
- PPO epoch：1
- LR warmup：0
- Critic warmup：0
- 最大 32 turns，单次 response 4096 tokens，总 context 65536
- rollout：temperature `.7`、top-p `.8`、top-k `20`
- 初始完整验证；每 20 step 完整验证；每 5 step 保存；每组保留最近 2 个完整 checkpoint
- 奖励：最终测试是否通过的二值 reward；没有 reward shaping
- CAPO 的 token PPO/GAE、call-level rows、call-mean loss 和原 token whitening 保持不变

当前 A 相对旧 baseline 的主要学习配方变化是 Actor 和 Critic 的 call minibatch 一起从 32 改为 128。B 相对 A 只增加 fresh Critic value head 零初始化。可靠性、评分、恢复和日志修改改变工程协议，因此新旧实验也不是严格单因素对照。

## 5. 实验结果总表

### 旧普通 baseline

| run | 验证结果 | 说明 |
|---|---|---|
| `training-capo-swe-pythonfull-v7-4b-gpu47-20260914-01` | step0 70/470；step20 73；step40 72 | 原 run 最后完成 step59 |
| `training-capo-swe-pythonfull-v7-4b-gpu47-resume40-20260915-01` | step40 72；step60 69；step80 50；step100 60；step120 60 | 从40恢复，最后完成126；step120 是保留恢复点 |

旧 baseline 说明 4B 原始模型具有约 15% 的随机采样修复率，但 PPO 没有展示稳定上升，后期出现明显回落。旧协议中曾混有评分基础设施和恢复问题，只能作为历史证据。

### baseline V2 有限 A/B 与当前续训

| 实验 | 初始/恢复前验证 | 20步验证 | 当前 step40 | 解释 |
|---|---:|---:|---:|---|
| A 默认 head | 71/470 | 69/470 | 68/470；02恢复前同权重随机重测74 | 没有改善证据 |
| B 零 head | 62/470 | 73/470 | 68/470；02恢复前同权重随机重测81 | 20步单次上涨，但40步没有保持 |

同一个 checkpoint 的重复随机验证可以相差多题，因此不能把 69/73、66/63、74/81 等不同采样直接连成学习曲线。当前最可靠的结论是：截至 step40，两组都没有展示可重复的修复率提升，零 head 也没有形成稳定优势。

step20 重测到 step40 的逐题配对：

- A：共同成功53，新增15，丢失21，共同失败381，精确 McNemar `p=.405`。
- B：共同成功56，新增12，丢失25，共同失败377，名义 `p=.04703`，但这是多次查看中的一次、没有多重比较校正，只能作为下降警报。
- step40 A/B：共同成功49，各自独有19，总成功数相同。
- A 提交数429→422，格式终止6→7，平均输出2441→2759 tokens。
- B 提交数434→448，格式终止3→3，平均输出2387→1863 tokens。
- 没有 NaN/Inf、optimizer skip 或明确输出/格式崩塌。

### PI 历史

- 最早 PI v1 在 baseline 相同初始验证70/470后，step20 为48/470，约 step35 停止。审查发现上下文边界和整文件/语义 hunk 序列化覆盖问题，不能视为干净的 PI 结论。
- 错误 PI V2 `p2-...20260916-03` 得到初始23/470、step20 15、step40 17、step60 14；根因是新启动器绕过 baseline 入口，丢失13项 `SMITH_*` Agent 环境配置，协议已不匹配，因此这些结果不能评价 PI 方法。
- 修正后的 PI：`training-capo-swe-pythonfull-v7-p2fixed-4b-gpu03-20260916-01`，最后 metrics 到 step91，随后因一个 incomplete episode 退出，`run.exit=1`。该 run 没有并入 baseline V2 的可靠 episode/grading 合约；不要自动恢复。其 step40 checkpoint 已按授权删除，step80 保留。
- 若在新仓库重新做 PI，必须让 baseline 与 PI 共用同一 P0 可靠性协议、Agent 配置、评分环境、恢复逻辑和超参数，只改变 Critic 可见的 privileged information。

## 6. 已完成的工程修改

### Episode 与评分可靠性

- 区分任务正常终止、生成基础设施中断、评分基础设施失败和未知结果。
- 未决评分不再静默记 reward0；同一 patch 的评分异常只允许有界重评。
- logical call ID 贯穿 agent、proxy 和事件；真实动作不因相同 prompt 被去重。
- 统一 wall deadline、request deadline、grader 和清理预留时间。
- 保存逐题 outcome、原始 patch、grader 状态、退出码和 attempt 证据。
- 验证必须覆盖全部470题且奖励完整，才允许产生有效分数。

### Checkpoint 与恢复

- Actor、Critic、optimizer、RNG、lr scheduler、dataloader 和计数都纳入完整恢复。
- 完整 checkpoint 有完成标记；恢复跳过半写入目录。
- 四 rank FSDP model/optim/extra_state 和 `data.pt` 的保存、加载、下一批一致性已经真实验收。
- 每5步保存、保留最近两点，保存串行并带空间门槛。

### 训练诊断

- 排除 dummy/padding 的 value MSE、EV、return variance、常数基线。
- token/call 权重的 raw/whitened advantage 统计。
- old/reference/rollout sampled k3 均值与尾部。
- 真实 optimizer attempted/actual/skipped 次数、行为和验证统计。
- 非有限梯度在所有 rank 一致停止，不再只跳过后继续。
- Critic fresh value head 可选零初始化；resume 不会重置已有 head。

### SWE 评分环境

- 发现 pydicom 官方测试会在离线容器请求79个数据文件，导致候选和 reference 都超时。
- 已加入固定文件、SHA 校验与容器回环 HTTPS fixture；不开放外网、不关闭 TLS、不修改官方测试和 reward。
- 参考补丁与候选补丁的真实重放、65项回归、124镜像环境审计通过；当前 A/B 已实际通过旧 step23 的该任务。

### 测试证据

- P0 定向 CPU 回归曾达到156 passed，另有26 subtests passed。
- checkpoint 四卡 roundtrip、optimizer/RNG/dataloader 恢复与首批更新通过。
- 最新 episode 成败分组修复在独立目录通过22项 CPU 测试，并用 A/B step32 真实张量回放。
- Windows Python 没有 torch，本地 pytest skip 不算通过；有效测试结果来自 A800 隔离 CPU 环境。

## 7. 深入诊断与必须保留的解释边界

### 奖励传播正常

A/B 的 `ppo-audit/step-000032.pt` 与 JSON 已检查。按真实 `rollout_id` 排除 pad 后，所有有效动作的 return 都是 episode 终局奖励，raw advantage 都是 reward 减 value。当前没有证据支持奖励只训练最后一次提交。

### Critic 在线预测较弱

- 21–40步相对“该批 return 均值常数”的事后 MSE 对照，A 只有3/20批更好，B为11/20批。
- 31–40平均 EV：A `.04197`，B `.03882`。
- step32 A：成功 token value `.5765`、失败 `.5514`，MSE `.29864`，EV `.0131`。
- step32 B：成功 `.3441`、失败 `.1925`，MSE `.08251`，EV `.1347`。
- 零初始化在固定轨迹 P1 中有明显冷启动优势，但在线优势没有保持。

这些结果支持进一步检查 Critic 训练预算，但不能单凭 MSE 宣布 Critic 是唯一根因；whitening 会消去整体偏置，batch 常数也是事后 oracle，不是部署模型。

### KL 日志不能跨 minibatch 直接比较

vendor `dp_actor.py` 的 `actor/kl_loss` 和 `actor/pg_loss` 会跨 minibatch 累加。minibatch 32→128 后 optimizer/minibatch 数减少，累加量自然变小。跨配方应使用统一分母的 `reliability/sampled_k3/old_vs_ref/mean` 或 call mean，并写清权重。

统一 token k3 均值：A 21–30 `.01770`、31–40 `.03073`、41–45 `.04964`；B 对应 `.02705`、`.04110`、41–47 `.05166`。参考偏离在增加，但后期两组接近。A step22 的 old-vs-rollout 均值4.42被一个极端 token 主导，不能把它解释成整批普遍错配。

### 当前采样限制

每批只有32个独立任务、每题一条 trajectory。几百个 call/token 不是几百个独立样本。成功轨迹通常比失败轨迹短，而 loss 是 call 等权、whitening 是 token 等权，存在长度和任务权重偏差的候选解释，但尚未证明它是 bug。

逐 token GAE 跨越数千 token，不能直接把 `gamma` 或 `lambda` 改成 `.95`；终局信号会快速衰减。CAPO 中见到的 `1.2` 是 ratio/clip 相关阈值，不是 KL 系数。当前 KL `.001`；`.005` 只应作为独立消融。

## 8. 建议新仓库首先做的实验

第一优先不是再盲跑784步，而是把 Actor 保守更新和 Critic 拟合预算拆开：

1. 使用同一批已保存固定轨迹、同一个完整 Critic 起点，冻结 Actor。
2. 只比较 Critic call minibatch 128 与32；LR都保持 `1e-5`，pass数、数据顺序、head初始化和 GAE 都相同。
3. 按完整 episode 划分 fit/check，避免同一 episode 的 call 泄漏。
4. 记录独立 check 的 MSE 相对常数、EV、bias、耗时和真实 optimizer 次数。
5. 若 Critic32 在独立 check 上稳定改善，再从相同完整 checkpoint 做20步在线候选：Actor128、Critic32，其余不变，完成470题验证。
6. 若更小 Critic minibatch 振荡，再单独测试 Critic LR `1e-5 → 3e-6`。
7. Critic 配方确定后，才单独做 KL `.001 → .005`，使用规范化 k3 和逐题修复结果评估。

不要同时修改 minibatch、LR、KL、head、warmup 和 GAE。不要仅凭 loss 有限或没有 crash 宣布 baseline work。当前 A/B 应至少等到 step60 完整验证再判断是否继续；如果配对修复率继续下降，应暂停长训并保留最新完整 checkpoint。

## 9. 迁移到新仓库的建议顺序

1. 从 GitHub 分支 `experiment/swe-baseline-v2-reliability-20260917` 的 `de5e78a` 开始，或将该分支按功能拆成小提交移植。
2. 先移植 P0：episode contract、评分分类、checkpoint完整性、全量验证门槛和环境审计。
3. 再移植 pydicom 离线 fixture；若新仓库的sandbox镜像/数据不同，重新运行124镜像审计，不直接复用旧 signature。
4. 运行 CPU 定向测试，再做四卡真实 checkpoint roundtrip；不要从一次 mock checkpoint 测试推断 FSDP 恢复正常。
5. 使用新 tag、新端口、新 Ray 目录和新日志目录；不要覆盖当前 A/B。
6. 新仓库如果仍使用当前 A800 八卡，先处理当前 A/B 的去留或选择空闲卡。当前两组占满0–7卡，本 handoff 不授权自动停止它们。
7. 从新模型/新代码 fresh start 时必须先完成470题初始验证，不能把训练过的恢复点验证当作基座性能。
8. 新 baseline 稳定后，再复制完全相同配方实现 PI，只改变 Critic 输入。

建议从当前分支选择性移植的核心目录：

- `agentlightning/verl/episode_contract.py`
- `agentlightning/verl/reliability_control.py`
- `agentlightning/verl/reliability_metrics.py`
- `agentlightning/verl/checkpoint_retention.py`
- `agentlightning/verl/critic_initialization.py`
- `agentlightning/verl/call_batch_config.py`
- `agentlightning/verl/trainer.py`
- `agentlightning/verl/full_dataset.py`
- `examples/multiturn_ppo/reliable_launch.py`
- `examples/multiturn_ppo/run_reliable_full_python_ppo.sh`
- `examples/multiturn_ppo/check_full_python_ready.py`
- `examples/multiturn_ppo/audit_full_python_envs.py`
- `examples/multiturn_ppo/swe_reliability.py`
- `examples/multiturn_ppo/swe_grading_evidence.py`
- `examples/multiturn_ppo/pydicom_http_fixture.py`
- 对应 `tests/verl/`、`tests/examples/` 和 `tests/server/` 测试

vendor CAPO Actor/Critic/PPO/GAE 核心算法文件在本轮核验时与来源 hash 一致；不要为了迁移顺手重写核心 PPO。`multi_turn_ppo.py` 的奖励传播也已通过实际张量检查。

## 10. 运维和清理注意事项

- 每个完整 Actor+Critic checkpoint 约91.36 GiB；两组各保留2点，磁盘峰值压力很大。
- 当前保存预检要求写前约112 GiB空闲；新启动门槛曾设295 GiB，用于容纳轮换峰值。当前292 GiB略低于新启动门槛，不代表现有训练保存已经失败。
- 已按授权删除过旧 baseline step40、step80及错误 PI step40等明确目标；不要重复运行历史清理脚本或扩大范围。
- 当前保留旧 baseline step120、旧 PI step80、当前 A/B 最新两组完整恢复点和全部日志。
- 禁止全局 `pkill`、`ray stop`、Docker prune 或模糊路径递归删除；只操作已核验 PID、screen、端口和绝对路径。
- 评分中的 `succeeded` 表示 rollout 执行完成，不表示任务修复成功；成功必须看 reward/grade。
- metrics 在验证后及保存后可能对同一 step 重复写入完全相同记录，分析时按 step 去重，不能当作两次验证。
- 自动巡检任务 id 为 `3-swe-ppo`，应用中处于 ACTIVE；名称写“每90分钟”，实际 RRULE 是每120分钟。它应继续只读监控当前 A/B，除非用户明确暂停或迁移它。

## 11. 关键提交

- `8441823`：P0 可靠 episode 合约与恢复保护
- `5e8b2d5`：固定轨迹 Critic 初始化诊断
- `e602e21`：零 head 在线候选和四 rank 恢复
- `8e0e473`：固定 patch 重放与候选失败分类
- `fcb224e`：Python exit120 评分恢复
- `017a500`：双四卡续训入口
- `fd0179e`：pydicom 离线官方数据 fixture
- `8a45543`：step40 配对分析
- `de5e78a`：episode级成功/失败诊断修复与深入报告

活跃 A/B 启动时没有加载 `de5e78a` 的分组指标修复。未来新仓库应使用修正版；分析当前旧日志时不得按旧 success/failure call 分组解释 episode 成败。

## 12. 文档索引

建议新的接手者按以下顺序阅读：

1. `SWE_AGENT_LIGHTNING_COMPLETE_HANDOFF_2026-09-19.md`：本总 handoff。
2. `SWE_BASELINE_V2_DEEP_DIAGNOSIS_2026-09-19.md`：奖励传播、Critic、KL 与下一实验的最新结论。
3. `SWE_BASELINE_V2_GRADING_FIX_2026-09-18.md`：A/B 从启动、评分修复、checkpoint清理到step40的完整时间线。
4. `SWE_BASELINE_V2_IMPLEMENTATION_PLAN_2026-09-17.md`：P0/P1/P2设计和验收标准。
5. `SWE_BASELINE_V2_P0_IMPLEMENTATION_2026-09-17.md`：可靠性代码与测试。
6. `SWE_BASELINE_V2_P1_CRITIC_DIAGNOSTIC_2026-09-17.md`：固定轨迹 default/zero head 诊断。
7. `SWE_BASELINE_INTEGRATED_REVIEW_2026-09-17.md` 与 `SWE_BASELINE_DIAGNOSIS_AND_RERUN_PLAN_2026-09-17.md`：旧 baseline 失败模式和综合判断。
8. `SWE_PI_V2_ROOT_CAUSE_REVIEW_2026-09-16.md`、`SWE_PI_V2_FIXED_RESTART_HANDOFF_2026-09-16.md`：旧 PI 配置错误和修复过程。
9. `AGENT_LIGHTNING_PRIVILEGED_CRITIC_RESEARCH_2026-09-09.md`、`SWE_SANDBOX_STATE_PRIVILEGED_CRITIC_DESIGN_2026-09-14.md`：最初 PI 研究与设计。
10. `A800_ENVIRONMENT_AND_USAGE.md` 与 `A800/AGENTS.md`：服务器环境和操作约束。

## 13. 最短接手摘要

代码在 GitHub 分支 `experiment/swe-baseline-v2-reliability-20260917@de5e78a`。A800 两组 Qwen3-4B PPO 当前仍占用0–7卡，最近完整验证 step40 都是68/470，当前没有学习收益证据。奖励传播已验证正确；旧 success/failure 诊断分组有 bug，已在最新提交修复但未热部署。下一项最有价值的实验是固定轨迹下只对照 Critic minibatch128/32，然后才决定 Actor128/Critic32 的20步在线候选。迁移时先复用可靠 episode、评分、checkpoint和环境审计，不要直接复制旧的硬编码 step20 恢复脚本，也不要把旧 PI 或旧 baseline 的随机验证拼成一条因果学习曲线。
