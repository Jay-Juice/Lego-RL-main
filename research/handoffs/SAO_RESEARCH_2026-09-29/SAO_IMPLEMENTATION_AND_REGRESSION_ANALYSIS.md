# SAO实现与性能退化审计

2026-09-29。核查范围：本地权威源码、A800实际Hydra参数与成功训练链日志、逐题评测记录、LEGO-RL公开代码及SAO原论文。生产源码、配置、模型、数据均未修改；没有恢复训练或重跑评测。

**结论：有明确的工程问题，也有显著的实验配方差异，但目前没有证据证明SAO核心公式接错。最强的训练异常是Critic长期预测能力偏弱；冷启动、小batch、数据分布与截断共同造成不良更新，是优先验证的解释。不能把“还有bug”或“只要继续训练就会涨”当成既定结论。**

当前实验应称为“Qwen3.5-9B / SWE-Smith / 单节点同步SAO适配实验”，不能称为官方成功实验或原论文的严格复现。我们此前对“主要算法参数一致”和“完整训练配方一致”的区分不够充分。

**证据范围与版本**

- Windows外层：`D:/ai project/RL学习/Lego-RL-main`；源码仓库在其下`Lego-RL-main`。
- A800运行根：`/media/ubuntu/D1/zsj/Lego-RL-main`。
- 本次固定LEGO-RL上游提交：`a3e28f171be165b5e8cda45030f336ec103690a7`，2026-09-28；这是调查时的公开版本，不假定它就是最初部署日版本。
- 运行verl基线：`7aed6b230776f963fa09509c10d9c3a767d1102c`，叠加LEGO SAO patch及适配。
- 本地SAO模板、35B生产recipe与固定上游逐字节一致。SAO patch文件只有agent-loop补丁上下文适配差异，没有DIS/GAE数学改动。BuiltinSWEAgentLoop主要本地差异是独立验证预算、严格verdict判定及metadata；完整diff和SHA见`upstream_comparison.json`与两个`.diff`文件。
- 论文：DeepXiv执行`deepxiv paper 2607.07508 --brief`作索引；算法与参数从原文核对，未把机器摘要当作原文证据。

**成绩是整体退化伴随波动，不是每个checkpoint单调下降**

按用户最新要求，未决在本表计失败；原始审计文件仍保留未决状态，不把超时伪造为正式reward=0。

| 模型 | 通过/500 | 通过率 | 相对base百分点 |
|---|---:|---:|---:|
| base | 279 | 55.8% | — |
| step20 | 272 | 54.4% | -1.4 |
| step25 | 262 | 52.4% | -3.4 |
| step40 | 254 | 50.8% | -5.0 |
| step50 | 246 | 49.2% | -6.6 |
| step60 | 205 | 41.0% | -14.8 |
| step70 | 240 | 48.0% | -7.8 |
| step80 | 254 | 50.8% | -5.0 |
| step90 | 226 | 45.2% | -10.6 |
| step100 | 222 | 44.4% | -11.4 |
| step110 | 221 | 44.2% | -11.6 |
| step120 | 240 | 48.0% | -7.8 |
| step130 | 237 | 47.4% | -8.4 |

step30原checkpoint曾误删、未测。60/70各2未决、130有1未决，最多影响0.4/0.4/0.2个百分点，解释不了主要差距。70之后引入训练评分有效性修复，不能把整个曲线视为单一不变配方。

本次重新按500个相同instance逐题对照base，结果如下。base的499条分片计分加原单题固定补丁复验reward=1，严格还原279，不从各次运行挑最好结果。

| checkpoint | base错→新对 | base对→新错 | 净变化 | 配对精确McNemar p，未校正 |
|---|---:|---:|---:|---:|
| 80 | 36 | 61 | -25 | 0.01439 |
| 100 | 24 | 81 | -57 | 2.08e-8 |
| 110 | 28 | 86 | -58 | 4.84e-8 |
| 120 | 35 | 74 | -39 | 0.000237 |
| 130 | 35 | 77 | -42 | 0.0000898 |

这些是探索性的单次轨迹配对统计，未做多重比较校正；不同资源配置、采样和中断续测仍是混杂因素，p值不是训练原因的因果证明。但100/110这样的差距很难只用“一两道超时题”解释。step110的Django由128/231降到98/231，SymPy由45/75到36/75，Sphinx由19/44到10/44；损失分布在多个项目。

**实际运行与两类官方来源的对照**

LEGO-RL是框架的SAO实现；原SAO论文是算法来源，二者不能混称为同一份官方代码。原文未提供足够的编码训练资产/全部执行细节，不能声称逐项精确复现。

| 项目 | 原SAO论文编码实验 | LEGO-RL成功recipe | 本次A800实际运行 |
|---|---|---|---|
| 模型 | Qwen3-30B-A3B-Thinking | Qwen3.5-35B-A3B | Qwen3.5-9B稠密模型 |
| 训练方式 | 异步 | 2训练节点+1rollout节点，异步 | 单节点共置、同步trainer |
| 每prompt轨迹 | 1 | 1 | 1 |
| 全局batch | 128（编码沿用主要参数） | 64 | 16 |
| Actor / Critic LR | 1e-6 / 5e-6 | 1e-6 / 5e-6 | 日志实际1e-6 / 5e-6 |
| Critic频次 | 每Actor更新2次 | 2次 | 2个epoch、mini=full=16 |
| DIS有效比值范围 | 0.2–4.0 | 0.2–4.0 | 0.2–4.0，token IS+reinforce |
| GAE | 长度自适应policy λ，critic λ=1 | 同类设置，优势白化 | α=1.5、γ=1、critic λ=1、白化开启 |
| Critic起点 | 强调value预训练重要性，具体编码预训练细节不足 | 先前训练约100步的warm Critic，再校准20步 | 基座backbone+随机value head；Actor约前19步不更新 |
| 训练数据 | 编码数据细节未充分披露 | OpenSWE 2699条 | SWE-Smith python-full-v7，6242条 |
| 长度预算 | 128K；编码OpenHands最多300轮 | prompt30K+response170K，200轮 | prompt8192+response65536；rollout context98304，128轮 |
| 验证配置 | temp1，300轮/128K | recipe有定期Verified500验证 | 独立temp0.7、200轮、262144 context、单次32768 output |

论文参数来源：[SAO原文§3.2与§4.1](https://arxiv.org/html/2607.07508v1)。LEGO设置来源：[固定版本生产配置](https://github.com/LegoX/Lego-RL/blob/a3e28f171be165b5e8cda45030f336ec103690a7/scripts/train/configs/sao_async_3nodes_qwen35_ohsdk_veomni.env)。原论文编码基线23.0%与我们的55.8%处于不同模型/协议，不能用绝对分数比较复现成功与否。

N=1是每个prompt只采一条，不是整个batch只有一条。把batch64改成16后仍使用相同LR，不代表更新噪声不变；按相同prompt数量计，会执行约4倍optimizer更新。我们的130步只约2080个batch样本槽，约为6242条的三分之一，并非完整一轮；也不等同官方130步。评测每卡32并发与训练全局batch是不同参数。

同步本身不构成SAO数学错误，通常反而减少policy lag；它主要改变调度和吞吐。官方单节点8B配置明确只是链路smoke，不是已证实能涨分的学习配方。dense模型无需MoE路由重放，不能把R3=False本身判为bug。

**最强异常：Critic长期没有建立有效的状态区分能力**

只统计成功checkpoint链：初始1–25、resume25的26–29、resume30的31–69、修复后v2b的71–130。排除了已丢弃的v2 71–79；30/70在保存后中断，没有完整正式metrics行，未补造。共有128个step日志；以下都是分段简单均值，不是评测成绩。

| step范围 | 日志步数 | Critic解释方差EV | 训练score均值 | 达到response窗口上限比例 |
|---|---:|---:|---:|---:|
| 1–19 | 19 | -4.483 | 0.566 | 26.32% |
| 20–30 | 10 | -0.078 | 0.581 | 19.38% |
| 31–70 | 39 | 0.077 | 0.567 | 7.21% |
| 71–90 | 20 | 0.040 | 0.541 | 1.88% |
| 91–110 | 20 | 0.076 | 0.528 | 0.94% |
| 111–130 | 20 | 0.046 | 0.516 | 2.19% |

EV是`1-Var(return-value)/Var(return)`；接近0表示相对常数预测的改善很小。所有这些日志的returns最小0、最大1，不是“整批同一回报导致EV分母退化”的假警报。Actor开始更新后，最高EV也只有0.301，未出现>0.4的step。20–130的109个已记录step中，94步的平均Critic梯度norm超过clip=10；它是诊断信号，不能简单把Adam的有效学习率机械除以这个比例。

LEGO公开文档记录过r6退化，r7通过warm Critic、白化等改动稳定；文档给出的成功运行EV常见0.2–0.5。我们已使用白化和clip10，因此不具备r6的全部前提，但长期弱Critic这一表现相似。[LEGO SAO文档](https://github.com/LegoX/Lego-RL/blob/a3e28f171be165b5e8cda45030f336ec103690a7/docs/content/docs/run-training/sao.mdx)

推断：小batch单轨迹下，弱value baseline让优势估计噪声较大，容易产生不利更新。此项证据最强，但仍需固定Actor、独立验证Critic的对照试验才能确立因果。不能仅凭低EV认定value head代码错了；任务难度、标签噪声、初始化和模型容量都能造成同样现象。

**新确认的一处实现/配置落差：10步Critic学习率预热没有生效**

实际Hydra：`critic.optim.lr_warmup_steps=10`，`lr_warmup_steps_ratio=0.0`。但运行后端`VeOmniEngine._build_lr_scheduler`只传递`lr_warmup_steps_ratio`，未读取绝对steps。VeOmni scheduler据此算出warmup=0，日志所有已记录步的Critic LR都为5e-6。

固定上游verl同一commit的函数也如此；LEGO SAO patch未修该段。这是上游backend与配置接口之间的兼容性问题，不是原论文算法结论，也不是我们后加verdict逻辑造成的。[上游函数](https://github.com/volcengine/verl/blob/7aed6b230776f963fa09509c10d9c3a767d1102c/verl/workers/engine/veomni/transformer_impl.py)

须区分三件事：LR逐步升温、Actor暂不更新的critic_warmup、提前训练好的warm Critic。我们第二项有执行，第一项没有，第三项没有。不能把“20步warmup”说成三项都满足。无LR预热可能影响随机value head初始稳定性，但它是否影响到最终退化尚无消融证明。本次未修改该函数。

**长轨迹与完整奖励：确定存在截断路径，学习影响待验证**

BuiltinSWEAgentLoop将`response_ids / response_mask / logprobs`按65536保留前缀，仍使用整个Harbor任务结束时的verifier奖励。这个response长度包含工具观察，不等于65536个模型生成token。训练filter只丢timeout/env_setup_failed；overlong/max_turns仍保留。

上游同一loop也存在前缀切片与最终奖励设计，不是此次verdict修复新引入。但我们窗口明显更小，早期26%/19%的样本达到上限，影响更突出。这个指标是达到上限比例，不是逐条确认都丢了最终编辑。

当最终修复动作落在被切掉的后半段时，训练只看见前半段却给它整题成败奖励，末端value target也被当作完整终局；会增大信用分配和有限窗口目标的不一致。前缀学习并非在所有情形都必然无效，因此不能直接把这项称为已证明的全部根因。后续应抽查截断位置、补丁形成时间与reward，比较完整轨迹或一致预算处理；盲目丢所有长轨迹同样可能产生选择偏差。

**数据与评分：责任需要分开**

1. 数据确实不同。当前manifest有6242任务、124仓库，最多的是python-pptx347、sqlfluff293、python-docx246。Verified500中Django占231、SymPy75。SWE-Smith合成破坏及issue生成与真实issue修复的分布不同，是负迁移候选原因，不能由此断言该数据集本身无效。[SWE-Smith官方生成流程](https://github.com/SWE-bench/SWE-smith)
2. 我们的数据适配器曾把内部verifier超时当作正常0奖励，这是确认的本地bug。旧审计1147份记录找到3个此类实例；可能引入错误负样本，但这不是全量误标率，不能据3条断言足以解释几十题下降。70后新版判定已修复；修复不会自动撤销70以前形成的权重变化。
3. 全量资产的`controls`仍6242项为空。已有少量baseline0/oracle1 smoke，不等于完成全量可解性和判分校验。379条缺PASS_TO_PASS不自动构成错误，只说明回归保护覆盖不同。应先做按仓库、测试规模、成功/失败分层的控制实验，再讨论数据质量。
4. 新verdict语义将无有效判定的样本排除，方向合理，但pytest collection/import错误有时来自模型坏补丁，有时来自环境。不能把所有此类错误都一概解释成环境；需要原始坏版本与oracle控制作区分。当前71–130只有4个invalid样本槽，尚无证据它是后半程主要退化来源。
5. 训练reward分段均值也未明显升高，不过各步题目不同；没有固定训练验证集，不能严谨下结论“训练拟合越来越好、只是过拟合测试集”。目前更准确的描述是更新效果差/泛化退化。

**其他已确认的工程问题及其解释边界**

| 问题 | 归属/状态 | 能否解释主要下降 |
|---|---|---|
| step80 metadata字段缺失导致concat退出 | 我们verdict改动引入，已修复并通过真实混合batch | 造成71–79重算；没有写成损坏的80。不能解释20–70已发生的下降 |
| 旧checkpoint30误删 | 我们的操作失误，未测且无法恢复 | 损失可评测模型，不改变已训练权重 |
| Docker网络池、OpenMP/BLAS过度并发、超时exec残留 | 评测基础设施问题，已按本任务修复 | 解释慢/未决；不直接证明训练算法有问题 |
| Sphinx模型补丁引入线程异常/队列死锁 | 有具体坏补丁与原测试复现 | 至少部分长尾是模型输出质量问题，不是同一个流程bug |
| stock merger给dense Qwen3.5改错键名的风险 | 已在实际使用前改direct merge，并校验 | 当前没有发现最终评分模型由此损坏 |
| 空微批次除0担忧 | 未部署guard；实际global分母路径、选定CPU测试通过 | 没有本次因它NaN/退化的证据；不宣称所有全局空批情形都安全 |

**本次排查降低了哪些嫌疑**

- 实际DIS两处配置镜像一致：bypass、token IS、0.2_4.0、reinforce。GSPO遗留的很小clip_ratio参数不决定这条loss，不能据此说误用了小PPO裁剪。
- reward确实落在最后模型token，GAE跳过工具观察，critic returns在优势白化前生成；未发现奖励全落在mask外而失效。
- 实际loss：Actor seq-mean-token-mean、Critic global token-mean。23个选定原有CPU断言通过，包含DIS loss/梯度、观察跳跃、λ解耦、reward落点、4种microbatch划分下Critic loss及梯度一致性。没有安装pytest；通过AST移除pytest装饰器、直接调用不依赖pytest helper的测试，不冒称完整测试套件或8卡集成回归。
- 本次step80原8个Actor分片与已评测HF模型按760个训练参数键、52800个位置作CPU数值抽查，按实际FP32→BF16转换后零差异。加上775键/形状/有限值检查，降低错误合并嫌疑；这不是全张量或forward logits等价证明，也未覆盖每份历史checkpoint。15个未训练MTP键来自base补齐。
- rollout/train logprob在多数步接近：阶段平均ESS约0.999，平均KL约0.0003，后段约0.0016–0.0018。未出现大面积IS权重失效的迹象。少数后段KL高到约0.01应留意，但不能用平均健康证明每个token完全正确。
- Actor LR始终1e-6、Critic始终5e-6；已记录从70恢复模型/optimizer/RNG/scheduler/dataloader，下一16样本顺序一致。无证据表明正常resume把优化器重置或弄错模型。

DIS比较的是当前策略与rollout策略，不是初始base。每步差距小，累计仍可远离base。无reference KL是SAO配方的一部分，不能说忘加KL是工程bug；加KL应标成新消融。

还有一个未定性细节：本地同步trainer先算values/GAE，再更新Critic两轮，再更新Actor，因此更新后的Critic主要在后续batch影响优势。论文的文字强调更快价值更新，但缺少足够原作者执行代码，不能据文字直接断言LEGO顺序错误，更不应未做对照就修改。

**按优先级划分的解释**

| 候选原因 | 已有证据强度 | 当前判断 |
|---|---|---|
| 冷Critic长期偏弱 + batch16单轨迹高方差 | 高：实际EV/梯度、成功recipe差异、配对成绩 | 第一优先级；需要受控实验确立因果 |
| 训练数据/评分覆盖与目标分布不匹配 | 中高：数据确不同、全量controls不足、曾有误标 | 第二优先级；不能简单归罪数据集作者 |
| 64K前缀截断仍配完整奖励 | 中高：代码路径与早期高上限命中率 | 需检查真实截断样本及完整轨迹对照 |
| LR warmup配置未生效 | 确定存在，影响程度未知 | 应修配置/backend接口并验实际LR，单独记录 |
| Actor更新步长/累计偏移不适合9B小batch | 中：相同LR不同batch与容量 | 可测低LR/大batch，不应宣布某个LR必然正确 |
| GAE/DIS接错、checkpoint merge错误、普通resume错误 | 当前较低 | 选定检查未发现；仍有完整GPU等价验证边界 |
| 只因评测超时或随机波动 | 不足 | 能影响小差距，解释不了100/110主要缺口 |

**下一轮最小可解释实验，而不是在130上继续碰运气**

建议保留现有停止状态；新的实验以base Actor为起点，现有Critic可作为候选warm初始化，但必须先验证，不能因为训得久就默认合格。

1. 先校验数据和预算。选择约100个分层训练任务，固定原始bug版本应失败、oracle修复应通过；记录超时/collection错误的归属。核查一批真正截断的成功和失败轨迹。把生成终止、用于学习的token范围、最终被验证的代码状态对齐；不要先大规模改模型参数。
2. 冻结Actor，先训练/校准Critic。用固定策略的代表性rollouts，按任务切分Critic训练与保留集，记录EV、MSE/Brier和校准；不要只看训练loss，不能把Verified500答案用于拟合。确认LR warmup实际曲线。EV0.2–0.4可作诊断参考，不能当跨模型通用硬阈值。
3. 先测batch这一项。共同的base Actor、合格warm Critic、同一数据/预算，比较global batch16和64；可评估梯度累积方案，mini/full设置也要同步，避免mini16下偷偷做4次Actor更新。按相同任务量与token量比较，不能只按step数比较。
4. 再测Actor LR。固定其余设置比较1e-6与例如5e-7；这是待验证候选，非已知正确答案。不要同时修改LR、batch、窗口、KL和奖励后宣称知道哪项有效。
5. 固定评测协议。沿用稳定n32/线程限制/网络与verifier版本，固定500集合和记录seed；用固定开发集作早期诊断、完整500作里程碑复核，减少反复针对同一500调参。至少对base与候选模型补充独立重复以估计采样方差，再判断小幅改善。

未部署任何本次发现的修复；训练仍停止，监控仍暂停。上述是下一阶段建议，不是已经执行的训练计划。

**可复核材料**

- `training_metrics.json`：四份实际日志的路径/SHA、逐step数值、分段统计；`analyze_training_logs.py`可重复提取。
- `paired_evaluations.json`：逐checkpoint来源/SHA、配对增减和按仓库计数；`paired_evaluations.py`可复核。
- `cpu_checks_output.txt` / `run_cpu_checks.py`：23个选定CPU断言及执行方法。
- `merge_samples_output.txt` / `check_merge_samples.py`：step80源分片数值抽查结果与边界。
- `upstream/`、`upstream_commit.txt`、`upstream_comparison.json`：固定公开源码与SHA；`verl_veomni_transformer_impl.py`保留warmup接口证据。
- 历史问题来源：外层`AUDIT_AND_FIX_REPORT_2026-09-26.md`、`LEGO_RL_SWE_HANDOFF_2026-09-24.md`第58–83节；这些是已记录审计，不把其中假设升级为本次实测事实。
