# 2026年10月28日 独立动态 PI 研发

状态：R4_DEVELOPMENT_PASS_CANDIDATE_FROZEN_NOT_TRAINING_ADMITTED，训练未启动。用户授权独立副本、原PI预算与SAO配方不变，验证动态候选/变化窗口/去重，合理收敛后可直接开启新freshbase实验训练；可以按阶段调整本线程监控间隔。旧ICPS v1.1与所有旧实验保持只读，不能恢复旧训练。
## 最新 R4 完成：冻结 flow_expand，转入独立确认

R4_PLAN.md在本轮输出生成前冻结。body_expand抑制声明/docstring作为评分锚点；flow_expand再增加一跳AST同名关系，属于语法启发式而非严格数据流。607生成实际Landlock拒绝标签访问，206秒左右；两队列development_r4和dynamic_r4均exit0。旧expand的607份完整输出与R3逐项一致。新目标覆盖body165/366、flow169/366，旧129；完整目标body99、flow98，旧53。flow净+40/366=10.93pp、gain56/lost16，首次通过预先+5pp开发门槛。开发repo-cluster CI不能当独立泛化证据。

真实token密度审计：flow目标行/锚点440/1320，旧259/1320；每千实际PI token目标行6.446 vs4.321。每千实际token命中题数2.476 vs2.152。source standalone/actual约81.7% vs63.8%，分开token化非可加，仅代理指标，不能称Critic可用信息或效果已经提升。详见reports/DENSITY_CONTROL_R4.json。

21本地字节契约、37真实Qwen契约通过；body和flow各24真实W0+构造新增/修改/回退全部通过，new目标24/24、old0/24，noop/retry/rollback各24，maxupdate128。仍非真实Actor rollout、Harbor在线或GPU验收。

按主指标选定flow_expand，CANDIDATE_FREEZE_R4.json锁定五份生成器SHA；停止在607继续挑分，按INDEPENDENT_VALIDATION_PLAN.md先审计历史诊断任务暴露，再冻结独立清单，不能直接把221库存称为已冻结或未见验证。后续只验证这一方案；若查看验证后改方案须将该验证降级开发。当前没有健康CPU job待重复启动。训练入口仍exit78，旧训练保持停止。R4备份archive/r3_before_executable_windows；旧35源再次SHA一致。

Windows权威：本目录；远端：`/media/ubuntu/D1/zsj/Lego-RL-main/experiments/icps_dynamic_state_v1_20261028`。A800/AGENTS.md规则继续有效。备份与初始35文件SHA见PROVENANCE.json。start_full97.sh显式exit78，必须完成ADMISSION_PLAN.md全部门槛后创建独立新入口，不能运行归档旧入口。

已实现纯输入函数dense_state.py：初始仍issue-only top3，连续真实源码窗口、紧凑标记、剩余预算扩展邻近上下文；后续按真实已发生文件变化动态选择实体并保留issue锚点。当前未实现完成工具输出候选证据，不能声称已接入。按可见内容去重，明确删除/未知；192 initial、128 update、4096 episode不变。尚未接入online provider/proxy/builder，旧runtime未改。旧607题全部development，标签由独立scorer读取，生成Landlock实际拒绝标签访问。不能把纯函数通过等同在线或GPU验收。

R1三个方案111/106/120目标行命中，均输旧129；全部失败保留。R2及R3 compact130/diverse108/expand143，分母366（nominal exact370，4未映射）；expand完整目标范围88，旧53。+14/366=3.83pp，未达事先+5pp开发门槛，不开训。真实使用token中位数165->190，不能称每例token完全相同。详见reports/RESEARCH_PROGRESS_20261028.md和各轮AGGREGATE.json。

242/366候选命中中，242个目标至少一条行/锚点均能放入192；oracle仅scorer，不能用于生成。剩余99漏点中84目标含issue词、42离最近窗口>20行；下一步结合局部边界与控制/数据依赖进行事前冻结的新设计，而非只继续扩局部窗口。候选全文字面成本中位1448.5（可能含class/method重叠，非最优压缩下界）。独立验证可用3064任务/123仓库，其中221任务来自607未见28仓库，已排除Verified500；仅metadata inventory，未冻结、未评分，不能称独立验证通过。

R2动态构造先因source1500文件容量拒绝新增文件（原失败保留）；按UID只筛容量后，第6例旧issue高分挤掉真实变化窗口，修改->回退可见内容相同被去重。R3只把真实changed_lines窗口优先，W0排序不变。完整607复核结果一致；16字节tokenizer本地契约、16真实Qwen tokenizer契约通过。24真实W0+构造新增/修改/回退全部通过：old新增目标0/24,new24/24；noop24/retry24/rollback24；max update128。仅构造事件，非真实Actor rollout/真实bug覆盖/GPU验收。R3源SHA cd9438f8684b15f94b68a4c1df12c2971ea41efc9ee213e2fade24efada39a53。源码备份archive/r1_before_context_revision、r2_before_dynamic_priority_fix。

唯一最新队列screen lego-pi-dynamic-dev-r3-20261028已完成exit0，无健康运行job待重复启动。远端logs/development_r3/{state,exit,generation.log,score.log,real_contracts.log,dynamic_constructed.log}；私有输出.private_development_r1/r2/r3不得导出。静态生成约3分钟，24动态场景81秒。heartbeat id pi已调15分钟，允许按后续耗时15–120分钟调整。下一轮应实施研究而不只轮询；完成/失败/需行动才通知。

Git工作树versioning/icps-dynamic-state-20261028，branch codex/icps-dynamic-state-20261028，draft PR#3 https://github.com/Jay-Juice/Lego-RL-main/pull/3。R1 e5d80f0、R2 ba70368完整保留；R3及报告已提交并push 0d1f87b。旧35源SHA未变，SAO/model/optimizer/runtime/recipe未改；新copy仅继承env/start被安全禁用。全部源以Windows为准，继续A800/AGENTS备份/WSLpreview/sync/SHA，不能热改或删挪远端资产。
