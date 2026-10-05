# SWE-Smith任务恢复与历史Agent Lightning筛选核查

更新：本文记录的最后4题已在后续修复中全部通过专项与真实Harbor验收，完整6248题v5已生成，pending清零。详见同目录`SWESMITH_FINAL_FOUR_FIX_2026-09-30.md`；下文保留当时诊断历史。

本轮按用户要求尝试修复，不以进一步缩小训练集作为默认解法。训练、GPU评测和自动监控均未启动；旧数据、checkpoint、HF模型、评测结果不变。

## 结果

- 上轮167题临时隔离中，163题现在通过严格的bug=0、oracle=1对照；4题保留待验收。
- 找回从Agent Lightning 6248题转换到Harbor 6242题时漏掉的6道Pandas题，6题全部通过bug/oracle对照。
- 已生成完整6248题候选，ID和顺序与AL v7 train.jsonl完全一致，未删除4题待验收项。
- 候选目录：`/media/ubuntu/D1/zsj/Lego-RL-main/data/swesmith_python_full_v7_verdict_v4_candidate_20260930`，同名`.parquet`。
- manifest明确`training_ready=false`、`activated_for_training=false`。旧6242 manifest/parquet SHA前后不变。
- 本轮独立控制覆盖185个不同任务，其中182通过，3个控制未能取得bug有效二值；另1个Conan已有缺依赖证据。**并非全量6248动态认证**。此前92题v3对照是另外一轮证据，不把所有未复验题冒称通过。

## 修复内容与归属

1. **源码内嵌测试适配遗漏，属于我们的迁移问题。** 初始恢复含bug的业务源码；仅把测试定义归一到原始可信测试，AST检查业务实现未改变。评分阶段验证内嵌测试未改，不再整文件覆盖模型的业务修复。专用测试文件和文档测试仍从可信payload恢复。这个处理包括迁回AL曾修好的6道混合Patsy任务所需逻辑。
2. **6道Pandas题转换遗漏，属于我们的导出方式问题。** 测试在Git中存在，但`.gitattributes export-ignore`使`git archive`不导出；改成核对普通文件mode后精确读取Git blob。不是原始题目缺文件。
3. **Furl环境适配漏迁。** 恢复旧AL使用的CPython 3.10.0 URL parser快照，仅复制到相应任务镜像，不修改共享Python环境。SHA `f14ec821fe7ded126d2202eef195f66bd63f74975c9ae88322d0500f13eba8db`。14题全部bug0/oracle1；其中1题属于上轮167题隔离。
4. **Pyquery离线HTTP回放漏迁。** 旧AL已有真实公开HTML快照及来源manifest；将同一SHA快照迁回对应任务验证容器的localhost服务，不改断言或模型答案。9题的oracle现在全部通过，其中8题bug也取得0；另1题原bug令doctest节点不可收集，仍待判分边界处理。快照SHA `633c5b6acb69cf38d6ca4da7ea9b87c09040636c10c100f3be3ace3a6c606216`。
5. **Patsy异常报告器兼容问题。** 老Patsy eval的locals映射触发exceptiongroup可选错误建议渲染器KeyError。仅在这些任务的pytest插件中捕获建议生成失败，保留原测试结果和异常；不是吞掉测试失败。70题复验69通过，修复了此前两题无判分；剩余pr_140为不同的导入错误。
6. **DVC测试并行问题。** 原bug和oracle在`-n 2`均超时；同一5项测试改`-n 0`，正式verifier控制bug为3pass/2fail、reward0，oracle为5pass、reward1，均约30秒。仅对该任务调整测试进程数；300秒期限、测试节点、断言和JUnit判分保持。可以确认这一调整解决复现，未声称已证明pytest/xdist内部的全部根因。

## 四题仍待验收，全部保留

| 任务 | 已知证据 | 未直接当坏题的原因 |
|---|---|---|
| `john-kurkowski__tldextract.3d1bf184.pr_325` | bug收集时缺`scripts`模块，oracle=1 | 需区分题目故意造成导入错误与环境故障；不能盲目给缺依赖一律0或修掉bug |
| `pydata__patsy.a5d16484.pr_140` | bug从collections导入Mapping在Python3.10报错，oracle=1 | 同上，不能添加兼容别名后无意消除待修bug |
| `gawel__pyquery.811cd048.func_pm_ctrl_shuffle__1355aoe9` | HTTP问题已解决，oracle=1；bug缺可收集的`PyQuery.closest`doctest节点 | 原bug改变了测试发现语义，当前保守JUnit规则不产生二值；需明确允许的失败判据 |
| `conan-io__conan.86f29e13.pr_15457` | 正确补丁验证仍缺cmake；补PATH不足 | 需要任务镜像内补齐可信依赖后重跑，不应跳过测试 |

本轮没有重写上述任务的业务bug，也未把无判分强行写成reward0。候选不激活，是因为这些项和完整环境兼容性尚未验收，不是因为再次删题。

## 之前Agent Lightning为什么筛选

直接读取AL v7的`exclusions.json`、`manifest.json`、旧适配器和Patsy修复报告，核实训练排除67题：

| 类别 | 数量 | 原因 | 能否恢复 |
|---|---:|---|---|
| Safety / gTTS | 47 / 8 | 正确补丁的必要测试需要不可用在线服务 | 有机会。需可用原服务或经验证的真实录制回放；不能伪造固定通过响应。本轮未恢复这55题 |
| Patsy纯测试变异 | 9 | 发布的Bug Patch只改测试，没有剩余业务bug；还原可信测试后空补丁通过 | 不能仅修适配器恢复成同一道业务修复题；需要重新定义/构造bug，属于新数据版本 |
| Paramiko空补丁通过 | 3 | 不做修改已通过声明F2P及同文件P2P，产生假阳性奖励 | 需找到可信、可区分bug和修复的测试证据；目前不能直接放回 |

此外28道Go训练题、4道Go验证题是Python实验范围之外，不属于坏题。AL v7保留6248训练、470验证。其67题排除曾获用户授权，原资产保留。

原Patsy审核15题中，6道业务/测试混合变异已经修复并保留，9道纯测试变异才排除。不能把两者混为“全都没法用”。这些问题不是Agent Lightning的PPO算法导致；原始测试变异、离线运行限制、我们后续Harbor迁移遗漏是不同层面。

## 验证和证据

所有路径以下述A800数据盘根为前缀：`/media/ubuntu/D1/zsj/Lego-RL-main/`。

- `logs/swesmith_embedded_repair_v4b_20260930/summary.json`：164混合/文档控制，初次151通过；经Patsy和Pyquery独立复验替代对应记录，最终161/164通过，评分前后业务源码SHA不变。
- `logs/swesmith_patsy_reportguard_v4_20260930/summary.json`：70/69。
- `logs/swesmith_pyquery_http_recovered_v4b_20260930/summary.json`：9/8；9个oracle全通过。
- `logs/swesmith_furl_recovered_20260930/summary.json`：14/14。
- `logs/swesmith_pandas_recovered_20260930/summary.json`：6/6。
- `logs/swesmith_dvc_serial_recovered_20260930/summary.json`：1/1；有界前置诊断在`logs/swesmith_dvc_bounded_20260930`。
- `logs/swesmith_embedded_harbor_v4_20260930/PASS.json`：真实Harbor 3场景，bug0、oracle1、篡改内嵌测试被拒绝且无伪造奖励。
- `tests/test_swesmith_embedded.py`：本地和Linux 5/5边界单测；此前v3的9场景Harbor和专用测试边界回归仍另存。
- Windows源文件manifest：内层仓库`audit_deployment_manifest_data_v4_20260930.json`；15文件精确WSL同步，远端`logs/swesmith_v4_source_sha_20260930.json`核对15/15。

早期v4试跑的oracle提取因容器内复制目录所有权影响Git信任检查而失败，已修审计脚本并用v4b新目录重跑；这些失败不是数据质量结论。Pyquery第一次准备因选择全部30题却断言9题，在执行测试前退出，保留目录后明确选择9项失败控制重跑。没有删除失败证据、替换模型答案或择优计分。

## 范围限制和后续

这是任务/判分环境修复，不是SAO数学、优化器、空批次逻辑或batch64实验变更。没有覆盖旧6242/v3资产，没有重新计算历史模型分数。AL还包含Pydicom/Sunpy资源、Modin/Tornado等特殊运行适配，不能用本轮部分控制宣称已完整迁移全部兼容逻辑；启训前仍需全资产对照清单与剩余项验收。

收尾时八卡均14MiB、无本次审计容器残留，D1约97.77GiB可用，仍不足保存新的约177GiB完整checkpoint。未启动训练，也未删除用户数据。

### 2026-09-30 四题可恢复性进一步核对

本次直接对照三个任务的原始oracle.patch，证据更明确：
- Tldextract pr_325的正确补丁新增整个`scripts/release.py`，缺模块正是任务尚未实现的业务内容，不是简单缺第三方包。
- Patsy pr_140的正确补丁将`collections.Mapping`改为`collections.abc.Mapping`兼容导入，原版本ImportError就是待修bug。
- Pyquery shuffle任务原版本将return移动到函数首行、docstring之前，使doctest不可发现；正确补丁把return移回末尾。不是测试数据根本不存在。

因此前三题不能因为pytest收集阶段报错就判作坏数据。当前verifier把所有收集错误当无效的规则过于保守；需要以可信环境预检、预期节点清单及错误归属为依据，识别候选业务代码导致的导入/发现失败为合法失败，同时仍让缺运行依赖、损坏测试、Docker错误保持无效。不能简单把exit2/4统统判0，不能往初始代码注入oracle。Conan仍需任务镜像内补齐cmake并重新双侧对照。四题均有继续解决的路径，本次仅核查与澄清，尚未实现新的判分规则或宣布全部通过。
