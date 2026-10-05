# 新一轮batch64：启动配置与环境修复证据

## 范围与归因

本轮由用户授权从原始Qwen3.5-9B重新训练，不续旧step130。不能将适配器问题、离线资源不足和上游代码缺陷混为一谈，也不能把专项控制通过宣称为6248题全部动态认证。

| 项目 | 证据与处理 | 归因边界 |
|---|---|---|
| 业务源码被测试恢复覆盖、子进程PATH缺失 | 此前同一oracle在恢复顺序改变前后结果不同；已保留可信测试边界并修复PATH | 已确认是本地Harbor适配引入 |
| Pydicom离线数据 | 原相同oracle：112通过、6失败，日志为下载失败后文件路径为None；加入79份已有官方文件（逐份SHA核验）后118通过。bug仍117通过、1失败 | 当前离线资产适配遗漏；不能据此指责上游联网环境 |
| Sunpy固定IERS数据 | 使用已有固定文件及SHA；所选两组bug0/oracle1，另真实Harbor双侧通过 | 迁回旧AL的环境准备，不改业务答案 |
| Modin资源 | 保留5个任务，使用原AL的单pytest进程及Ray资源上限，5组bug0/oracle1；真实Harbor双侧通过 | 环境执行方式迁移，不是SAO算法修改 |
| Tenacity顺序 | 保留同一测试集合，只按模块聚合，5组bug0/oracle1 | 迁回旧AL避免异步测试模块来回切换的兼容设置 |
| Tornado原生runner | 15组双侧通过。初版报告桥接把测试函数异常也当环境error，是本次新增映射错误；修正为检查异常traceback是否经过实际测试方法，setup/teardown/loader错误仍未决 | 不把所有非零退出算失败，不修改断言或模型答案 |

Pydicom固定oracle SHA：`641ee96771ff68bac3908d0c18b6b8d6fbba405f231ead990fd1c3cf05a58be0`。资源补齐前两侧各约213秒，补齐后各约1.5秒；失败控制未被修成成功。

## 验收与资产

- 原167隔离任务及6个Pandas遗漏任务已在之前版本恢复；v5最后4题验收保留。
- 本轮剩余特殊环境29组bug/oracle全部通过；Tornado判分桥接Windows/Linux专项测试各2项通过。
- 真实Harbor另8场景通过：Tornado、Modin、Sunpy、Pydicom各bug0/oracle1，异常均空。
- 新数据为`data/swesmith_python_full_v7_verdict_v6_20260930.parquet`，6248题ID和顺序与v5一致。全索引路径、脚本语法、124个基础镜像缓存检查通过。没有重新删题。
- 旧失败记录、旧数据和镜像保留，未以通过复验覆盖历史证据。训练激活标记与全量动态认证标记分开，后者仍为false。
- 新源码/配置7文件WSL精确dry-run、同步、SHA7/7一致，见内层`audit_deployment_manifest_training_v6_20260930.json`。没有部署空批次guard，也没有改优化器或SAO数学实现。

远端证据均在`/media/ubuntu/D1/zsj/Lego-RL-main/`下：

- `logs/swesmith_training_v6_20260930/summary.json`：第一次对照，不删除失败记录。
- `logs/swesmith_training_v6_native_recheck_20260930/summary.json`：Tornado报告桥接修正。
- `logs/swesmith_training_v6_pydicom_recheck_20260930/summary.json`：最终29/29。
- `logs/swesmith_training_v6_harbor_20260930/PASS.json`：真实Harbor8/8。
- `data/swesmith_python_full_v7_verdict_v6_20260930/runtime_assets/pydicom/provenance.json`：79份文件来源与SHA。
- `logs/sao_b64_w32_v6_20260930_asset_preflight.json`：全索引与实际配置检查。

## 训练参数与空间

| 参数 | 新实验 |
|---|---|
| 起点 | 原始Qwen3.5-9B |
| TRAIN_BSZ / TRAIN_PROMPT_BSZ | 64 / 64 |
| TRAIN_MINI_BSZ / Actor mini / Critic mini | 64 / 64 / 64 |
| AGENT_NUM_WORKERS | 32（总worker数） |
| Actor LR / Critic LR | 1e-6 / 5e-6，与旧实验一致 |
| Critic warmup | 保留20步；新batch下为1280样本，旧batch16下为320样本 |
| Critic epochs | 2 |
| Response / context / turns | 65536 / 98304 / 128 |
| 保存 / 评测 | 每10步完整保存 / 不做中途评测 |
| 新checkpoint保留 | 全部保留，空间不足前通知，禁止自动最新3轮转 |
| 实验目录 | sao-qwen35-9b-swesmith-b64-w32-v6-20260930 |

本轮用户授权删除上一轮原checkpoint，已精确删除80/90/100/110/120/130及旧marker，回收约1060GiB；HF合并模型和所有评测结果保留。D1清理后约1156GiB，每份新完整checkpoint约177GiB，只能容纳约6份，预计97个训练step，须提前通知空间风险。

2026-09-30 01:05:44（服务器时间）启动screen `1486046.lego_sao_b64_w32_v6_20260930`，日志`logs/sao_b64_w32_v6_20260930_launcher.log`。启动前GPU全部空闲、无Ray进程、checkpoint目录全新。此处只记录启动，首个正式step的成功仍须后续日志确认；90分钟自动化在首步成功后才启用。


### 启动记录更正

首次启动在训练前因D1临时目录路径过长，触发Ray UNIX socket长度限制而退出；这是本次启动配置问题，未发生训练更新。保留失败日志。将TMPDIR改为指向D1目录的短符号链接，并显式连接本次launcher的Ray集群后，01:11:04启动第二次screen `1489308.lego_sao_b64_w32_v6_20260930b`。新日志为`logs/sao_b64_w32_v6_20260930b_launcher.log`及同前缀train/vllm日志。配置最终SHA为`edd8eebe030059c44fae95f4c379d15e3f6e0459d3e1adc26a99bfafc74f01df`。01:17检查八卡模型已加载，仍待首个正式训练step确认。

## 90. 2026-09-30 首批发现Redbot Git标签兼容问题，真实对照修复
- b启动已完成推理初始化并开始step1，但Redbot func_basic__jhzylht3无reward。日志证明pytest导入阶段ValueError: 3.5.14.devbaseline+...；模型patch只改repo_manager.py，未改version。Harbor predict_patch默认创建harbor-baseline tag，Redbot split("-",3)将baseline读为count，故与新建Git基线冲突。这是运行适配问题，不是SAO算法错误或模型失败；旧该轨迹保留unresolved并过滤。
- 原bug和固定oracle真实Harbor三场景：旧tag+oracle仍无reward，新harborbaseline+bug为21pass2fail/reward0，新tag+oracle为23pass/reward1。证据logs/redbot_baseline_tag_control_20260930/PASS.json，oracleSHA189ab8be5388c7fec8d772b02ad07790f7825cc7b5e1813aa70ec7336ced7ec1。没有替模型补答案。此前nop对照predict_patch disabled未覆盖这条链，已补实际baseline初始化路径。
- 依用户报错修复重启授权，精确Ctrl-C停止1489308 b screen，scoped Ray退出，八卡14MiB；只按compose config路径归属停本run残留容器，不动六个其他旧容器。旧训练日志/轨迹保留，未产checkpoint，待新独立v6c起点base重新生成首批。
- 新独立config scripts/train/configs/sao_sync_1node_qwen35_9b_swesmith_b64_w32_v6c_20260930.env（SHA2946bc6bb71438cbfdaeb171956fa2ef5d6931495dee15d44aaf883040ca4e21），source v6相同recipe，EXP后缀v6c，日志后缀20260930c，专用agent_loop_config_oh_docker_b64_v6.yaml（SHA2aa73dd5ef0a04f2e1b05631d4e2043a1a1afd250943d3774b1e595e392780f0）只加predict_patch.baseline_tag=harborbaseline。两份经WSL精确同步，LF换行预检；源码不改core/loop。自动化仍PAUSED，首正式step成功后启用90分钟。
- 首批日志两条UnboundLocalError Traceback为题目instruction内示例，非程序异常；read-only monitor已将关键词命中标为候选，并分开读取真实result.exception_info。不要见到关键词就修或重启。

- 01:35:54新screen1703700.lego_sao_b64_w32_v6_20260930c已启动，launcher logs/sao_b64_w32_v6_20260930c_launcher.log，正式dryrun0WARN、SHA2/2、八卡空闲后启动。新EXP=sao-qwen35-9b-swesmith-b64-w32-v6c-20260930，日志和轨迹均独立，原base起点。不要重复启动。
- 01:55首批64任务全部result、43通过21失败、exception0；实际训练中Redbot23pass/reward1/exception空，全部实际TrialConfig使用harborbaseline。约01:55开始训练计算，02:25通过Ray read-only state确认8个WorkerDict.critic_train_mini_batch RUNNING。02:28首正式step尚未返回，8卡31GiB/100%，无新增故障；不能只凭GPU忙宣称成功。旧batch16每步Critic更新约555–664秒，当前batch64计算更长，继续守首步正式有限loss/gradient，再启90分钟监控。py-spy非阻塞栈读取权限拒绝，未提权/改系统设置。


## 91. 2026-09-30 首正式step1通过，90分钟监控已启用
- 02:54读回正式step1：64有效，43通过/21失败，result.exception_info为空，invalid_count=0；reward_mean=0.671875。Critic loss=2.566780637949705，grad_norm=41.082366943359375，LR=5e-6；记录的数值指标均有限。远端证据logs/sao_b64_w32_v6_20260930c_first_step_metrics.json。
- 首步4300.871秒（71.68分钟），generation830.759秒、values443.058秒、Critic update2977.175秒（49.62分钟），total_tokens=3105524。当前已进入step2任务生成，准确screen1703700.lego_sao_b64_w32_v6_20260930c保持运行，不重复启动。计算阶段长时间日志稀疏不等于停滞，需结合正式指标/Ray任务/GPU判断。
- 原critic_warmup20保留，前20步仅Critic，不声称首步Actor已更新。EV=-20.94088363647461、response clip_ratio=0.25属于需持续观察的训练指标；本次仅证明首步环境与数值运行成功，不证明训练效果改善，不自动改算法或因初始EV低而重启。
- 数据6248集合不缩减；全部静态检查、专项对照和真实Harbor验收不等于全6248动态认证。首批64实际任务无环境异常；题目instruction中的Traceback文本不计程序故障。
- 既有automation lego-rl-sao已通过工具更新并读回确认为ACTIVE、每90分钟，名称Lego-RL batch64训练巡检；提示全部替换为当前v6c训练状态，旧评测/轮转指令不沿用。平稳安静，仅故障/修复重启/保存异常/空间风险/完成通知。
- D1约1154GiB；新checkpoint全部保留，save10/test0，下一保存10。旧原checkpoint删除约回收1060GiB，HF与评测仍保留。新checkpoint没有删除授权，提前在约两份保存空间加日志余量时报告，不能写满。


## 93. 2026-09-30 06:03 metrics超时字段合并修复并重启v6d
- 05:57巡检发现v6c已于04:39退出。step3 Parso最后轨迹AgentTimeoutError（实际1800秒，先前仅看max_timeout3600不能代表最终有效超时；本次已纠正），容器6c4d133262f6自动清理；step3合并在DataProto.meta_info.metrics报agent_timeout缺字段。正式仅step1/2，未到save10，无checkpoint，需从原base重算。不是loss/OOM，不能假称已恢复第2步状态。
- 根因是原适配层正常metrics缺agent_timeout/verifier_timeout默认值；之前回归只测reward_extra_info，漏真实metrics层。新增_TRIAL_STATUS_METRIC_KEYS统一三个标志，在正常、直接Harbor调用和empty分支填0，异常仍按原逻辑置1；不改判分、过滤、核心loss或空批次guard。
- 扩展utils/validate_reward_metadata_concat.py用真实源AST初始化与真实verl DataProto.concat，旧缺字段负对照复现，正常/Agent超时/Verifier超时/未决/early-empty全120排列通过，所有literal metric写入key均有默认值。最初测试返回值断言误以为list，读真实实现后修正为dict-of-lists，生产修复未因此改变。日志logs/metrics_concat_regression_20260930.log。旧源备份audit_backups/pre_metrics_20260930。
- Windows精确WSL dryrun/sync到隔离验收再生产，SHA3/3：loop e8d81f5a1737a8d1655ed38c5051737ca579819586e8898ffeca9d42b9d13594，回归9ecfa67282688b1c726609ded491be509f184ce08c287d7614cef425c0c77c2d，新config269b979de3785e3bd5c9147d1c53de8b8ca566bae69500a3317828909fbe3ae1；旧cdad loop SHA不再适用，禁止回滚。
- 正式dryrun退出0，确认八卡14MiB、无raylet/gcs_server/本轮screen后，06:03:24启动2372130.lego_sao_b64_w32_v6_20260930d。独立EXP=sao-qwen35-9b-swesmith-b64-w32-v6d-20260930，config scripts/train/configs/sao_sync_1node_qwen35_9b_swesmith_b64_w32_v6d_20260930.env；launcher logs/sao_b64_w32_v6_20260930d_launcher.log，同前缀_train/_vllm。参数仍batch/mini64、workers32、criticwarmup20、原6248v6、tagharborbaseline、save10/test0、keepall，不改公式。原v6c日志/轨迹保留不混，不重复启动。
- 监控脚本已指向v6d；继续90分钟巡检。尚待新run首正式step成功，不能沿用旧run成功声明。D1约1154GiB，新checkpoint不得自动删；其余安全边界不变。
