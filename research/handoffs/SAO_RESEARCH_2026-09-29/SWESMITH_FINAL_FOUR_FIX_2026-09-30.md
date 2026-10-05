# 最后四题修复与镜像来源核查

用户要求把已找到方向的四题修复做完，而不是继续停在解释阶段。本轮没有删除题目，没有改SAO训练算法、共享Python/Docker环境或历史数据。

## 四题的实际修复

| 任务 | 修复 | 独立容器双侧对照 |
|---|---|---|
| Tldextract pr_325 | 可信测试报缺本地scripts模块、候选确实缺release.py时，识别为业务实现未完成；不是基础设施失败 | bug=0；oracle=1，60测试通过 |
| Patsy pr_140 | 同时检查候选顶层旧Mapping导入、当前解释器特性及所有收集错误的具体来源，识别该业务兼容bug | bug=0；oracle=1，147测试通过 |
| Pyquery shuffle | 验证内嵌测试内容未改，再检查函数docstring位置被错误return破坏，且pytest只报告这个预期节点不可发现 | bug=0；oracle=1，109测试通过 |
| Conan pr_15457 | 把已有离线CMake 3.22.1复制到该任务镜像，使用项目支持的conftest_user工具路径配置；不关闭测试 | bug=0，38失败；oracle=1，38通过 |

Conan错误版本的失败来自业务API不匹配：Git.__init__不支持excluded参数，已确认不是继续缺CMake。正确补丁在同一环境中全部通过。

前三题采用**验证器持有的限定规则**，而不是“所有pytest exit2/4都算0”。规则同时要求候选源码证据与pytest日志/XML证据吻合，先执行原测试防篡改检查；没有读取或应用参考实现来修正候选。未知错误、额外依赖错误、缺报告、错误命令参数继续无有效奖励。规则覆盖已证实故障，不声称解决所有可能的收集错误。

## 镜像到底是下载的还是我们构建的

两层都有。下载的是SWE-Smith基础镜像；我们基于它创建每道Harbor任务镜像。

本次Conan基础镜像为：
`jyangballin/swesmith.x86_64.conan-io_1776_conan.86f29e13@sha256:db8589f5c3994d4c1559118778f8730af62626bf053d53f1a35c5ea2710074a2`

旧任务Dockerfile只在这个基础镜像上切换题目分支、删除Git历史、创建日志目录。**没有删除CMake的步骤。** 本轮另外启动未追加我们任务层的原始digest镜像，只读检查确认：PATH中没有cmake，项目配置预期的`/usr/share/cmake-3.15.7/bin/cmake`也不存在，`/opt`只有miniconda3。

因此这一题确实是下载的基础镜像未包含所选测试所需的外部构建工具，不是下载损坏，也不是我们的层把库删了。CMake是外部程序，不是仅安装Python包就会自动具备的依赖。项目的测试配置还写有CI机器上的固定工具目录；“镜像能启动/项目能导入”不等于所有选定功能测试都可运行。不能仅凭这个本地证据推断上游全部评测流程如何补工具。

同时，其他适配问题必须分开归因：PATH没有带测试虚拟环境、整文件恢复覆盖业务修复、遗漏AL已有环境适配，属于我们这边的问题；Patsy的Mapping导入、Tldextract缺业务模块、Pyquery代码顺序错误，则是任务本来要求模型修的bug，不能由环境初始化偷偷修掉。

当前CMake来自服务器已有的`/opt/cmake-3.22.1-linux-x86_64`，仅复制到新任务镜像`/opt/lego-cmake`；所有文件SHA和版本记录在本轮日志，没有在线安装或改共享环境。

## 证据与范围

远端根：`/media/ubuntu/D1/zsj/Lego-RL-main`。

- 四题双侧控制：`logs/swesmith_final_four_v5_20260930/summary.json`，4/4通过。
- 镜像来源：同目录`image_origin.json`；Conan子目录`cmake_provenance.json`记录工具文件SHA。
- 原始错误代码、正确补丁、构建日志、pytest XML与逐项判分理由都独立保存，不覆盖上轮证据。
- 边界单测：`tests/test_swesmith_collection_verdict.py`，Windows与A800均5/5；包含未知依赖、混合错误、过时日志、额外CLI错误不判0。
- 真实Harbor验证：`logs/swesmith_final_four_harbor_v5_20260930/PASS.json`，11/11通过：4题各自bug0/oracle1，移除numpy、非法pytest参数、篡改内嵌测试3个反例均无有效reward。
- 本地/远端源码SHA：`audit_deployment_manifest_data_v5_20260930.json`及远端`logs/swesmith_v5_source_sha_20260930.json`，5/5一致。

完整新版本已生成：`data/swesmith_python_full_v7_verdict_v5_candidate_20260930`及同名parquet，6248题、原AL v7顺序不变，pending=[]，上轮v4与历史6242资产不变。此前167题隔离已全部完成专项恢复，另6道Pandas遗漏题也已恢复。累计本次恢复路径涉及的186个不同任务控制通过，不是全6248逐题动态认证。

训练保持停止，没有重算历史模型分数。收尾八卡均14MiB，无本轮审计容器在运行；D1约96.45GiB。没有删除用户数据。
