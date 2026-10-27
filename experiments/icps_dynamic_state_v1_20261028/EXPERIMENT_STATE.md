# 2026年10月28日 独立动态 PI 研发

状态：R4_INDEPENDENT_COVERAGE_NOT_ADMITTED_TRAINING_DISABLED，训练未启动。用户授权独立副本、原PI预算与SAO配方不变，验证动态候选/变化窗口/去重，合理收敛后可直接开启新freshbase实验训练；可以按阶段调整本线程监控间隔。旧ICPS v1.1与所有旧实验保持只读，不能恢复旧训练。
## R5已完成：保留旧证据可减少回退，但未优于冻结R4

唯一R5队列已exit0，flow对照607份完整输出与R4逐项一致；本地与远端3契约通过，607实际Qwen生成budget/精确源码/往返检查通过。guard_expand目标144/366、完整88（旧129/53），gain15/lost0，净+4.10pp未达开发+5pp。anchor_expand目标164、完整93，gain47/lost12，净+9.56pp但低于R4 flow169/98（gain56/lost16）。本轮不把任一方案晋升为新正式候选，不对确认集重测挑选；R4独立未通过仍有效，训练不启动。

结果说明保留旧窗口能降低覆盖回退，但同时占据新可执行窗口的预算；不能仅靠“保留全部旧信息”解决排序问题，也不能据此判定PI本身无用。下一轮先量化原607 proposal评分中的重复issue信号与候选竞争，再事前定义能提升非重复信息的排序/分配策略，保留本轮负结果，预算192/128/4096不变。不得在220确认题上继续调参；新候选仍需新独立确认、动态/在线/Harbor/八卡/SAO对照。无健康job待重启。报告reports/development_r5/{FROZEN,AGGREGATE}.json，私有输出.private_development_r5不下载。

## R5开发推进：先保留当前旧证据，再使用剩余预算

本轮只读原607开发输入，未读取220确认集逐题结果。R4损失诊断完成exit0：丢失16题中14仍有单独可装入192的目标proposal，但全部排在第6位以后；16均有可执行目标，仅2同时触及被排除声明/docstring，不能简单归因于排除docstring。候选已包含但两法均未命中的57题中47也有可装入proposal。分类可重叠，均属scorer事后oracle分析，不给生成器坐标。证据reports/R4_DEVELOPMENT_LOSS_AUDIT.json。

修改前R4冻结5源及状态备份archive/r4_before_guard_experiment，R4源与freeze原位不改。R5_PLAN.md在新输出前固定两个W0原型：guard_expand保留当前oldS1全部真实窗口，用紧凑格式节省后仅加窗口/邻接上下文，compact不能装入则原样保留本次当前S1（不是旧状态PI）；anchor_expand只保留当前S1首窗口，再填flow候选。两者原预算、top3候选和最多3窗口不变；新增独立guard_windows_r5.py，无在线/训练实现修改。

本地与远端3个契约均通过；唯一screen lego-pi-dynamic-dev-r5-20261028，ops/development_r5.sh，logs/development_r5/{state,exit,contracts.log,generation.log,control.log,score.log,supervisor.log}。正在607 Landlock生成oldS1、冻结flow对照与两新规则，之后必须607 flow完整输出等价再评分。无GPU/optimizer，不能把W0测试当动态/在线验收。第一次损失诊断SHA清单CRLF失败未执行，原failed_crlf保留，LF修正后诊断通过。

## 最新独立确认：未通过覆盖准入，保持停训

审计64份历史诊断metadata，从221库存排除1个额外已暴露任务，冻结220任务/28仓库；不是预训练未知数据，仅相对已审计PI诊断独立。manifest SHA a74551529b9d8831351dfe2b3489e3a4517db93e4cef21319db6ec2fc6050855。原CANDIDATE_FREEZE_R4.json及5份生成器未改，只测预先冻结flow_expand与旧S1，没有试其他方案。

只用现有pinned prepared images，177真实只读W0捕获成功，43只有本地build配置故按无build/pull规则列不可用，不替换；另1目标不在有界capture。176可评分/26仓库，名义分母仍220。主覆盖旧79/176=44.89%，新87/176=49.43%，gain17/lost9、+4.55pp；repo-cluster95%CI[-0.72pp,+9.03pp]跨0，独立覆盖门槛未通过。完整目标27->44/176（+9.66pp），候选命中同124/176，不能用完整目标的显著性替换预设主指标。全220严格已验证命中下界35.91%->39.55%，44不可用/未映射不视为正常失败。

目标行205->355，每千实际PI token目标行7.148->10.659（仅可评分输入的token密度代理）。这说明有扩大有效源码窗口的迹象，但尚不足以证明主覆盖改善可推广，更不是Critic学习或RL效果证据。scorer3契约通过，Landlock实际拒绝Gold/位置读取，生成输出先冻结再独立评分，身份/patch旧侧映射检查通过，无任务verifier、Actor rollout、GPU或optimizer。capture约23秒；generation耗时见远端receipt。logs/confirmation_capture_r4及confirmation_score_r4均exit0，没有健康队列待重启。

下一步保留本次确认的失败结论和冻结源，先在原607 development分析覆盖回退与候选转化，不在这176题上筛规则/反复试参。若对本确认逐题结果用于改设计，必须将它标为development；任何新候选都需另一份事前排除既有确认的独立清单，不扩大本轮样本/重采挑分直至显著，不降低门槛。在线接入/Harbor/因果gather/八卡/SAO配方对照均仍未完成，训练入口exit78继续禁用，旧训练不恢复。

公开证据reports/CONFIRMATION_EXPOSURE_FREEZE_R4.json、CONFIRMATION_CAPTURE_R4.json、confirmation_r4/{FROZEN,AGGREGATE}.json；私有manifest/captures/逐题输出仅远端.private_confirmation_r4。以下R1–R4开发记录保留为历史，不覆盖本次未准入结论。

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
