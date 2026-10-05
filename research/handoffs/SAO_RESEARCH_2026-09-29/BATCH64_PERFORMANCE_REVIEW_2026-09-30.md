# Batch64 当前训练性能检查（2026-09-30）

结论：不是已证明的最快配置。有低侵入优化候选，但本次只读检查，没有改运行参数、暂停或启动竞争GPU作业，也没有做候选GPU测速。

## 实测依据

当前v6d已完成step1–5；检查时step6轨迹阶段已产生结果。前5步平均72.18分钟，生成18.15分钟、Critic更新47.04分钟，其余6.99分钟。当前前20步为Critic-only；Actor未更新，不能拿当前显存证明后续Actor安全。

旧batch16的step111–130平均28.03分钟，生成9.06、Critic9.75、Actor7.07分钟。当前平均训练token3216974，旧656090，相差4.90倍；Critic耗时相差4.83倍。因此当前Critic长耗时大体随token量增长，并没有证据表明batch64出现异常数量级减速。样本吞吐改善不可全部归功batch，因为当前未更新Actor。

当前硬件8×A800 80GB PCIe；topo显示0/1、2/3、4/5、6/7两两NV8，跨四卡组为SYS。SP8/DP1序列通信跨NUMA。Critic日志max allocated约28.26GiB、reserved31.83GiB，过去Critic计算现场nvidia-smi约35GiB。三者口径不同，也不保证所有更长序列的未来峰值。

## 源码核验

远端源码根 /media/ubuntu/D1/zsj/Lego-RL-main：
- third_party/verl/verl/workers/engine/utils.py:165–186：dynamic=True时使用token预算×SP；固定micro_batch_size只用于else路径。因此仅把micro_batch_size_per_gpu从1改2不会改变当前分批。
- third_party/verl/verl/utils/seqlen_balancing.py:394–408：按ceil(total_tokens / max_token_len)决定micro-batch数量，另有DP同步和均衡分组。
- third_party/verl/verl/workers/engine/veomni/transformer_impl.py:434–445：SP传入动态分批，loss分母是全局有效token数；get_data_parallel_size为world_size/ulysses_size。
- third_party/verl/verl/workers/engine_workers.py:272–301：train_mode覆盖整个多epoch minibatch，内层disable_auto_offload=True。CPU卸载不是每个microbatch反复调用，不能凭开关True断言它主导47分钟。
- transformer_impl.py:310及实际Hydra：Actor/Critic都开gradient checkpointing；enable_fsdp_offload=False，手工阶段性param/optimizer offload=True；已有forward_prefetch=True。

## 候选优先级

1. 首先只调整CRITIC_PPO_MAX_TOKEN_LEN_PER_GPU：20480→24576，验证后才考虑32768。保持SP8、batch/mini64、epochs2和全部训练预算。基于前5步token及当前源码公式：

| 上限/卡 | 每epoch microbatch预计平均 | 与当前相比 |
|---|---:|---:|
| 20480 | 20.2 | 当前 |
| 24576 | 16.8 | 数量约少17% |
| 32768 | 12.8 | 数量约少37% |
| 40960 | 10.2 | 仅列算术，不建议首试 |

这些是分批次数推算，不是实测加速比例；总token/FLOPs基本不减少。可能减少调度/FSDP通信重复并提高kernel效率，也可能收益很小或显存上升。每次只变一个开关，Actor14336暂不动。分批顺序变化可能有浮点误差，不能保证bitwise一致，但不是减少样本/epochs或改SAO目标。

2. 其次单独测试Critic关闭gradient checkpointing，保持原20480预算。利用更多显存减少反向期间前向重算；全关能否容纳尚未实测，不能与token上限加大同时首试。不要连Actor一起关。PyTorch说明checkpointing通过重新计算换内存：[官方说明](https://pytorch.org/blog/activation-checkpointing-techniques/)。

3. SP4/DP2降优先级。交接第9及后续实测记录：旧16题SP4总2149.60s vs SP8 2463.30s约快12.7%，但Actor reserved73.01GB，现场约79437/81920MiB，余量很小，且轨迹长度有差异。不能为了避开NUMA忽略既有接近显存上限证据。批量64需重测，不能直接全量切换。FSDP通信也不保证全留单NUMA。

4. workers32→64只可能缩短生成部分，不会缩短Critic47分钟，且长尾单任务不随并发消失。不优先提升；也不能直接照搬评测每卡32的配置，因为训练workers是总数，资源竞争不同。

不以提速名义改变Critic epochs2→1、缩短response/context、减少warmup、改mini-batch/学习率。这些会改变训练配方，不是纯工程优化。冻结更多层同理。

## 验证方式与实际收益边界

等到step10完整checkpoint之后，才适合安排独立同输入/同权重的短GPU对照；本次没有停训授权需求，也没有自行执行切换。比较应复用同一64条token/attention/response mask及相同Critic权重，验证有效token数、loss/梯度容差、优化器更新次数、最大显存与耗时。先warmup，再比较原20480与24576；不得通过重新生成短答案冒称配置加速。若无法取得相同训练张量，明确标注非受控比较。

当前Critic占整步约65%；假设实测Critic快20%，整步仅约少13%（72→63分钟），不是整步快20%。这只是收益换算，不是预测。GPU100%利用率表示有kernel活动，不代表矩阵计算/带宽已达到理论上限；当前MFU日志0也不能作实测计算效率依据。

verl官方同样把动态token上限定义为每GPU性能参数：[Performance tuning](https://github.com/verl-project/verl/blob/main/docs/perf/perf_tuning.rst)。本报告具体行为以本机冻结版本源码为准。

## 巡检附记

此次观察到step6 Patsy func_basic__18q7atp2两次RewardFileNotFound；verifier明确报Embedded tests changed or missing: patsy/eval.py。不能为了速度放松测试完整性保护或替模型改答案；保留未决/按既有过滤逻辑处理，当前无训练进程退出证据。后续90分钟巡检确认该批次合并和过滤结果。
