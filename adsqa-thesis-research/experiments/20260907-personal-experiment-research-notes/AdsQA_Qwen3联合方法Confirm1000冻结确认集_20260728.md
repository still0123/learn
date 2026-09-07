# AdsQA Qwen3联合方法Confirm-1000冻结确认集

## 1. 用途与边界

本数据集用于最终确认“低支持识别→问题条件化视听证据补看→证据约束重写→充分性门控回退”能否稳定提高AdsQA问答正确率。

该集合是**当前联合方法专属的冻结确认集**：

- 排除当前方法用于训练、校准、Development、OOF开发和Confirm-D确认的全部视频；
- 选择过程中不读取答案语义、`meta_info`、模型预测、支持度或裁判分数；
- 但它不是相对于项目全部历史实验的全局未接触集合。此前其他无关候选已经覆盖AdsQA的大部分视频，严格排除所有历史实验后无法构造1000视频。

因此后续论文可称其为“第二个方法级大规模冻结确认集”，不得称为“整个研究流程的全局盲测集”。

## 2. 冻结路径

远端根目录：

```text
/data1/rmx/projectb/AdsQA-main/data/qwen3_joint_confirm1000_v1/
```

主要文件：

```text
questions_answer_free.json
selection_records_answer_free.jsonl
shards/shard0of5.json
...
shards/shard4of5.json
private_references/groundtruth.json
audit.json
manifest.json
FROZEN
```

`private_references/`权限为`700`，参考答案文件权限为`600`。推理、证据选择和协议审计只能读取answer-free文件；只有所有预测和选择结果冻结后，裁判阶段才允许读取私有参考答案。

## 3. 数据来源与清洗

源文件：

```text
data/testset_question.json
data/testset_groundtruth.json
```

源数据共有7,859行、7,846个唯一问题ID。检测到13行完全相同的重复记录；仅在问题、视频、类型及对应私有参考均完全一致时确定性合并，任何冲突重复都会使构建器失败。

构建过程中还排除了1,532个私有参考答案为空的问题。该规则只检查参考是否非空，不利用答案语义或文字内容进行抽样。

## 4. 方法专属排除集

构建器冻结排除以下数据源中的全部视频：

| 来源 | 行数 | 唯一视频 |
|---|---:|---:|
| AdsQA `train.json` | 500 | 100 |
| RealClaim985训练输入 | 985 | 139 |
| Calibration240复核清单 | 240 | 35 |
| Development244复核清单 | 244 | 35 |
| Confirm-D300 | 300 | 300 |

排除集共609个唯一视频，其中509个属于AdsQA测试问题源。最终1000视频与上述排除集的交集为0。

当前方法的OOF开发、组件消融和静态强基线均由`train.json`或Confirm-D派生，因而已经被上述视频级排除覆盖。

## 5. 冻结抽样规则

固定随机种子：

```text
20260728
```

候选必须同时满足：

- 视频未出现在方法专属排除集中；
- 视频文件存在；
- 64帧视频索引存在；
- CLIP候选缓存存在；
- OCR候选缓存存在；
- 私有参考答案非空。

符合条件的视频共1,029个。构建器建立“题型—视频”容量图，使用确定性最大流选择：

```text
Type_1: 200
Type_2: 200
Type_3: 200
Type_4: 200
Type_5: 200
```

每个视频最多进入一次，每个题型恰好200题。若同一视频同一题型存在多个合法问题，使用固定哈希选择一个问题。最终再按固定哈希分成5个分片，每片200题且每个题型40题。

## 6. 冻结审计结果

| 项目 | 结果 |
|---|---:|
| 问题数 | 1,000 |
| 唯一问题ID | 1,000 |
| 唯一视频 | 1,000 |
| 每类问题 | 200 |
| 每个分片 | 200 |
| 每分片每类问题 | 40 |
| 排除视频交集 | 0 |
| Answer-free禁用字段 | 0 |
| 私有参考覆盖 | 1,000/1,000 |
| 非空参考答案 | 1,000/1,000 |
| 视频文件覆盖 | 1,000/1,000 |
| CLIP缓存覆盖 | 1,000/1,000 |
| OCR缓存覆盖 | 1,000/1,000 |
| 分段ASR联合覆盖 | 1,000/1,000 |
| ASR状态 | `success=988`、`no_speech=11`、`no_audio=1` |
| ASR失败 | 0 |

缺失的70个视频已在独立补充目录完成分段ASR，并与原930个记录联合审计。联合缓存保留`success`、`no_audio`、`no_speech`和`transcription_failed`显式状态，不用空字符串替代无音频或无语音。联合记录aggregate SHA256为`084446e1f685647d402115d3284ab368c95b121387ae7880d41b07024e9ebbd6`，联合审计文件SHA256为`927e3ee650c4f84c1cadc0d0d2a9af87d5283b533f296903db51144840841a53`。

最终四臂协议已经在任何QA推理前冻结，协议SHA256为`0ed03079b1f6816c3ab33654ff930e8a86205166badf7f47781c76314a823cb8`。详细方法、主次比较和禁止事项见[最终四臂预注册](AdsQA_Qwen3联合方法Confirm1000最终四臂预注册_20260728.md)。

## 7. 哈希

```text
manifest.json:
ac3cd2978c5003ffdb1f10dc83db4ef2db4c9d7be3f6c766349419e7bd8e951a

audit.json:
75693e74d7ec83c6cedf3356bc746414e8ee218e65558e9bb2490b115a7f5e9f

questions_answer_free.json:
87344f000942eba1c9c03d0b43ef70a82e30c809a52ac4ebfed26c8377e5050a

private_references/groundtruth.json:
e2efccb11bc0f6ebeb01572596f8b2177b640b7c451c94eb54d2b564df564e88
```

`FROZEN`保存`manifest.json`的SHA256。后续脚本必须先验证该哈希，任何题目增删、重排或替换都应使实验立即停止。

## 8. 后续实验限制

该集合只允许一次冻结评测，不得用于：

- 修改RealClaim985阈值；
- 修改10%触发率；
- 调整margin、Prompt或答案解析；
- 选择锚点数量、OCR/ASR权重或裁剪尺度；
- 根据结果在完整方法与NoLocalCrop之间事后择优；
- 扫描MMR权重、Top-K或视觉Token预算。

建议最终主比较预先固定为：

```text
Uniform8
MMR8
同触发、同Token的ExtraGlobal控制
完整选择性视听证据补看方法
```

主要检验为完整方法对Uniform8；对MMR8和同计算量控制的比较作为预注册关键次要检验。
