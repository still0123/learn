# P3 旧案对新申请的约束图谱

## R-01 旧案已暴露的主战场

- 已被审查员系统攻击的方向：
  1. 通用视频问答主框架；
  2. 过采样与关键帧优选；
  3. 全局/局部双流视觉表征；
  4. 广告知识库 RAG；
  5. 结构化推理/链式思维；
  6. 自我验证/链式校验；
  7. 热力图/局部定位。
- 对新申请的约束：这些方向即便还能继续细化，也不适合再作为“全新专利”的主标题与独权核心。

## R-02 审查员最喜欢的拆解方式

- 旧案中，审查员把方案压缩为“已知模块的组合并得到可预期效果”。
- 对新申请的约束：新方案不能继续以“我们也有 OCR / RAG / verification / global-local”这种模块列表方式写；必须围绕一个**新的中间机制或控制机制**来组织。

## R-03 旧案中没有被充分覆盖的新萌芽

根据当前代码与文档，以下机制在旧案中没有被充分主张，但现在已经在系统里出现雏形：

1. knowledge leakage / contamination awareness；
2. supporting_evidence_ids 级别的检索结果 provenance；
3. lexical / embedding / hybrid retrieval orchestration；
4. claim_type → required_evidence 路由；
5. traceable_to_raw 的 raw asset 贯通；
6. evidence-permitted knowledge / risk-aware prompt context。

## R-04 新申请最值得避开的坑

- 不要再以“广告视频问答方法”这个过宽标题直接开局。
- 不要再用“链式反思/链式校验”做主标题。
- 不要把“RAG 升级成 hybrid”本身当创造性。
- 不要只说“更可解释/更可靠”，而不说**通过什么新的控制机制实现**。

## R-05 新申请最有潜力的新主线

初步看，最有希望的新主线不是视觉前端，而是：

```text
证据可追溯性 + 知识风险感知 + 声明类型路由 + 检索编排控制
```

这条主线相比旧案，更靠近：

- 推理治理；
- provenance control；
- multimodal verification routing；
- risk-aware RAG orchestration。

这也是当前代码里最像“新 disclosure”的部分。