# SWE-Smith数据、轨迹截断及batch64审计

日期：2026-09-29。用户请求检查bug/oracle判分与截断轨迹，并解释batch64相关参数。

结论：batch64值得作为独立实验，但本次发现了可以复现的数据适配错误，先处理这些错误比直接放大batch更重要。此次未改训练源码/数据资产、未启动训练，未部署空批次guard。只新增独立审计脚本及D1日志，临时审计容器全部退出清理，未处理其他容器。

## 1. 100任务bug/oracle控制

固定seed=20260929，从6242任务抽取100项，覆盖83仓库：80项按仓库抽样、9项大测试集、8项无PASS_TO_PASS、3项历史超时任务。风险加权抽样，不是全量错误率估计。

每题两份隔离容器：原始bug版本、同一版本应用oracle。oracle由冻结base镜像中 `git diff --binary HEAD~1 HEAD~2` 提取；原数据和评分脚本不修改。4CPU/8GB、内部pytest300秒；外部另有有界清理；4任务并发。全部使用缓存的digest固定base镜像重建任务Dockerfile所定义的bug初始状态（对应task镜像tag当前均不存在），不是对100个已有task镜像做Harbor端到端验证。容器network=none，生产为public，因此尤其网络相关超时需另行匹配环境，不能直接认定为坏数据。

| 原始控制结果 | 数量 |
|---|---:|
| bug=0、oracle=1 | 94 |
| bug=0、oracle仍0 | 3 |
| oracle无法应用：目标业务文件已被移除 | 2 |
| bug和oracle均300秒超时、无reward | 1 |

六项异常与追查：

| 任务 | 证据与结论 |
|---|---|
| `davidhalter__parso.338a5760.func_basic__xlbdayjr` | payload含 `parso/tree.py`；task初始移除该文件，oracle直接apply失败。隔离诊断先恢复payload、再apply oracle，原verifier随后把正确业务文件覆盖回bug，SHA改变且reward0。只取消第二次恢复、保持同一oracle/测试断言，SHA不变且reward1。 |
| `pydata__patsy.a5d16484.func_basic__dg2dvm91` | 同一问题，具体为 `patsy/infix_parser.py`。同一oracle在评分前被覆盖时reward0，只恢复一次时reward1，前后SHA提供直接证据。 |
| `pwaller__pyfiglet.f8c5f35b.combine_file__sind222x` | oracle后3个CLI测试失败，`pyfiglet: not found`。仅给verifier环境PATH前置 `/opt/miniconda3/envs/testbed/bin`，同一oracle变为reward1。绝对路径调用pytest解释器并不会自动修复其子进程PATH。 |
| `conan-io__conan.86f29e13.pr_15457` | oracle后37passed/1error，所需cmake不可用。补PATH仍reward0，尚未证明仅PATH能解决；应核对工具依赖与原测试环境，不当模型失败样本直接使用。 |
| `gruns__furl.da386f68.func_basic__o4gpato7` | oracle仍3failed/70passed，涉及IPv6 netloc及多斜杠URL；依赖/Python兼容性或原测试集合问题仍待细分，不伪称已修好。 |
| `iterative__dvc.1d6ea681.func_pm_remove_loop__tu21q9d9` | bug/oracle各300秒超时，当前新版脚本均保留unresolved。由于审计禁网且测试涉及队列，不能只据本次证明生产任务必然无解。另两项历史Trio超时任务本次均bug0/oracle1。 |

**责任归属：**把包含doctest/内嵌测试的整个业务源码当成“隐藏测试文件”，再于verifier阶段覆盖，属于我们SWE-Smith适配方式的问题；不能归罪SAO算法，也不能说SWE-Smith所有任务都有问题。CLI环境不完整也是适配应负责检查的问题。通用地判断pytest exit1即模型错误还会把某些setup ERROR误当负奖励，必须靠对照验证环境，不能靠退出码包办。

这些修复只在独立诊断中尝试，**没有部署生产**。诊断取消payload恢复不能直接作为正式修复：正式方案必须保证模型不能修改测试作弊，同时不覆盖业务修复。内嵌测试应提取成独立可信测试，或先隔离这些任务、按正确边界重建新版资产；完整bug/oracle控制通过后再使用。

### 全量静态扫描与历史关联

- 6242任务中，145项的payload存在路径名不含test的Python文件，涉及6仓库：Patsy70、Parso28、Pyquery21、Inflect14、Python-pinyin7、Tldextract5。这是文件名启发式风险集合，**不是145项全部已确认判错**。
- 原1–70及成功恢复分支71–130共2116条result记录（包含重试等，不等于唯一训练样本数），46条涉及上述风险任务；21份保存的模型patch与这些payload业务文件路径相交。其原记录为19个reward0、1个reward1、1个无reward。
- 21个路径相交证明评分恢复可能抹除模型改动，但未对每份原补丁进行正确性复验，不能称“21个本来正确的答案全被误判”。需要进一步量化影响，不能凭样本数宣布它解释全部下降。

## 2. 100条保存轨迹的截断检查

从2103条有保存proxy消息和reward的记录中分层选择100条：五个训练阶段×成功/失败，每层3条较长轨迹+7条固定随机轨迹。排除已丢弃的旧resume70分支，71以后只读 `resume70_metadatafix_20260928`。

现有proxy JSON保存消息、工具定义、调试来源，没有保存实际 `traj_acc_ids`/逐token mask/logprob，因此只能用冻结Qwen3.5 tokenizer和真实chat-template分段重建；原模型token与后处理工具调用重新序列化可能不同。以下是敏感性估算，不能冒称原始精确token审计：

- 100条中30条重建response超过65536；模拟单段8192上限的更保守重建仍有29条超过。30条中13成功、17失败。抽样主动偏向长轨迹，**不能解释为全量30%截断率**。
- 重建response平均约65.1%为工具/观察token。64K上限包含工具观察，不是64K纯模型输出。
- 查看了跨界和截断后的工具调用：大多为测试、诊断、收尾；未在这100条中确认“成功的关键业务修复整个发生于截断后”这一强因果情形。
- 仍存在编辑调用跨界的具体例子：step114 Glom失败轨迹，file_editor修改 `/testbed/glom/core.py` 的调用重建区间64981–65573；后续工具观察确认文件已编辑。即学习窗口可只保留编辑调用的一部分，而验证运行完整动作后的代码。位置是重建值，不是原始token位置。
- 成功轨迹中也有越界的测试文件修改/新增诊断脚本，但不能把这些当作最终通过的关键业务修复。step61一个越界 `str_replace` 调用实际参数不完整、工具验证失败，也不能算成功执行的修复。

代码层面确定：`builtin_swe_agent_loop.py` 保留完整verifier reward，但对 `response_ids/mask/logprobs` 同取前65536；当前过滤只drop timeout/env_setup_failed，overlong仍保留。这个预算与奖励归因风险存在，**本次证据不足以说它就是主要下降原因**。下一次应记录真实prompt/response/model/observation长度、切点、最后执行编辑位置，再比较到预算即停止执行与保留完整学习轨迹的方案；不要只靠重新分词下定论。

## 3. batch64各参数的实际作用

已仅通过shell展开真实Hydra参数，未执行trainer。针对当前同步训练、N_RESP=1：

| 变量 | 原值 | 建议初次batch64值 | 说明 |
|---|---:|---:|---|
| TRAIN_BSZ | 16 | 64 | 保持配置/显示/检查一致；当前sync真正loader batch不是直接读它 |
| TRAIN_PROMPT_BSZ | 16 | 64 | 映射data.train_batch_size，真正每轮收集64个prompt |
| TRAIN_MINI_BSZ | 16 | 64 | Actor mini默认来源 |
| ACTOR_PPO_MINI_BATCH_SIZE | 16 | 64 | 显式设置，避免source后旧派生值残留 |
| CRITIC_PPO_MINI_BATCH_SIZE | 16 | 64 | 显式设置，避免Critic仍按16更新 |
| AGENT_NUM_WORKERS | 16 | 16起步 | 并发采集槽位，与总统计batch独立；后续单独评估32 |
| N_RESP | 1 | 1 | 每prompt一条轨迹，不同时改变这个维度 |
| Actor/Critic epochs | 1 / 2 | 1 / 2 | 保持原值；Actor warmup期间不更新 |
| Actor/Critic动态micro token预算 | 14336 / 20480 | 保持 | 与mini64是不同层级，不需要机械乘4 |

参数展开实测：`data.train_batch_size=64`、`actor.ppo_mini_batch_size=64`、`critic.ppo_mini_batch_size=64`、`agent.num_workers=16`、`rollout.n=1`、`critic.ppo_epochs=2`，两项micro token预算不变。

**mini不是语法上必须变大，但实验目标决定应当变大。**希望64条共同形成一次Actor更新，则mini64；若总batch64而mini16，warmup后每轮变成4次Actor更新、8次Critic更新，不能当作“64条平均梯度的一次更新”。mini64时为1次Actor、2次Critic更新。动态microbatch/梯度累积让64条不必同时激活在GPU，但更多数据、values/logprobs及host offload仍会增加内存/总耗时，不能承诺零资源成本。

**workers不必同步加大。**当前部署的AgentLoopManager按单样本入队，从worker队列领取可用worker，收齐全部样本后才更新。workers16可完成64条，近似4波且空位动态补任务；不是每波更新权重。32/64约对应8个TP1 rollout副本每卡4/8并发，只影响吞吐与资源，不决定batch64是否生效。训练同时有Actor/Critic offload，不能照搬只有推理的评测每卡32结论。训练默认RemoteDocker环境也未自动获得评测那套显式子网池配置；提高workers前要单独检查网络、CPU和内存。

**TRAIN_PROMPT_BSZ表示prompt数量，不是prompt token长度。**改64不要求把8192 prompt length、65536 response length或98304模型context也乘4。只改TRAIN_BSZ、漏改TRAIN_PROMPT_BSZ，实际同步训练可能仍为16。

### 受控实验还需同步换算的计数

- 以同样6242条、drop_last的一epoch为例，batch16约390轮；batch64约97轮。应按已见任务/token数比较，不只比较相同step。
- `trainer.critic_warmup=20`在batch16约320任务，在batch64约1280任务；若要严格匹配原样本预算，对应5轮。如果刻意给Critic更多预热则可留20，但这是另一项变化，不能不加说明。
- 每10step保存时，原约160任务/次，新约640任务/次；checkpoint体积仍约177GiB，不随batch直接乘4。
- 不应直接套旧resume130配置启动新batch实验；原dataloader状态、global step与总训练步数预算均需重新明确。应建立独立实验目录，记录起始Actor/Critic、数据版本与预算。
- 本次检查D1约99.2GiB可用，小于一份完整checkpoint约177GiB；没有删除任何保留模型。即使GPU可运行，也需先解决下一保存空间。

## 4. 下一步优先级

先修复并隔离验证业务源码恢复边界、verifier PATH/工具依赖，无法通过bug/oracle控制的任务隔离到新数据版本；按受影响仓库扩展控制，不能把本次94/100当全量质量认证。之后再做batch64实验，初始workers16、mini64，保持学习率和其余预算明确；吞吐实验再单独改workers32。此前Critic warmup实际LR接口问题也仍未修，不要把扩大batch当作所有问题的替代解法。

## 5. 证据位置

远端根 `/media/ubuntu/D1/zsj/Lego-RL-main`：

- `logs/swesmith_controls_audit_20260929/selection.json` 固定样本；各任务保存oracle SHA、测试脚本SHA、bug/oracle日志。
- `logs/swesmith_controls_audit_20260929/summary.json` SHA256 `b17d70630ac90e807737f7f7b590b12dc3095ad0c44dbfba32a6f1f3649cfcd6`。
- `logs/swesmith_controls_diagnosis_20260929/summary.json` SHA256 `7501e4ba2ac443ea3d7853a5c5f450503718eb1b77d0b8735061b19636e00565`；包含同oracle源码前后SHA。
- `logs/swesmith_trajectory_audit_20260929.json` SHA256 `a2839240fbf438a4c91a95e5318cd9b90ad2bb692f8ca7e13e94503970e661e6`。
- `logs/swesmith_payload_source_candidates_20260929.json` SHA256 `208df2531234319d21c06f1546d892ffd97595ead88ebc16a277de5ad2145f9e`。
- `logs/swesmith_training_payload_overlap_20260929.json` SHA256 `d8591b09ad60f665516ffac2d0c87b7e954d2360ac4a81e0c385f0868c0126ee`。
- `logs/swesmith_trajectory_tail_calls_20260929.json` 保存跨截断边界工具调用摘要。
- `logs/batch64_parameter_mapping_audit_20260929.txt` 仅参数展开，无训练启动。

Windows权威审计源码在内层repo的 `utils/audit_swesmith_controls_20260929.py`、`utils/diagnose_swesmith_controls_20260929.py`、`utils/audit_saved_trajectories_20260929.py`。均经WSL单文件dry-run/同步/SHA确认，未全目录同步。
