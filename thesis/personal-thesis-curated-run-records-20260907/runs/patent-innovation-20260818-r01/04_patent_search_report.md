# I4 专利检索阶段报告

生成时间：`2026-08-18T01:54:17+08:00`

## 1. 阶段结论

```yaml
stage: I4
status: SKIPPED_GATE_ZERO_SURVIVOR
input_candidate_count: 8
pass_to_i4_count: 0
PASS_TO_I4: []
patent_search_authorized: false
patent_search_executed: false
coverage: NOT_APPLICABLE_NO_SURVIVOR
```

I3 输入候选共 `8` 个，通过候选为 `0` 个。按照工作流，I4 只能检索通过 I3 的冻结候选版本；`PASS_TO_I4` 为空时，严格禁止为凑数检索被淘汰候选。因此本阶段未执行任何 CN、WO、US、EP 查询，未访问专利全文，未生成专利命中记录。

这是一项门禁阻断结论，不是专利相似性、新颖性或创造性结论。由于没有获准检索的候选，检索覆盖度记为 `NOT_APPLICABLE_NO_SURVIVOR`。

## 2. 阻断依据

I3 规定进入 I4 必须同时满足：

- 总分 `>=80/100`；
- 技术问题 `>=6/10`；
- 数据流 `>=9/15`；
- 非平凡耦合 `>=14/20`；
- 本地支持 `>=10/15`；
- 技术效果 `>=9/15`；
- 实现可行性 `>=6/10`；
- 权项表达 `>=9/15`；
- 无任何硬失败。

本轮无候选同时满足总分、全部分项最低分和无硬失败三类条件。80 分门槛与硬失败门禁均未放宽，硬失败不可由总分覆盖。

| I3 处置 | 候选 | I4 状态 |
|---|---|---|
| `HOLD_EXPERIMENT` | I2B-P02、I2B-P03 | 未进入，`NOT_EXECUTED` |
| `RETAIN_DEPENDENT_ONLY` | I2B-P01、I2B-P05、I2B-P08 | 未进入，`NOT_EXECUTED` |
| `HARD_REJECT` | I2B-P04、I2B-P06、I2B-P07 | 未进入，`NOT_EXECUTED` |

其中：

- I2B-P08 为本轮最高分 `75`，仍低于 80 分，并命中 `HF_SELF_PRIOR_SUBSTANTIAL_OVERLAP`，与自家权利要求 8 实质重叠，不得进入 I4。
- I2B-P02 为 `61` 分、I2B-P03 为 `53` 分；两者虽无当前硬失败，但总分及相关分项未达标，均为实验先行，未进入 I4。

## 3. 执行覆盖

| 项目 | 结果 |
|---|---|
| CN 查询 | `0`，`NOT_EXECUTED` |
| WO 查询 | `0`，`NOT_EXECUTED` |
| US 查询 | `0`，`NOT_EXECUTED` |
| EP 查询 | `0`，`NOT_EXECUTED` |
| 专利全文抓取 | `0` |
| 权利要求或说明书段落核验 | `0` |
| 专利族、日期、法律状态核验 | `0` |
| 来源记录 | `0` |
| coverage | `NOT_APPLICABLE_NO_SURVIVOR` |

`04_sources_patents.jsonl` 为合法空 JSONL，不包含占位记录、虚构专利或未核验线索。

## 4. 未来重新开放 I4 的必要条件

未来候选只有同时满足以下条件，才可重新开放 I4：

1. 形成新的冻结候选版本并重新提交 I3，不得直接沿用本轮淘汰版本启动检索。
2. I3 总分达到 `>=80`，且所有七项分项均达到最低分。
3. 清除全部硬失败；与自家在先实质重叠者必须形成不被既有权项直接涵盖的新必要技术关系，而非改名、扩字段或增加普通实现细节。
4. 对技术效果和实现可行性提供可审计的本地代码、数据或冻结实验支持；计划项不得表述为已实现。
5. 明确原子必要特征、特征间控制或数据依赖、删除测试及独立权项骨架，并冻结待检索版本。
6. 由新的 I3 裁决显式写入非空 `PASS_TO_I4`，I4 才能对其中候选执行 CN、WO、US、EP 检索。

候选专项要求：

- I2B-P02、I2B-P03：先完成 I3 指定的等预算对照与独立消融，补足技术效果、实现及其他低于门槛的分项后重新评分。
- I2B-P08：除补足总分、技术效果、实现和权项表达外，必须消除与自家权利要求 8 的实质重叠硬失败；仅作为既有权项从属实施细化不能据此进入独立候选查新。
- I2B-P01、I2B-P05：须消除自家在先实质重叠，并补足全部低分项。
- I2B-P04、I2B-P06、I2B-P07：须先补齐核心本地支持，并分别解决模块并列或业务规则核心等硬失败后，才可作为新版本重新立项。

## 5. 建议检索原子特征模板

以下仅为未来通过 I3 后的检索准备，状态统一为 `NOT_EXECUTED`，本轮未将任何模板提交至专利数据库。

### T1：单原子特征

```yaml
status: NOT_EXECUTED
feature_id: F<n>
input_object: "[视频/帧/镜头/视听事件/声明/证据实例及同义词]"
processing_action: "[检测/关联/更新/约束/回取/验证及同义词]"
state_or_structure: "[状态量/账本/图/张量/证书及上位、下位概念]"
output_result: "[证据对/采样集合/冲突状态/验证结果]"
query_template_cn: '("[输入对象同义词]") AND ("[处理动作同义词]") AND ("[状态或结构同义词]")'
query_template_en: '("[input synonyms]") AND ("[action synonyms]") AND ("[state or structure synonyms]")'
```

### T2：双特征共现与关系

```yaml
status: NOT_EXECUTED
feature_pair: [F<a>, F<b>]
required_relation: "[F<a>的输出作为F<b>的输入/控制条件/更新依据]"
query_template_cn: '("[F<a>同义词]") AND ("[F<b>同义词]") AND ("[控制/响应/更新/约束关系词]")'
query_template_en: '("[F<a> synonyms]") AND ("[F<b> synonyms]") AND ("[control/respond/update/constrain relation terms]")'
```

### T3：完整必要关系链

```yaml
status: NOT_EXECUTED
chain: "输入对象 -> 状态构建 -> 条件触发或互锁更新 -> 受约束输出 -> 技术结果"
query_template_cn: '("[核心输入]") AND ("[核心状态]") AND ("[触发或互锁关系]") AND ("[输出]")'
query_template_en: '("[core input]") AND ("[core state]") AND ("[trigger or interlock relation]") AND ("[output]")'
verification_target: "独立权利要求、相关从属权利要求及说明书实施段落"
```

### T4：分类号、引用链与同族扩展

```yaml
status: NOT_EXECUTED
seed: "[通过T1-T3核验的主对比文件]"
expansion:
  - "IPC/CPC相邻分类"
  - "申请人和发明人"
  - "引用与被引用专利"
  - "CN/WO/US/EP同族"
  - "最早优先权日、申请日、公开日和法律状态"
```

## 6. SHA256

### 输入与工作流

| 文件 | SHA256 |
|---|---|
| `03_gate_decision.yaml` | `dd87959ff4accfdd5f8c4b01a468e3e45c768a04113cc6457c7dc772ade6bb5e` |
| `03_candidate_gate.md` | `42cc14300a17772039758a73177967fe42ed0722386f15f96cd6d78e6be18da9` |
| `03_candidate_gate.jsonl` | `41f0361d41457c6de54b93a4108b920dc2e0f471aed61ff35d9e4e2521ab8c18` |
| `GOAL_OVERNIGHT_V2.md` | `6fc29151984ab1b2bd01ce820f4aea10e38f9a52c42de40bb6cc57eb45298092` |
| `MULTI_AGENT_INNOVATION_WORKFLOW.md` | `08c5f19ed5cbbc2be2188d1480659855fa671c69ee9d753550ea8730d9312c66` |

### 正式稿完整性复核

| 文件 | SHA256 | 结果 |
|---|---|---|
| `新申请初稿V2.1_说明书全文_20260817.md` | `1e980b4a7dcc87ead5a368d0523f65da8a94318a21d1dee1a9bde019d8d04c7b` | 与基线一致 |
| `一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md` | `224e09e6c3de3e2ca5ae5d1f3726fc266d4c06bbf4f1536340b6bb2d884bb2fa` | 与基线一致 |
| `一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.docx` | `844a947527b8921e7258966a3ebe7b36967d41ac767296773f2c7af1f8205e2f` | 与基线一致 |

本阶段未修改正式稿，未执行 Git 操作。
