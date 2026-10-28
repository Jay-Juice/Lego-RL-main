# 动态 PI 设计与训练准入

本轮用户授权先研发验证，方案合理收敛后直接启动新实验训练。不是立刻开训，不恢复旧checkpoint。方法变化只限PI选择、表达和去重；head、freeze、Actor/reward/filter/SAO/GAE/loss/optimizer与既有ICPS匹配SAO的训练配方不变。PI预算192/128/4096不变。旧SAO历史packing阶段1–20和21–97保持原对照，不私自统一或调整。

## 研发设计

初始从原issue-only top3候选中构造短语法单元，压缩重复路径，按候选多样性和issue相关性分配同192预算。只用真实源码，不编造修复结论。后续从当前工作区与前一可观测工作区比较获得实际变化；允许变化实体进入候选，保留一个issue锚点。当前上下文和删除/身份未知状态显式表达。缓存只保存有界来源与已发内容，不使用Gold、注入位置、终局reward、未来调用或隐藏测试。

状态触发以实际可见源码和语义状态为主，避免函数外窗变化却重复发送原正文。可见内容相同不重复扣预算；状态回退必须发出，不能用全局seen集合误吞A→B→A。同逻辑调用重试必须返回原完整payload且不二次扣费，跨会话/时间逆序/未知映射失败关闭。明确budget exhaustion，不能用旧PI冒充当前状态。

## 覆盖率和信息密度

原607任务全部已被观察，标为development/historical。242/366候选实体相交约66%不是可直接复制进192token的Bug定位：class可能包含很多方法，单行也可能超预算，候选命中不提供真实位置。独立scorer分解242中可容纳的最短真实行/锚点、完整语法上下文成本、候选多样性和排序损失。Oracle最短成本只作离线容量上界，绝不能导入生成器。初始与动态覆盖分别报告，不能借后期可见变化冒充初始覆盖。

记录真实源码可见行/锚点、完整目标hunk、函数覆盖、每100实际token覆盖、重复正文率、有效变化覆盖、显式未知、metadata占比、wall/CPU/RSS。源码完整性、坐标、tokenizer往返和原生预算是硬约束，碎片化覆盖不能替代可解释语法单位。保留old同源同tokenizer对照及新增/丢失计数。

探索最多先做三种事前定义初始分配规则，开发集配对评估后选一项；每轮代码、SHA和全部失败保留。允许后续按明确机制继续修改，但不能用无限轮挑最高分声称泛化。

## 独立验证和训练准入

先查原训练6248与既有位置标签/快照中未用于旧诊断的任务及仓库。冻结新验证清单，排除Verified500评测任务及已见607；生成进程只收issue和W0/动作前源码，标签由独立scorer保管。无法获得足够独立可评分样本时，记录数据限制并继续研发，不用旧Test重命名为盲测。

在看新验证结果前冻结唯一方案。开发主覆盖相对v1.1至少改善5个百分点、候选命中条件下转化率改善，完整hunk不退化；独立验证主覆盖净增、仓库聚类区间下界>0且完整hunk不退化才判为覆盖门槛通过。目标是接近可达到的66%，不是以Gold定位实现66%。若开发数据无法达到门槛，分析机制，不降低门槛自动开训。已打开验证集若用于改设计，降为开发并需要新确认集。

动态：真实历史可验证输入回放及构造编辑/删除/回退/rename/parse错误的契约测试；报告两种证据的区别。旧轨迹缺完整W_t不能伪造真实回放。需要补充时可做隔离真实Harbor探针，不运行隐藏任务verifier、不产生额外奖励。PI与Actor数据路径/逐token因果/gather/PI预算必须通过。

通过以上后运行真实tokenizer/proxy集成和8GPU原生SP8短更新验收，独立日志和模型状态全丢弃；源代码逐项对照只PI相关差异。完整dryrun仅方法/实验命名等授权变化，SAO配方固定。无数值非有限/结构错位后方可创建freshbase新EXP正式训练。覆盖改善不保证RL改善，报告其限制；不能从旧ICPS checkpoint混续。

## 运行与版本控制

Windows独立源备份后修改，WSL rsync预览审阅、sync、SHA。共享venv/VeOmni/vLLM只读，无安装/下载/资产删除/全局Ray或Docker清理/停止他人进程。训练启动需全8GPU空闲、无冲突服务、完整prepared数据/镜像与磁盘预留：保留旧安全保存门槛及完整checkpoint机制，不降门槛、不partial保存。空间不足通知一次等待用户处理。

GitHub新分支codex/icps-dynamic-state-20261028，从当前已归档ICPS commit823ac02建立独立worktree。仅提交审核后的源码、聚合报告和方案，不上传模型/数据/日志/原始轨迹/私有评分证据。旧分支与main不改。

本线程heartbeat初始30分钟；短CPU阶段可调整15–30分钟，长GPU/训练阶段按实测耗时改30–120分钟。每次先读本状态/验证报告/最新证据；健康或无变化静默，只有阶段完成、失败、需用户操作时通知。准入全部通过后启动一次正式训练，不重复健康任务；完成或无法安全继续时报告并结束相应监控。

Offline asset preparation (2026-10-28): twelve Linux CPU contracts and readonly
hashing of 18 actual cached files pass. Four safetensors shards/775 tensor headers
match the exact index/layout/total bytes; tokenizer/chat template/config and the
two original parquet identities are bound. Parquet rows/labels were not read.
The entire inspection/hash pass rejects metadata/file-set drift, symlinks and
mid-pass mutations. First eleven-contract Linux pass is preserved before this
strengthening; local Windows strict-resolve permission errors are not a pass.
See GPU_OFFLINE_ASSETS_R6_CONTRACTS_R2.json and GPU_OFFLINE_ASSETS_R6_REVIEW.json.
The private manifest remains remote. This new component is not yet integrated
with the receipt consumer. Native/shared/lazy dependency policy, reviewed producer
and real Ray/GPU acceptance remain pending; no admission or GPU update occurred.
The current five-input GPU_OFFLINE_ASSETS_R6_CONTRACTS.sha256 binds the R2 source.
