# 训练与评测检查及修复报告

日期：2026-09-26（Asia/Shanghai）

## 1. 结论与本次执行边界

本次针对当前 Lego-RL Qwen3.5-9B 同步 SAO 实验进行代码和历史产物审计，随后按用户要求修复可在本地独立验证的问题。

**本地源码已修复，服务器尚未部署。** 当前 step40/50/60/70 独立 Verified500 评测应继续沿用现有版本和协议。没有停止或启动服务器作业，没有修改服务器训练数据、模型、checkpoint、评分产物、环境或定时任务；没有使用重置卡。代码修改留在 Windows 工作区，未提交或推送。

不立即同步的原因：评测脚本会在运行途中启动新进程、加载 Python 文件，并在结束时调用汇总工具。此时部署会让同一个 run 混用新旧版本。此次评分语义的修正还会改变后续训练样本的有效性，必须单独记录版本边界。

- Windows 源码根：`D:\ai project\RL学习\Lego-RL-main\Lego-RL-main`
- 服务器运行根：`/media/ubuntu/D1/zsj/Lego-RL-main`
- 本次审计基于本地 `1db178b` 及当前运行日志；修复前本地工作树干净。
- 所有“已通过测试”仅指下述本地回归测试，不等价于真实八卡/Harbor集成验证。

## 2. 已确认问题及本地修复

### 2.1 训练 verifier 内部超时被当作 reward=0（优先级最高）

证据：读取本实验 1,147 份 trial 结果和 verifier 输出，发现三条 `SWE-Smith verifier error: TimeoutExpired`，内部 pytest 超时为300秒，但 Harbor记录均为 `exception_info=None`、`verifier_result.rewards.reward=0.0`。

| step | instance_id |
|---|---|
| 32 | iterative__dvc.1d6ea681.func_pm_remove_loop__tu21q9d9 |
| 50 | python-trio__trio.cfbbe2c1.func_pm_class_rm_funcs__z53t7qz3 |
| 53 | python-trio__trio.cfbbe2c1.func_basic__e95hvdta |

证据位于服务器本实验 `harbor_trials/sao-qwen35-9b-swesmith/sao-qwen35-9b-swesmith-64k-full-sp8-tokenpack-v1/step_00NN/` 对应任务的 `verifier/test-stdout.txt` 和 `result.json`。1,147是产物数量，包含恢复/中断/验证相关记录，不代表1,147道唯一训练题。

旧代码先创建0奖励，异常后仍返回0退出码，因此上层timeout指标漏报。超时可能由错误补丁或环境引起，现有结果无法区分；不能直接把这三条改成正奖励。

本地修改：`utils/prepare_swesmith_harbor.py`

- 删除预置零奖励，清除同目录旧reward和旧状态。
- pytest退出码0/1分别产生明确的1/0奖励。
- 退出码2/3/4/5、TimeoutExpired及其他异常不产生reward，返回非零退出码。
- 写入 `grading_status.json`，区分 `scored` 和 `unresolved`，记录退出码/异常。
- shell wrapper传递失败，不再无条件 `exit 0`。

**尚未生效的部分：** 已生成6242个任务目录各有独立的测试脚本副本，修改生成器不会更新它们。评测结束后需要生成新版训练任务资产并验证，而不是仅同步这个Python文件。旧数据和旧日志必须保留；本次没有补测、更改历史标签或重训受影响step。

### 2.2 无 verifier verdict 的部分轨迹可能进入训练

旧Agent非零退出路径可在缺少判定时提交reward0；全部重试失败后也可能留下可用partial tokens。审计的1,147份结果没有缺失verifier_result，但这不排除2.1的内部伪判定。

本地修改：

- 新增 `src/verl_patch/agent_loop/verdict.py`：只接受显式、有限的二值0/1，不把缺字段、None、NaN/Inf或其他数值当作reward0。
- `builtin_swe_agent_loop.py` 跟踪最终提交是否有有效verdict。
- 无有效verdict的轨迹保留审计元信息，标记 `verifier_unresolved`，进入现有空输出/过滤路径，不用于正常负样本训练。
- 审计中单独标识verifier未决，避免直接将它统计成环境搭建失败；兼容现有verl时仍使用已有可过滤的termination类别。
- 有效reward0仍保留，既有重试最终取得有效verdict的行为保留。

**部署门槛：** 本地测试执行了真实trial方法控制流，但Harbor和代理是替身。必须在完整训练环境确认空样本过滤、批内指标聚合、异常文件提取及全失败batch行为。现有“无判定时重新生成”的重试策略没有在此次重构为固定补丁重验，后续应进一步区分生成失败与评分失败。

### 2.3 checkpoint轮转没有待评测保护

step30曾因代理误解用户意图而被轮转删除，未评测，目前没有找到原checkpoint副本。本次修复不能恢复它。

本地修改：`scripts/train/rotate_complete_sao_checkpoints.py`

- 年龄和“保留最近三份”不再单独构成删除授权。
- 读取本实验根目录的 `checkpoint_retention.json`。
- `protected_steps` 保护待测/固定里程碑，优先于删除批准。
- 只有出现在 `deletion_approved_steps` 且不受保护、也不在最新keep份内的完整checkpoint，才可成为删除候选。
- 缺少策略或存在未批准候选时，`--apply`拒绝删除；预览仍可查看。
- 保留原有固定实验路径、marker、各分片和data.pt检查。

未来策略示例（**没有写入服务器**）：

```json
{
  "version": 1,
  "protected_steps": [40, 50, 60, 70],
  "deletion_approved_steps": []
}
```

当前删除watcher应继续关闭。不可仅因评测结束就自动批准删除；需确认评测产物/必要导出保留、磁盘规划及用户保留要求。最新keep份之外可以额外保留受保护模型，空间不足时应报告，不自动解除保护。

step40现有同盘硬链接归档可防目录轮转删除，不是跨盘灾备。checkpoint文件非空检查也不等价于逐文件校验和或真实恢复验证。

### 2.4 HF结构校验可能对空目录通过，成功提示过度

本地修改：`utils/verify_merged_hf_keys.py`

- 拒绝无safetensors文件和空权重集合。
- 拒绝跨文件重复参数键。
- 检查分片索引与真实键/文件映射一致；多分片缺索引拒绝。
- 默认要求完整键集合；缺少MTP必须显式使用 `--allow-missing-mtp`，不接受宽泛的任意含mtp字符串键。
- 新增可选 `--check-finite`，逐tensor在CPU检查NaN/Inf。
- 成功提示仅声明键/形状/索引通过，明确未证明源FSDP数值等价。

当前已合并的20/25/40模型此前实际校验为775/775，并非空目录误通过。**本次未重新扫描这些大模型，也未执行真实FSDP→HF数值对照。** 新的finite扫描需要torch/safetensors及CPU内存，部署后择空闲时执行。

### 2.5 汇总工具对异常reward和非500题集合的防线不足

本地修改：`utils/summarize_verified_shards.py`、`utils/merge_verified_runs.py`

- NaN、Inf、非二值、无法解析的reward记入 `invalid_reward_files`，不作为有效计分。
- 单run汇总新增严格500题数量门槛，避免499道配置自身“覆盖完整”就报完成。
- 任一异常reward导致完整性检查不通过；重复、缺题等原有检查保留。

没有改写当前/历史summary，没有改变既有分数。汇总仍保留错误计数供人工审计，不能仅因500份reward存在就忽略历史异常或认定为严格官方结果。

## 3. 本次测试与局限

本地Windows Python运行：

```text
python -m unittest discover -s tests -p test_audit_safety.py -v
python -m unittest discover -s tests -p test_rotate_complete_sao_checkpoints.py -v
```

**10 + 1 = 11项测试通过**，包含参数化子场景：

- 成功测试/真实测试失败保持1/0。
- pytest退出码2–5、300秒超时不保留旧奖励。
- 非零Agent退出无verdict、重试耗尽无verdict均排除；真实0奖励及后续成功重试保留。
- 无权重目录、空集合、错误形状、重复键、错误分片索引拒绝。
- 500题合法汇总通过，499题和NaN/Inf/非二值奖励拒绝；互补run汇总也拒绝异常奖励。
- 删除无策略时拒绝；保护优先于批准；明确批准的旧完整checkpoint可以删除，最新三份保留。

测试无需GPU。由于本地没有torch/safetensors/omegaconf/verl完整依赖，模型读取接口使用测试替身，trial方法使用真实方法AST和Harbor/代理替身。没有声称运行完整Agent-loop测试套件、真实容器或八卡canary。

首次测试受Windows Python 3.13临时目录0700权限和默认GBK读取影响失败。测试已改用继承工作区权限的普通唯一目录，源码显式UTF-8读取，随后上述11项通过。最初生成的10个 `tmp*` 目录因权限限制未能清理；它们是本次测试残留，不是项目数据，未修改ACL或申请扩大权限。名称：`tmp_4u_8ksd`、`tmp58hg8d60`、`tmpa013w5ra`、`tmpa9t6uov2`、`tmpcau93hg1`、`tmpfhm3ron4`、`tmphlda1023`、`tmpmk18pjsy`、`tmptrwj5ghe`、`tmpv3_acddt`。后续同步应仅按明确文件清单，不传这些目录。

## 4. 本轮评测完成后必须处理的事项

### 4.1 先冻结当前四份评测结果，再切换版本

1. 按旧独立协议完成40/50/60/70，各自500唯一题、独立run ID，审计Agent/环境/verifier错误。
2. 固定补丁复验只用于恢复评分，不重新生成后择优；保留原始分数、恢复后分数和逐题来源。
3. 确认全部评测进程退出，再按Windows源码差异与SHA精确部署本次修改。不能在单个run途中切换汇总/评分实现。
4. 同步时必须包含新增 `verdict.py`，不能只同步调用它的Agent loop。
5. 数据任务脚本另建版本，记录生成器SHA、原数据SHA及评分协议版本；不能无备份地全量覆盖当前6242题。
6. 在真实Harbor验证：通过、测试失败、内部超时、收集失败和无verdict分别符合新分类；再验证过滤和训练恢复。未经此检查不直接续训。

### 4.2 补齐数据有效性检查

- 当前全量manifest共6242项，controls均为空；工作总结记录5题baseline0/oracle1检查通过。不能由此推出全量已验证。
- 18份日志包含collection error，部分是SunPy warning-as-error/`.hypothesis`收集问题。它们未必全部是环境故障；要检查原始buggy、oracle及模型补丁，不能统一改成无效或负例。
- 优先检查三条内部超时和18条收集错误涉及的任务，再按仓库、测试时长、任务类型分层扩展controls。
- 379项没有PASS_TO_PASS是数据事实，不自动构成错误，但当前奖励覆盖的是选定测试，不等于完整仓库回归通过。
- 应补数据交集/来源审计：仓库相同不等于泄漏，需查具体issue、补丁、commit及训练样本生成来源。

### 4.3 Critic质量与训练设计

Actor开始更新后的49条可解析step指标中，17条explained variance为负、无一超过0.4、18条Critic grad norm超过30；step31–69的explained variance均值约0.077。部分停训节点在checkpoint完成后即中断，未写出整条正式指标，不能把49条当作所有Actor更新数量。

这证明“成功跑完warmup”不足以说明Critic有效；不证明Critic是效果下降唯一原因，也不构成现在修改学习率的依据。后续应在固定轨迹上检查：value/return对齐、action mask、预测偏差、正负样本拟合、梯度裁剪频率、冻结模式及优化器实际更新。一次只对比一个因素，使用独立训练验证集而非反复调Verified测试集。

当前70步约1120个batch样本量，仅约占6242的18%，并未完成一轮全量训练；该估算不是去重任务覆盖。Actor从step20开始更新，step70约为第51次Actor更新。

### 4.4 轨迹预算与奖励分配

训练loop对超出response窗口的轨迹只保留前缀，同时保留完整任务reward。早期日志平均约25.5%样本达到response窗口上限，step31–69约7.2%。该做法不自动等于未来信息泄漏，但后半段动作未直接参与训练，需按截断/完整轨迹分别分析。不要在现有实验中途直接改变预算或奖励语义。

### 4.5 评测可比性与研究结论

| 模型 | 历史Verified500结果 |
|---|---:|
| base | 279/500，55.8% |
| step20 | 272/500，54.4% |
| step25 | 262/500，52.4% |
| step30 | 未测；原checkpoint已删除，目前无副本 |
| step40/50/60/70 | 本报告不预填最终结果，以主任务各run完成审计为准 |

base是互补run合并且包含固定补丁复验；20/25也有复验。这是内部对照，不能直接称严格leaderboard成绩。temperature0.7下应做逐题配对分析，必要时重复固定checkpoint评测，不能仅由少7题/17题作因果结论。比较多个checkpoint并从同一测试集选最好模型也会产生选择偏差。

原训练内98K验证与旧独立262K协议不同，当前已避免混用。训练和评测预算不同本身可以成立，但所有checkpoint间的评测预算必须相同。

本轮是9B稠密模型、同步SAO、自选SWE-Smith子集、冷Critic的适配基线，不是作者35B-A3B实验的逐项严格复现。当前仍未完成privileged-critic idea的受控对照；后续应做相同配方SAO与PI-SAO，只改变Critic特权输入。

## 5. 已核对、没有发现相应错误的部分

- 实际恢复代码加载Actor、Critic和data.pt，日志明确从step25/30接续；没有发现datalaoder缺失警告或从头跑的证据。这不等同于逐样本顺序已做完整去重证明。
- Actor/Critic实际学习率维持1e-6/5e-6，恢复前后主要训练预算已在既有日志核对。
- CUDA包装器漏用导致的首次续训失败发生在初始化，无新step；之后用原用户级包装器恢复。
- base与20/25/40合并模型chat_template文件相同；实际加载base和40 tokenizer的词表/特殊token一致，两个抽样聊天输入编码一致。不是所有可能输入的等价证明。
- 658份正奖励训练记录均有至少一个passed测试摘要，未发现明显全跳过却得1的样例。
- 当前40/50/60/70已保存并保留，本次没有删除任何服务器checkpoint。

## 6. 下一次续训的最低门槛

先结束并审计四份旧协议评测；完成评分故障分类和真实环境集成验证；保存版本边界及逐题异常台账；明确checkpoint保护清单；根据固定轨迹Critic诊断设计下一项对照。改变评分有效性后，应标记为新的训练阶段，不能将前后曲线冒称完全同配方连续实验。
