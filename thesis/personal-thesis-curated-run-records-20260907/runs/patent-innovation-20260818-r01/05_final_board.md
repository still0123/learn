# I5 最终总评审板

生成时间：`2026-08-18T01:57:41+08:00`

证据刷新时间：`2026-08-18T02:12:06+08:00`

## 1. 最终裁决

```yaml
stage: I5_FINAL_BOARD
status: COMPLETE_ZERO_PASS
PASS_TO_I4: []
FINAL_PATENT_CANDIDATES: []
RETAIN_DEPENDENT_ONLY: [I2B-P01, I2B-P05, I2B-P08]
HOLD_EXPERIMENT: [I2B-P02, I2B-P03]
HARD_REJECT: [I2B-P04, I2B-P06, I2B-P07]
I4_PATENT_NOVELTY_SEARCH: NOT_APPLICABLE_NO_SURVIVOR
```

I5严格接受空`PASS_TO_I4`，不重新放行任何候选。零候选通过是有效结果：八个候选均未同时满足总分至少80、全部分项最低分且无硬失败；最高分P08仅75分，并与自家权利要求8实质重叠。

**来源：**`03_candidate_gate.md`第1节、`03_gate_decision.yaml:summary/decisions`。  
**Receipt：**`I5_RECEIPT`（本文第12节）。

## 2. 检索规模与全文核验

| 阶段 | 规模 | I5口径 |
|---|---:|---|
| 批量元数据召回 | 800 | Receipt记录的召回量 |
| 日期政策协调后合格池 | 848 | 778保留、38恢复、32新增 |
| 摘要或更强证据筛选 | 300 | 126篇全文级、174篇arXiv官方摘要级、仅标题0篇 |
| Exa语义补召回 | 1501 | 18/18查询，费用USD 1.73，仅作语义召回 |
| 最终全文队列 | 120 | 34篇预核验、86篇待核验 |
| 追加全文队列 | 24 | V4/V5各12篇 |
| V1 rank 1-40 | 40成功、0不可用 | 权威 |
| V2 rank 41-80 | 30成功、10不可用 | 权威 |
| V3旧批次 rank 81-120 | 自报32成功、8不可用 | **Receipt已拒绝，不计数** |
| V3R rank 81-120 | 32成功、8不可用 | 权威恢复；rank/title逐条一致 |
| V4 topup 1-12 | 12成功、0不可用 | 权威 |
| V5 topup 13-24 | 12成功、0不可用 | 权威 |
| 最终论文机制卡 | 77 | 严格为R1=34、R2=43；R3/R4仅保留在来源清单 |

**权威 I1 统计：144 次全文尝试、126 篇全文成功、18 篇`FULL_TEXT_UNAVAILABLE`、108 篇 2026 池合格正文、77 张R1/R2最终论文机制卡。** 旧V3有38/40个rank-title对与最终权威队列不一致，继续作为拒绝批次；权威V3R已恢复32/8且rank/title一致，不与旧批次重复计数。

**来源：**`01_paper_verification_summary.json`、`01_sources_papers.jsonl`、`01_paper_cards.md`、`01v3r_summary.md`、`01v4_summary.md`、`01v5_summary.md`。  
**Receipt：**`receipts.jsonl:L5,L7-L9,L13-L16`、`I5_EVIDENCE_REFRESH_RECEIPT`。

## 3. 零候选通过原因

1. 无候选总分达到80；P08最高75，P05为63，P02为61。
2. P01、P04、P05、P06、P07、P08共六项命中硬失败。
3. P02、P03虽无硬失败，但技术效果和实现均低于最低线。
4. P01、P05、P08与当前正式稿存在实质重叠，只能保留窄从属实验价值。
5. P04、P06、P07分别存在无核心本地支持、模块并列或业务规则核心，不得由I5恢复。
6. 论文集合未覆盖某个窄关系，不等于该关系具备专利新颖性或创造性。

**来源：**`03a_evidence_gate.md`第5-7节、`03b_paper_attack.md`第2节、`03_gate_decision.yaml`。  
**Receipt：**`I5_RECEIPT`。

## 4. 八候选结论

| 候选 | 分数 | 分类 | 最终结论 |
|---|---:|---|---|
| P01 短时文字/Logo显隐脉冲 | 59 | `RETAIN_DEPENDENT_ONLY` | 自家跨帧文字、补看和预算边界已覆盖上位概念；仅留槽位准入、三时刻、等Token替换的窄从属实验 |
| P02 互斥signed-lag声画格 | 61 | `HOLD_EXPERIMENT` | 无硬失败，但无正向激活证据；实验先行，不进I4 |
| P03 镜头曝光欠账 | 53 | `HOLD_EXPERIMENT` | 可退化为加权采样；EcoFrame+CREST拥挤度CRITICAL，等预算正面对照前冻结 |
| P04 产品实体属性账本 | 48 | `HARD_REJECT` | 无本地串绑失败集，当前为re-ID、属性抽取、槽表、问题解析并列 |
| P05 声明-模态-时间冲突张量 | 63 | `RETAIN_DEPENDENT_ONLY` | 自家声明三态、时间关系、多源冲突已公开；仅留五态、更新分流、禁抵消窄实验 |
| P06 广告叙事阶段图 | 43 | `HARD_REJECT` | 无阶段边证据，且营销阶段存在业务规则硬风险 |
| P07 报价版本事实账本 | 48 | `HARD_REJECT` | 无版本错误证据，易退化为OCR/ASR加促销规则与版本数据库 |
| P08 事实副本图删除回执 | 75 | `RETAIN_DEPENDENT_ONLY` | 与自家权利要求8实质重叠；只作权8从属实施质量或数据治理实验 |

**来源：**`02_candidate_cards.md`各候选卡、`03a_evidence_gate.md`第6节、`03b_paper_attack.md`第3-10节、`03_candidate_gate.jsonl`。  
**Receipt：**`receipts.jsonl:L17`仅作I2-B沿革；当前结论以现文件SHA、I3产物和`I5_RECEIPT`为准。

## 5. 从属实验价值

### P08：第一优先

本地已有2/20、8/20、12/20残余支持和OCR方向5/10的直接失败证据。实验目标是降低残余支持和错误负标签，不是建立新独权。名称和结论应限定为“对已发现路径及冻结复验协议的条件充分回执”。

必须在等修改像素、时长和模态预算下比较单锚点、多框、副本图覆盖；分别删除隔离复验和训练硬准入，并增加无压缩原始证据复验。

### P05：第二优先

价值在于诊断ASR主导、OCR不可辨识、同刻冲突和合法时序更新被标量聚合混淆。先通过各模态E+到E-单调性门禁，再独立删除时间维、模态维和`unidentifiable`禁入。`0.6599`不得归因于本机制。

### P01：第三优先

价值在于验证短曝光文字/Logo的首次、峰值、末次原帧是否在等Token下优于逐帧Top-K和仅峰值。应先标注至少100个短曝光事件，并报告压缩前后关键文字保留率。

**来源：**`03_candidate_gate.md`中P01/P05/P08记录、`03_gate_decision.yaml:candidate_decisions`。  
**Receipt：**`I5_RECEIPT`。

## 6. P02/P03重开条件

### P02

1. 建立旁白领先、视觉领先、近同步、无关四类双审配对集。
2. 证明声画联合路径真实激活，不能复用旧AV退化为CLIP的结果。
3. 完成无互斥、无符号、无问题槽位三项独立删除测试。
4. 固定事件、ASR、视图、Token和回答器，对照零时延、固定滑窗、Scene-RAG式对齐。
5. 形成新冻结版本，重新达到I3总分及全部分项门槛，获得新的非空`PASS_TO_I4`。

### P03

1. 冻结欠账状态转移、清偿条件和预算冲突规则。
2. 建立快切镜头与决定性事件双标注。
3. 执行Uniform、MMR、EcoFrame、CREST、Exposure五臂等解码帧、等视图、等Token实验。
4. 分别删除最低覆盖、等量回收、三时刻突发和实体连续性。
5. 任一核心关系无独立效应即停止独权方向；只有新版本重新通过I3方可进入I4。

**来源：**`03_candidate_gate.md`中P02/P03记录、`04_patent_search_report.md`第4节。  
**Receipt：**`I5_RECEIPT`。

## 7. I4专利查新口径

I4状态是：

```text
NOT_APPLICABLE_NO_SURVIVOR
```

原因是I3没有幸存候选，I4未获授权。CN/WO/US/EP查询均为0，专利全文抓取0，权利要求/段落核验0，专利来源记录0；`04_sources_patents.jsonl`是合法空文件。

这**不表示**“未检到类似专利”“没有类似专利”“具备新颖性/创造性”或“可以申请”。只有候选新版本重新通过I3并产生非空`PASS_TO_I4`后，才可启动正式专利查新。

**来源：**`03_gate_decision.yaml:i4`、`04_patent_search_report.md`第1-4节、`04_patent_search_status.yaml:execution`。  
**Receipt：**`I5_RECEIPT`。

## 8. 当前正式申请稿不应改动

1. 不把P01/P05/P08升格为当前独权，不把P02/P03实验计划写入正式稿。
2. 不改变现有F1-F9闭环、同一验证器同口径评分、绝对阈值+相对裕量、条件失败回退、权利要求8最小破坏训练边界。
3. `0.5409→0.6599`只归因于真实正反声明分类训练。
4. Full-7844 `+7.00/+10.12pp`只支撑支持度触发、证据补看和独立候选生成的联合效果。
5. E-VAds `28胜0负`只支撑绝对阈值与相对裕量双条件门控。
6. 不写入未实现机制、计划实验、虚构效果或保证授权表述。
7. 不把研究产物中的V3错位引用带入正式稿。

结束复核的三个正式文件SHA256与`00_brief.md`基线一致，未修改正式稿。

**来源：**`00_brief.md`“当前独权原子特征/证据边界”、`03_gate_decision.yaml:formal_application_integrity`、`04_patent_search_report.md`第6节。  
**Receipt：**`receipts.jsonl:L1`、`I5_RECEIPT`。

## 9. 下一轮优先级

**独立候选重开轨：**

1. P02：先证明互斥signed-lag的独立效应和真实联合激活。
2. P03：仅在严格等预算下正面超过EcoFrame与CREST后重开。

**从属实施实验轨：**

1. P08：降低反事实样本残余支持和错误负标签。
2. P05：验证时间更新分流和禁抵消是否改善可审计错误类型。
3. P01：验证短时文字脉冲三时刻等Token回取。

P04/P06/P07本轮不分配实验资源，不得从`HARD_REJECT`直接恢复。

**来源：**`03_candidate_gate.md`第4节、`03_gate_decision.yaml:candidate_decisions`。  
**Receipt：**`I5_RECEIPT`。

## 10. 公开日期风险

1. 论文池资格与专利现有技术日期必须分开。2025预印本在2026正式发表可进入研究池，但最早公开日仍是2025。
2. V2已核验到“2026正式发表、2023-12-08首次公开”的论文族，不能用venue年份覆盖更早公开。
3. 2026年1月至8月近邻论文均需按具体申请日、公开可得性、司法辖区和宽限期逐件判断。
4. 旧V3因队列错位不可承担日期或机制结论；权威V3R已恢复32篇全文并记录8篇不可用，后续只按稳定`paper_record_id`和标题引用。
5. 新候选提交前公开代码、论文、答辩材料或Git内容可能形成自公开风险，须先确认申请时序。
6. 本轮没有专利检索，不能据论文检索推断专利领域无在先公开。

**来源：**`00_brief.md`论文范围、`01v2_summary.md`关键核验事项、`01v3r_summary.md`日期纠正、`02_candidate_reference_reconciliation.md`、`04_patent_search_report.md`第1节。  
**Receipt：**`receipts.jsonl:L7,L15,L16`、`I5_EVIDENCE_REFRESH_RECEIPT`、`I5_RECEIPT`。

## 11. 代理人复核点

1. P01/P05/P08是否只能落入现有从属权项或实施方式，尤其P08与权利要求8的实质重叠。
2. 未来新增关系是否有原始说明书支持，避免超范围修改和支持性风险。
3. P02/P03重新通过I3后，按冻结必要特征执行CN/WO/US/EP正式查新、同族、日期和法律状态核验。
4. 逐件判断2025预印本、2026正式论文和申请日前后公开的现有技术资格。
5. 当前申请与潜在新申请的单一性、重复授权、分案或继续申请路径。
6. P06/P07的业务规则风险；P02/P03是否只是常规信号处理或采样参数变化。
7. P08只能使用条件充分表述，不得使用绝对删除、保证安全或保证授权表述。
8. 发明人、权属、公开代码/论文/Git时间线及保密义务。

**来源：**`03a_evidence_gate.md`第4节、`03_candidate_gate.md`第4节、`04_patent_search_report.md`第4节、`patent-innovation-analysis/SKILL.md`门禁规则。  
**Receipt：**`receipts.jsonl:L1`、`I5_RECEIPT`。

## 12. Receipt与审计异常

```json
{
  "receipt_id": "I5_RECEIPT",
  "stage": "I5_FINAL_BOARD",
  "decision": "COMPLETE_ZERO_PASS",
  "pass_to_i4_accepted_as_empty": true,
  "candidates_reopened": [],
  "formal_application_modified": false,
  "git_operation": false,
  "patent_search_executed": false,
  "outputs": ["05_final_board.md", "05_final_board.json"]
}
```

```json
{
  "receipt_id": "I5_EVIDENCE_REFRESH_RECEIPT",
  "stage": "I5_EVIDENCE_REFRESH",
  "decision": "COMPLETE_STATS_AND_REFERENCE_REFRESH_ONLY",
  "candidate_content_modified": false,
  "candidate_scores_modified": false,
  "candidates_reopened": [],
  "pass_to_i4_remains_empty": true,
  "i4_status_remains": "NOT_APPLICABLE_NO_SURVIVOR",
  "formal_application_modified": false,
  "git_operation": false,
  "outputs_updated": ["05_final_board.md", "05_final_board.json"],
  "outputs_created": ["02_candidate_reference_reconciliation.md"]
}
```

审计异常：

- `I1-V1` Receipt中的摘要哈希与当前`01v1_summary.md`不一致，但V1 JSONL哈希一致；V1计数由当前摘要、40行JSONL及匹配JSONL哈希确认。
- `I1-V3-OLD` Receipt明确为`REJECTED`，旧V3不得恢复或重复计数；权威V3R现为32篇成功、8篇不可用且rank/title一致。
- I3发现P01、P04、P05、P08的旧V3 rank ID错位；后续以`01_sources_papers.jsonl`的稳定`paper_record_id`和标题为准，映射见`02_candidate_reference_reconciliation.md`，不回写候选内容与评分。
- `I2-B` Receipt哈希与当前候选卡哈希不一致，说明后续增量重校准覆盖了初版；该Receipt仅作沿革。
- `receipts.jsonl`没有I3/I4独立行；I5引用`03_gate_decision.yaml`、`04_patent_search_status.yaml`和本节Receipt，不虚构缺失记录。

**来源：**`receipts.jsonl:L14-L17`、`01v3r_summary.md`、`02_candidate_reference_reconciliation.md`、`03a_evidence_gate.md`第4.1节、`03_gate_decision.yaml`、`04_patent_search_status.yaml`。  
**Receipt：**`I5_EVIDENCE_REFRESH_RECEIPT`、`I5_RECEIPT`。

## 13. SHA256

| 文件 | SHA256 |
|---|---|
| `05_final_board.json` | `f4cd6884d9c9d12d63d5e62b66d8f80638e1fead5c9991ab44b2fc02f1e77d11` |
| `00_brief.md` | `48113d5c3e9680ffeadc489c6174828c9c8aa1c5f61f75532883001c9ec3705d` |
| `01_paper_verification_summary.json` | `7a7020c78dc0c753bd1298e99eae205ca9919d7df7d6ac3be723e4d501cd8a28` |
| `01_sources_papers.jsonl` | `58934393e8f64861203e401fe868fb366a122d351a18cf9100333c1539de3950` |
| `01_paper_cards.md` | `7ecaafc0c30ebe5288d66be0b41507cd8dd896c01a1acf29f880903b065fa90a` |
| `01g_fulltext_verification_queue.jsonl` | `309fd5ce5c8af3075132dabf25f092f769d174866f86b14d90f0b3faadbbc032` |
| `01v1_verified_001_040.jsonl` | `7d0cf750de856a7aefb08fb1a95f13ac0937d0b2c4e0810498092819c50ec986` |
| `01v2_verified_041_080.jsonl` | `622766e406b8935a179019236abf248467b591af40d98ae8766497ab5764f597` |
| `01v3_verified_081_120.jsonl`（拒绝批次） | `7dc11191de7f9da4c8a0744a3226c317aff5cc6ded24d84ccec7b532eae8d76f` |
| `01v3r_verified_081_120.jsonl` | `bbe3630d0168fdae1d67cc73c71eccf8d15b23f485d86664c3cae61bb22552b2` |
| `01v4_topup_001_012.jsonl` | `7a1a3e73cebf3475922e1c44d4660572f1136f0d11717a73a5e402d3794b7876` |
| `01v5_topup_013_024.jsonl` | `6efb7eab8cccb81c7b6d24542c69ce893730a4f99d15b24fed1b37a984803af2` |
| `02_candidate_reference_reconciliation.md` | `90670175a0b55e4bb75bccb38861e3de155a88f15a64b66d99f374085cdb1303` |
| `02_candidate_cards.jsonl` | `da5c0904f0783368f0b4facb88488e5b9605856b0403039f9f1ffbc447686cdc` |
| `03_candidate_gate.jsonl` | `41f0361d41457c6de54b93a4108b920dc2e0f471aed61ff35d9e4e2521ab8c18` |
| `03_gate_decision.yaml` | `dd87959ff4accfdd5f8c4b01a468e3e45c768a04113cc6457c7dc772ade6bb5e` |
| `04_patent_search_report.md` | `ad023622b7ab0b8b2baf9f82ab24830c811e72150df7ab973d9a5d73954ae964` |
| `04_patent_search_status.yaml` | `ce1390e1b9844193fb4051b734df26c514affb4cdfc5a9bb1884356fa7d5be77` |
| `receipts.jsonl` | `1af1679f3001fed065ac1a82e5933a8783fa0b2ef3cbe0df877cdc91ac8923a4` |

`05_final_board.md`自身SHA256采用外部摘要交付，避免文件内自引用。
