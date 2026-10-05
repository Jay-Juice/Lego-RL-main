# SWE-Smith→Harbor 适配修复及候选隔离版说明

## 结论与责任

已确认的业务源码覆盖、verifier 子进程 PATH 缺失，是本项目新增 SWE-Smith→Harbor 适配器的问题。`utils/prepare_swesmith_harbor.py` 在本地提交 `9730693` 中新增，父提交没有这个文件；不能归因于官方 SAO 算法。此前未发现这些问题是我们的疏漏。

**本轮没有证明原始 SWE-Smith 的167题无效，也没有完成所有题型的无损适配。**6075题是候选隔离子集，未用于训练，不是获准替代原6242题的最终训练集。原任务资产、parquet、历史结果及checkpoint均保留。

## 已修复并部署

- verifier 子进程 PATH 显式包含 testbed 环境，修复 Pyfiglet 等命令行入口找不到环境的问题。
- 生成器和 verifier 先检查全部恢复路径；只恢复明确的独立测试文件，拒绝不受支持的源码/文档内嵌测试路径。保留恢复可信测试以防修改测试作弊；补充意外payload、缺失文件和符号链接重定向检查。
- 引入 pytest JUnit 执行证据，区分正常测试失败与无有效verdict。收集/准备错误、全skip、缺报告、超时不产生虚假二值reward。准备错误也可能由模型补丁造成，不能一律称基础设施错误。
- 生成新版本而不覆盖原资产；不允许恢复运行时用不同verifier默默改写旧任务目录。
- 精确部署清单8文件（含验证/测试工具），生产SHA 8/8通过。旧文件备份：远端 `audit_backups/pre_swesmith_v3_20260929`。未改核心SAO/verl、未部署空批次guard、未改训练配置。

## 为什么候选版暂时少了167题

| 类别 | 数量 | 当前证据与状态 |
|---|---:|---|
| 疑似业务源码与测试共文件 | 145 | 文件名/路径风险集合；Parso、Patsy已复现整文件恢复覆盖oracle修复，不能推广为145题全部有坏标签。当前适配不支持，临时隔离。 |
| 文档内嵌测试 | 19 | 更严格路径策略排除的Parse/Pyquery文档或README测试；并未证明题目无效。 |
| 环境对照尚未通过 | 3 | Conan缺cmake、Furl兼容性待查、DVC无网络条件下超时；不能直接归罪原始数据。 |

这和原Agent Lightning数据筛选不是同一层：前者是题目/数据流程，当前新增限制来自我们的Harbor适配。正确后续是为源码内嵌测试、doctest等补上不覆盖业务修改的验证方式，并做同题bug/oracle和测试防篡改验证，再决定恢复哪些题；不能以多筛题代替修复。

## 验证及范围

- 本地旧专项回归10项通过；新增7项本地通过6项、Windows符号链接权限原因跳过1项，远端Linux7/7通过（含符号链接）。生产部署后Linux7项再次通过。
- 真实Harbor Trial + Docker + nop agent 9场景通过：pass、fail、collection、timeout、missing、setup_error、skipped、source_boundary、cli_path。证据：`logs/verdict_v3_harbor_integration_20260929b/PASS.json`。首次隔离集成因本地镜像标签尚未构建导致启动失败，保留原日志；显式本地构建后才完成上述验证。
- 原固定100题样本中，候选子集包含92题，全部bug=0、oracle=1；其余8题明确列为隔离，没有换题补足样本。**92/92不能作为原6242题或全部6075题动态验证通过的声明。**证据：`logs/swesmith_v3_controls_20260929/summary.json`。
- 6075题静态恢复边界与生成脚本SHA检查均通过；旧manifest、旧parquet SHA未变。证据：`logs/swesmith_v3_asset_validation_20260929.json`。
- 生成verifier SHA：`02f0b6a1fdef73728fd82dd8abe884087ec570728a496ca9bd167a516a79c975`。

## 数据与下一阶段

候选任务目录：`/media/ubuntu/D1/zsj/Lego-RL-main/data/swesmith_python_full_v7_verdict_v3_20260929`，对应同名前缀 `.parquet`。保留相对顺序，但集合改变；不得称完全相同训练配方。生成时源码快照保存在 `logs/swesmith_v3_controls_20260929/prepare_swesmith_harbor_at_asset_build.py`；其后仅调整旧目录保护的控制流程，生成verifier字符串SHA未变。

训练和监控继续停止，未启用候选版，未开始batch64实验。后续优先补全被隔离题型的适配，不能默认缩减数据；既有评分修复不能逆转历史梯度更新。D1约98.6GiB不足新完整checkpoint（约177GiB），本轮没有删除数据。
