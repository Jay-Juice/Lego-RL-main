# Lego-RL：SWE benchmark 与 Privileged Critic 迁移调研

调研日期：2026-09-19，Asia/Shanghai。服务器状态是本轮 SSH 只读检查结果；历史实验数字来自明确标注的 handoff/结项报告。本轮只新增本文，未修改训练代码、安装环境、部署、启动或停止任务，也未提交或推送 Git。

## 1. 结论

Lego-RL 适合承载当前 idea：已经有真实 coding harness、Harbor sandbox、生成时 token/logprob 记录、带 Critic 的 GAE 路径，以及同步/异步训练。不过它不是此前 Lightning/CAPO 的同一套训练表示，迁移需要重接数据通路，不能整体搬旧 trainer。

建议首先做单机 Docker + 同步训练 + FSDP + 一个固定 harness，以现有 Qwen3-4B-Instruct-2507 为第一候选。先打通普通 Critic baseline 和可靠评分，再只改变 Critic 的信息输入。SAO 可以作为后续算法对照，但其默认配方不等于普通 PPO。

已有资产可显著降低成本：SWE-smith Python 6248/470 数据、全部 124 个所需镜像 digest、Qwen3 权重、独立 SWE-bench harness 都还在。现有 Python 训练环境与 Lego-RL 的依赖版本不匹配，应新建隔离环境，不原地升级正在运行的环境。

两项优先问题：

1. 旧 470 题是 SWE-smith validation，不是 SWE-bench Verified。当前查到的官方 SWE-bench 镜像只有 3 道 Lite/SymPy 试跑题；正式 benchmark 还需要准备。
2. 默认启动脚本会全局停止 Ray、按进程名 kill，并清理共享内存。在共享 A800 上实际启动前必须改为实验级资源管理。

## 2. 项目和资料地图

```text
D:/ai project/RL学习/Lego-RL-main/              当前工作区外层
├── A800/                                    服务器操作/安装指南
├── SWE_AGENT_LIGHTNING_COMPLETE_HANDOFF_2026-09-19.md
└── Lego-RL-main/                             实际 Python 项目根
    ├── src/verl_patch/                       agent loop / proxy / configs
    ├── src/harbor_patch/                     harness 和 sandbox 适配
    ├── patches/                             verl / SAO / vLLM 补丁
    ├── scripts/                             安装、训练、推理、评测、配置模板
    ├── utils/                               数据转换、index、grader、权重合并
    ├── tests/agent_loop/                     本地可见测试
    ├── docs/                                文档网站
    └── webui/                               日志与轨迹仪表盘
```

当前外层和内层都没有 `.git`；内层也没有安装后的 `third_party/` 或 `.venv/`。这是源码快照，不是已经可运行的训练工作树。`src/verl_patch` 主要负责集成，核心 trainer/engine/GAE 仍依赖 setup 下载并打补丁后的 verl。

GitHub 目标为 <https://github.com/Jay-Juice/Lego-RL-main>。本轮 `git ls-remote https://github.com/Jay-Juice/Lego-RL-main.git` exit 0，但没有任何 refs，符合尚未有提交的空仓库状态。浏览器抓取和 REST 元数据未成功，不能进一步确认默认分支/权限；尚未验证 push 权限。后续应先建立干净的上游源码起点、记录来源，再在该仓库维护项目改动；不需要把历史 Lightning 工作树全部并入。

本轮重点交叉阅读的参考资料：

- 同级 `Agent-R1/privileged_critic_agentic_rl_idea.md`：研究定义、对照与信息边界。
- `PRIVILEGED_CRITIC_PROJECT_HANDOFF_2026-09-02.md`、`handoff.md`：P1 current facts、相对初始状态的 Delta、旧 step-level 路线。
- `TOKEN_GAE_PRIVILEGED_CRITIC_GUIDE.md`、`CAPO_PRIVILEGED_CRITIC_RESEARCH_2026-09-06.md`、`CAPO_P1_HANDOFF_2026-09-09.md`：token GAE、Critic 双入口、历史配方边界。
- `CAPO/CAPO-main/CAPO_P1_FINAL_2026-09-10.md` 和 `diagnostics/p1_late_collapse_side_20260910/FINDINGS.md`：比早期 handoff 更新的最终结果与机制调查。
- `PRIVILEGED_CRITIC_LOGGING_SPEC_FOR_VERL_AGENT.md`：作为日志设计参考，不把所有字段和频率自动当成新实验要求。
- 当前外层 Lightning 总 handoff，以及同级 `agent-lightning-main` 中的 SWE 状态设计、PI-v2 审查、环境指南和实际 PI 模块。
- Lego-RL 的 README、依赖/安装脚本、训练模板、agent loop、proxy、SAO 补丁、Docker 环境、数据工具、相关测试与文档。

这是架构和迁移可行性调研，不是对所有前端文件和全部第三方补丁逐行完成正确性证明。

## 3. 对 idea 的准确理解

Actor 使用部署可见历史 H_t；训练期 Critic 使用 V(H_t, Z_t)。Z_t 来自当前 model call 生成之前的环境状态，reward、Actor 输入、old/ref logprob 和 Actor 推理接口保持一致。

SWE 的候选 Z_t 是沙箱控制面读取的工作区状态与进程/socket 状态。Delta 表示相对 prepared 初始状态 S_0 的当前净变化 D(S_0, S_t)，不是追加所有历史事件。修改后恢复的文件应从净变化中消失。

token-level value 对应 V(H_t, Z_t, a_{t,<k})。同一次 model call 使用同一个生成前快照；当前 token 不得看到当前动作执行之后的文件变化，也不能看到后续 call 的 Z。

第一版应延续已有边界：不使用 reference patch、未来轨迹、终局分数或动作后的 hidden test verdict 作为当前 baseline 的信息。SWE 中很多状态原则上能通过 Actor 工具查询，研究价值是训练时的额外状态可见性和避免重建/查询成本，不宜把它一概描述成 Actor 永远无法获取的信息。

历史结果不支持提前假定 PI 必然提高最终修复率：

- CAPO 1.7B 最小 P1 的结项报告：baseline 252/274，P1 240/274；P1 中期更快、最终更低。不能使用 09-09 尚未完成的快照代替最终结果。
- Lightning 09-19 总 handoff：A/B 在 step40 都是 68/470；实际张量已验证终局奖励传播，尚无稳定学习增益证据。
- EV/MSE 改善、Actor 泛化、梯度方差是不同问题。首 token、全 token、按完整 episode 分组的固定轨迹诊断应与最终任务分数一起看。

## 4. Lego-RL 的现有数据流

```text
task index parquet
  -> BuiltinSWEAgentLoop
  -> Harbor Trial / coding harness / sandbox
  -> in-process API proxy
  -> verl server_manager.generate
  -> proxy 保存 token IDs / response_mask / generation logprobs
  -> Harbor verifier reward
  -> AgentLoopOutput（整条多轮轨迹）
  -> verl batch / values / GAE / Actor 与 Critic update
```

具体入口：

| 位置 | 当前作用 | 迁移用途 |
|---|---|---|
| `src/verl_patch/agent_loop/builtin_swe_agent_loop.py` | 创建 Trial、读取评分、组装轨迹 | episode/outcome 合约、PI 元数据交付 |
| `src/verl_patch/agent_loop/vllm_chat_completion_proxy.py` | 逐次 model call、token 轨迹、历史改写 | call 身份、生成前 snapshot hook、token span 映射 |
| `src/harbor_patch/environments/remote_docker.py` | Docker sandbox/runtime | 状态采集 adapter、离线 runtime |
| `src/harbor_patch/agents/*` | OpenHands/Claude Code/OpenCode 等 | 固定一个 harness，检查工具/调用生命周期 |
| `patches/verl_7aed6b23.patch` | 基础 verl 扩展 | batch/worker/训练接线的版本基底 |
| `patches/verl_sao_7aed6b23.patch` | GAE、value engine、reward placement、filter | 可复用能力；不代表必须启用整套 SAO |
| `scripts/train/lib/hydra_args.sh` | Actor/Critic 配置映射 | 明确设置 baseline 超参，避免继承错配 |
| `utils/create_task_index.py` | Harbor 目录 -> parquet registry | 新建 SWE-smith/官方 benchmark 的 task adapter |
| `webui/` | 日志、逐题与轨迹展示 | 复用展示；增加少量 PI 与固定诊断指标 |

默认是 GRPO advantages + GSPO loss，Critic 默认关闭。只把 estimator 改成 GAE 不足以得到预期 PPO；还要显式配置 policy loss、Critic、KL、clip、gamma/lambda、归一化及 batch 单位。

### PPO 与 SAO 必须分开命名

`scripts/templates/verl/sao.env` 同时设置：单 rollout、GAE、DIS/REINFORCE、没有 reference KL、长度自适应 policy lambda、独立 critic lambda、冻结 attention、更多 Critic 更新和 warmup。这是另一套算法配方。

若第一目标是复现原 idea 的受控 PPO 对照，建议普通 PPO vs 同配方 PI-PPO；若决定用 Lego 的 SAO recipe，则应做 SAO vs 同配方 PI-SAO。不能以“SAO 有 Critic”为由将其当作旧 PPO 原样迁移。

仓库提供的单机 Qwen3-8B SAO 配置明确只是 plumbing smoke，原文指出该模型在那套 OpenSWE 任务上几乎无正奖励；不能把该配置视为 A800/4B 上已经验证有效的学习配方。35B 的论文/README 结果也不能外推到现有 4B。

## 5. PI 的主要接入难点

### 5.1 旧 call rows 与新 full trajectory 不同

Lightning 的 `critic_batch_view` 假定每行一个 call，可以把额外 PI 放在 prompt 中，再拼接与 Actor 完全相同的 response。Lego 的 response 区包含多轮模型输出和工具 observation，不能给整条轨迹前缀一次性塞入所有 Z_t：那会让早期价值预测看到未来状态。

候选设计 A：保持 Actor 轨迹不变，为 Critic 构造按时间交错的独立序列：

```text
H_0, Z_0, A_0, O_1, Z_1, A_1, O_2, Z_2, ...
```

只在对应 action 之前插入该轮 PI。单独保存 Actor token -> Critic token 的索引，Critic 前向和更新都使用这套映射；将 values gather 回原始 Actor response 形状后计算 GAE。PI/observation/padding 不进入 GAE 时间步或 value loss 的监督 token。

候选设计 B：Critic 按真实 call 的 `(H_t, Z_t, A_t)` 单独前向，随后把 values 映射回整条轨迹；Actor 仍按原生 full trajectory 更新。它更接近旧实现，但重复 history 的计算/显存成本可能很大，loss 权重必须保持等价，不能因拆 call 顺便改变优化目标。

两种方案需要在固定轨迹上对比输入长度与显存，再确定实现。当前没有假定简单增加四个 tensor 字段就足够。

### 5.2 call 身份与 snapshot 一致性

需要记录 `episode_id / sandbox_id / logical_call_id / attempt_id / state_seq / action_token_span / snapshot_hash`。在真正生成前采集状态，通过 side channel 送给 Critic；不能写进发往模型的 Actor HTTP messages。

要处理 proxy 的历史重写、context compaction、partial rollout 重试和 subagent session。第一版固定单 harness、同步训练、尽量单顺序工具流，可以减少额外变量，但仍要验证这些情况是被禁止还是被正确支持。

进程/文件 snapshot 是有持续时间的读取，后台进程可能继续写文件。时间戳只能证明读取发生在生成之前，不能证明跨文件原子一致；应记录范围、时长、缺失/冲突，避免宣称完整原子状态。

### 5.3 复用旧模块的边界

同级 Lightning PI-v2 中可参考的模块：

- `agentlightning/privileged_state/baseline.py`：冻结 prepared buggy tree 的 path -> blob。
- `sandbox.py`：文件/进程/socket snapshot 和净变化。
- `semantic_diff.py`：内容 hunk。
- `serialize.py`：有预算序列化。
- `agentlightning/verl/privileged_critic.py`：不修改 Actor tensor 的独立视图原则。

这些应选择性移植并适配 Harbor，不能直接指向旧 runtime package。PI-v2 审查已发现过 hunk 只保留部分 chunk 却标记 `truncated=false`；新实现必须按 changed lines/chunks/records 真实覆盖率记录。context 预算应在生成前预留约定 response 空间，不能用事后实际 response 长度给 PI 扩容。旧 checkpoint 不能直接当作新版 verl 的完整可恢复 checkpoint；若需要 warm-start，先独立验证导出权重和 value head。

## 6. 必须先解决的工程问题

### 6.1 启动脚本与共享机器冲突（源码已确认）

`scripts/train/lib/ray.sh:cleanup_ray_and_shm` 包含 `ray stop --force`、`pgrep ... | kill -9`、`/tmp/ray/*` 与 `/dev/shm` 广泛清理；实际训练入口会调用它。退出 trap 也全局停止 Ray。`scripts/lib/ray_bringup.sh` 有相似行为。

需要实验专属 Ray 地址、短 temp 路径、GPU 列表、端口和进程所有权记录；清理只处理当前实验拥有的资源。配置不同端口本身不能抵消全局 cleanup。本轮没有执行这些脚本。

### 6.2 评分失败仍有混成 reward0 的路径（静态发现，待运行复现）

`builtin_swe_agent_loop.py` 把缺失 verifier 的 reward 默认成 0；nonzero agent exit 分支可以在没有 verifier verdict 时标为 completed。所有 retry 都无 verdict 后，默认 `trial_reason` 仍可能是 completed，并保留最后一次 partial token metadata。若这些 tokens 有效，后续是否正确排除必须补针对性验证。

已有 `termination_reason` 和 trajectory filter 是好的基础，但不能等价于 Lightning V2 的“未决评分不得当失败样本”合约。建议分开 task failure、agent budget、generation failure、grader failure、unknown；重评固定 patch，避免失败时重新生成把评测变成隐含 best-of-retries。验证须检查全部预期 instance 的覆盖与 verdict 完整性。

### 6.3 数据格式与运行时依赖尚未接好

Lego 消费的是 Harbor task directories + index parquet，旧 JSONL 不能直接换个路径使用。需生成 task.toml、instruction、environment 与 verifier，保留源 instance ID、split、镜像 digest、测试协议和 fixture 来源。task index 只是指针，不是完整任务内容。

旧 Docker 镜像缓存里没有已检查配置所需的 OpenHands SDK runtime 镜像；Harbor/OpenHands SDK 也不在旧训练环境。`RemoteDockerEnvironment` 默认 runtime staging 在 `/opt/harbor-agent-runtime-cache`，本次服务器上不存在，应改为项目适用位置并检查离线运行行为。部分 runtime 路径无条件 pull，不能把“缓存过镜像”当成“完全离线可用”。

### 6.4 安装并非完全固定且可直接离线重放

setup 默认 Python 3.12.3、verl v0.8.0、vLLM v0.19.0，Harbor 则是 `Elvin-Yiming-Du/harbor` 的 `main`，不是固定 SHA。开始正式实验前要 pin Harbor SHA，保存全部 upstream SHA 和 patch hash，并验证补丁正向应用。

requirements 同时列出多种 CUDA 12/13 组件，不能直接用作 A800 已验证的二进制兼容结论。现有 FlashAttention wheel 对应旧 torch2.9 ABI，不能当作 torch2.10 的可复用二进制。vLLM 官方也建议独立环境，并强调 wheel 与 PyTorch/CUDA 构建匹配：[v0.19 安装文档](https://docs.vllm.ai/en/v0.19.0/getting_started/installation/gpu/)。

## 7. A800 实测资产与环境复用

本轮首个状态快照服务器时间：2026-09-19 18:43 CST。之后完成了 package metadata、数据行数和 Docker digest 只读核验。以下不表示做过新的 GPU smoke。

| 项目 | 实测状态 | 复用判断 |
|---|---|---|
| SSH | `A800`，ubuntu，成功连接 | 可继续使用既有方式 |
| GPU | 8 × A800 80GB PCIe；驱动 550.144.03 | 硬件可用；当时 0–7 全部被现有实验占用 |
| D1 | `df -h` 约 447G 可用、97% 已用 | 是瞬时快照，会随旧 checkpoint 轮换变化 |
| 主机内存 | 约 1 TiB，available 约 474 GiB | 容器并发需与现有任务协调 |
| 系统 | x86_64，glibc 2.35 | 新二进制仍需实际兼容检查 |
| Docker | 28.0.4，Compose 2.34.0，overlay2 | daemon 可访问，不需要重新部署 Docker |
| Docker 数据根 | `/media/ubuntu/D1/zsj/agent-lightning-runtime/docker` | 可共享既有镜像，勿迁移/清理 |
| 所需 SWE-smith 镜像 | 数据引用 124 个 digest，匹配 124，缺失 0 | 全部镜像身份可复用；新 verifier 仍需重验 |
| 校内 PyPI | `10.250.0.80/.../packaging/` HTTP 200 | 镜像仍可达；未验证全部新版本可下载 |
| 旧联网隧道 | 127.0.0.1:17890 connect refused | 旧代理链路目前未在监听，下载前需恢复/另行配置 |

当前存活的两组 Lightning screen：

- `agl-full-v2-A-gpu03-20260919-02`
- `agl-full-v2-B-gpu47-20260919-02`

本轮没有停止、重启或热修改它们，也没有重新计算它们的验证成绩。

### Python 栈对照

| 环境 | Python | torch | vLLM | verl | transformers |
|---|---|---|---|---|---|
| D1 `agent-lightning-d1` | 3.12.14 | 2.9.0+cu129 | 0.12.0 | 0.7.1 | 4.57.6 |
| `~/.conda/envs/agent-lightning` | 3.12.14 | 2.9.0+cu129 | 0.12.0 | 0.7.1 | 4.57.6 |
| `~/.conda/envs/agentic-rl` | 3.12.13 | 2.8.0 | 0.11.0 | 0.7.0 | 4.57.3 |
| `~/.conda/envs/agent-r1` | 3.10.20 | 2.6.0 | 0.8.5.post1 | 0.7.0 | 4.57.5 |
| Lego 本地依赖目标 | >=3.12,<3.14 | 2.10.0 | 0.19.0 | v0.8.0 + 项目补丁 | 5.4.0 |

上述旧训练环境都没有 Harbor。Python 小版本满足条件不意味着整个环境兼容。安装版本 metadata 是本轮事实；editable 包的实际执行代码仍应在新部署时验证 `__file__`/SHA，不能只看 distribution version。

独立官方评测环境仍在：

```text
/media/ubuntu/D1/zsj/agent-lightning-runtime/envs/swe-bench/bin/python
Python 3.12.14 / swebench 5.0.2
```

可以用于新导出的 patch 评分，与 Lego 训练依赖分离；本轮确认解释器和包 metadata，没有重跑官方 harness。

本地 Windows Python 为 `D:/anaconda/anaconda3/python.exe`、3.13.5，没有 torch。因此未把本地 pytest skip 或源码可读当作训练测试通过。

### 模型与数据

已有模型根：`/media/ubuntu/D1/zsj/GOPD/G-OPD-main/models`。本轮读取 config 并确认 safetensors 文件存在的模型包括 Qwen3-4B-Instruct-2507、Qwen3-8B、Qwen3-1.7B、Qwen3-30B-A3B-Instruct-2507。没有全量重新 hash 权重，也没有加载到 GPU。4B instruct 可优先复用，但换 OpenHands harness 后应重新测原始能力和工具格式。

旧训练数据：

```text
/media/ubuntu/D1/zsj/agent-lightning-runtime/data/swe-smith-training/python-full-v7/
  train.jsonl     6248 行
  val.jsonl        470 行
```

实读 `data_source=async_swe_smith`，instance ID 为生成式 SWE-smith ID。470 验证集中 pdfminer 占 122、pandas 占 82 等，分布与官方 Verified 不同。建议保留用于开发期同口径比较，最终单独做官方 benchmark。

IERS、pydicom 等离线 fixture 目录仍存在，旧修复经验可用，但新容器协议下重新检查挂载、SHA 和判分等价。

已检查的 HF cache 只有 SWE-bench Lite dataset；官方镜像为 SymPy 20590、20639、20442 三题。这三题可作为最小评测检查，不是有代表性的 benchmark。未对服务器其他用户/项目目录进行全盘数据搜寻。

## 8. 建议实施顺序与验收

1. **建立仓库基线与运行隔离。** 将内层源码作为清晰项目根纳入新 GitHub 仓库，记录上游 provenance；修正实验级启动/退出清理；确定新服务器源码/运行路径。当前尚无新 Lego 远端目录约定，不猜测并创建。
2. **准备独立 Lego 环境。** 固定依赖、Harbor SHA、补丁 hash，选择匹配 A800 的 CUDA/PyTorch/vLLM/FlashAttention；先 import/CPU 检查，再等可用卡做最小 GPU 路径。保留现有训练环境。
3. **任务和评分接入。** 先复用 3 个官方试跑题与少量跨仓库 SWE-smith；验证 gold/empty/failing patch、完整判分、timeout/infra 分类。复用 124 个镜像构建 Harbor adapter，不能复用旧审计 signature 直接宣布通过。
4. **普通 Critic baseline。** 单固定 harness、同步 PPO、n=1，从同一个基础模型重新测初始能力。显式冻结实验协议，而不是复制混杂的模板默认。证明多轮 token/reward/GAE 和一次完整 Actor/Critic 保存恢复。
5. **Critic-only PI。** 先在固定轨迹上验收时序、Actor/ref 隔离、value 映射、两处 Critic 入口、上下文预算、packed/unpacked 一致性；再做同配方 baseline/PI 对照。fit/check 按完整 episode 切分。
6. **正式 benchmark。** 可先完成 Lite 工程链路，再准备 Verified；官方任务作为独立泛化评测，不拿旧 470 的分数替代。导出 `instance_id/model_name_or_path/model_patch` JSONL，用独立官方 harness 交叉验证。每次不同 patch/重评用新的 run ID，避免复用缓存结果：[官方评测文档](https://www.swebench.com/SWE-bench/guides/evaluation/)。
7. **结果稳定后扩展。** SAO、异步、多 harness、模型规模和更广 benchmark 分别成为独立实验轴；一次只引入可解释的变化。

建议最小日志集合：resolved config 与源码/环境/数据 manifest；逐 episode 的 patch/outcome/grade evidence；model call 的原始 token/span/hash；首 token 与全 token 的 MSE/EV/bias/return variance；raw/whitened advantage；真实 Actor/Critic optimizer 次数；PI coverage/fallback/采集成本；全部逐题验证结果。长轨迹内容抽样压缩保存，标量和完整验证证据持续保留。

## 9. 本轮已验证与尚未验证

已执行：本地目录/源码/文档读取；Git 只读 refs 查询；SSH 主机/GPU/磁盘/screen/Conda 查询；直接 Python metadata 查询；JSONL 行数与字段检查；Docker daemon/Compose 查询；124 个所需 digest 与本机 RepoDigests 集合比对；模型 config/文件存在检查；校内镜像 HTTP 和旧隧道端口检查。

代表性只读命令（实际使用 Windows OpenSSH，不使用 ssh.bat）：

```powershell
& 'C:/Windows/System32/OpenSSH/ssh.exe' -o BatchMode=yes -o ConnectTimeout=10 A800 '<read-only command>'
git ls-remote 'https://github.com/Jay-Juice/Lego-RL-main.git'
```

远端查询包括 `nvidia-smi --query-gpu=... --format=csv`、`df -h`、`screen -ls`、`conda env list`、`docker info`、`docker image inspect` 和 `python -B -`。未调用训练 launcher、Docker run/build/pull、全局清理、rsync 或安装器。

尚未验证：Lego 依赖解析/安装、当前补丁对 upstream SHA 的实际 apply、Harbor 导入与 task 转换、snapshot adapter、Lego GPU 前后向、四卡 checkpoint roundtrip、完整官方 benchmark、push 权限。静态发现与设计建议不等于上述执行已通过。

操作规则以当前 `A800/AGENTS.md` 和安装指南为准。旧项目的 D1 自定义 Conda 路径是历史状态，不自动覆盖当前指南对新环境位置的约束；实施环境准备时再明确记录新路径。本文不包含启动新训练或改变现有 A/B 的授权。
