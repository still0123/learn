# P8 代码实现难度评审

## 评审结论

现有 `code_refactor` 已经具备“证据包 -> 知识检索 -> 结构化提示词 -> 答案声明检查计划”的轻量管线，可作为新专利方案的工程起点。但目前实现仍是文本级、规则级、单向流水线：

- 已有基础：`EvidencePackage`、`RetrievedKnowledge`、混合检索、结构化 prompt、claim check plan、轻量 pipeline 和单元测试。
- 未实现核心：多模态证据一致性图谱、问题驱动证据路由、跨模态冲突仲裁、可信证据包约束生成。
- MVP 可行性：中等。若不接入真实 OCR/Logo/视觉检测模型，可在现有 AdsQA 字段上 3-5 天做出可运行原型；若要求真实视频帧级多模态抽取和端到端实验，约 2-4 周。
- 专利支撑价值：较高。现有代码能证明“证据包化”和“证据驱动检索”已经落地，新申请应把创造性聚焦在图谱化一致性计算、动态路由、冲突仲裁和生成约束，而不是泛泛的 RAG 或 prompt 模板。

## 现有代码基础

| 模块 | 文件 | 当前能力 | 可复用程度 |
|---|---|---|---|
| 证据包 | `code_refactor/evidence/evidence_package.py` | 定义 `EvidenceField`、`EvidencePackage`，支持 ASR、OCR、Logo、meta、visual_tags、ad_evidence_types、scores、traceable 标记 | 高 |
| 证据类型推断 | `code_refactor/evidence/evidence_package.py` | `infer_ad_evidence_types()` 用规则从 question/answer/meta/asr 推断广告证据类型 | 中 |
| 检索 | `code_refactor/rag/retriever.py` | 词法相似度、keyword overlap、evidence match、`RetrievedKnowledge` | 高 |
| Embedding/Hybrid 检索 | `code_refactor/rag/embedding_retriever.py` | hashing fallback、sentence-transformers/FlagEmbedding/transformers backend、hybrid retrieve | 高 |
| Prompt 生成 | `code_refactor/reasoning/prompt_builder.py` | 将证据包和知识项组成结构化 prompt，要求引用 evidence_id/knowledge_id | 中 |
| Claim 检查 | `code_refactor/reflection/claim_checker.py` | 把答案切成 claim，并按 OCR/Logo、ASR、marketing、visual 分类生成检查计划 | 中 |
| 轻量 pipeline | `code_refactor/scripts/run_lightweight_pipeline.py` | 单样本运行：加载数据、构造证据包、检索、prompt、claim plan、输出 JSON | 高 |
| 测试 | `code_refactor/tests/test_lightweight_pipeline.py`、`test_embedding_rag.py` | 覆盖 loader、KB、检索、prompt、claim plan、embedding/hybrid retrieve | 中 |

## 新专利方案到代码的落点

### 1. 多模态证据一致性图谱

目标：把当前扁平 `EvidencePackage` 扩展为“证据节点 + 跨模态关系边 + 一致性/冲突分数”的图结构。

建议新增文件：

- `code_refactor/evidence/evidence_graph.py`
- `code_refactor/evidence/consistency.py`
- `code_refactor/tests/test_evidence_graph.py`

建议类/函数：

```python
@dataclass
class EvidenceNode:
    node_id: str
    evidence_id: str
    modality: str  # asr, ocr, logo, visual, meta, knowledge
    text: str
    time_window: list[float] | None
    source_ids: list[str]
    confidence: float | None

@dataclass
class EvidenceEdge:
    src: str
    dst: str
    relation: str  # support, duplicate, temporal_overlap, contradiction, weak_prior
    score: float
    reason: str

@dataclass
class EvidenceConsistencyGraph:
    graph_id: str
    sample_id: str
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge]
    global_consistency_score: float
    conflicts: list[dict]

def build_evidence_graph(packages: list[EvidencePackage]) -> EvidenceConsistencyGraph:
    ...

def score_cross_modal_consistency(nodes: list[EvidenceNode]) -> list[EvidenceEdge]:
    ...
```

实现方式：

- 从 `EvidencePackage.asr`、`ocr_text`、`logo_text`、`meta_info`、`visual_tags`、`ad_evidence_types` 抽节点。
- 用词面重叠、时间窗重叠、source_type、confidence 计算 support/duplicate。
- 用数值/品牌/价格关键词不一致、否定词、互斥营销类型识别 contradiction。
- 将 `global_consistency_score` 写回 `EvidencePackage.scores["graph_consistency"]` 或作为独立对象传给下游。

MVP 难度：中。

风险：

- 现有数据中真实 OCR/Logo/帧级视觉字段多数为空，MVP 只能基于 ASR/meta/question 和弱规则模拟多模态。
- 若专利文件声称“多模态”但实验只用文本字段，说明书和实验需要明确可接入 OCR/Logo/视觉检测器，避免实施例支撑不足。

### 2. 问题驱动证据路由

目标：根据问题类型和 claim 检查需求，动态选择证据模态、检索策略和 prompt 结构。

建议新增文件：

- `code_refactor/evidence/evidence_router.py`
- `code_refactor/tests/test_evidence_router.py`

建议类/函数：

```python
@dataclass
class RoutingDecision:
    route_id: str
    question_type: list[str]
    required_modalities: list[str]
    selected_evidence_ids: list[str]
    retrieval_mode: str  # lexical, embedding, hybrid, graph_aware
    generation_constraints: list[str]
    reasons: list[str]

class QuestionDrivenEvidenceRouter:
    def route(
        self,
        question: str,
        packages: list[EvidencePackage],
        graph: EvidenceConsistencyGraph | None = None,
    ) -> RoutingDecision:
        ...
```

实现方式：

- 复用 `reflection.claim_checker.infer_claim_type()` 的规则，把问题映射到 `ocr/logo/asr/visual/marketing_knowledge`。
- 结合 `EvidencePackage.task_types` 和 `ad_evidence_types` 做 route。
- 对 `TE`/文字数字价格类问题提高 OCR/Logo 权重；对声音/旁白类提高 ASR 权重；对策略/受众/情绪类走 marketing knowledge + evidence graph。
- 将路由结果传给 `retrieve()` 或新增 `graph_aware_retrieve()`，只允许检索和问题相关的证据包字段。

MVP 难度：低到中。

风险：

- 现有 `build_query()` 会拼接所有字段，尚未支持按模态裁剪；需要新增受控 query builder。
- 路由规则若过粗，容易被审查员认为只是常规规则匹配。建议加入“问题类型-证据一致性-冲突状态”联合决策，而不只是关键词判断。

### 3. 冲突仲裁

目标：当 ASR、OCR、Logo、meta、知识项之间存在不一致时，输出可追溯的仲裁结果，决定哪些证据可用于回答，哪些应降权或禁止生成。

建议新增文件：

- `code_refactor/reflection/conflict_arbiter.py`
- `code_refactor/tests/test_conflict_arbiter.py`

建议类/函数：

```python
@dataclass
class ConflictCase:
    conflict_id: str
    node_ids: list[str]
    conflict_type: str  # entity, number, time, modality, knowledge_leakage
    severity: str  # low, medium, high
    description: str

@dataclass
class ArbitrationResult:
    accepted_node_ids: list[str]
    rejected_node_ids: list[str]
    downgraded_node_ids: list[str]
    constraints: list[str]
    rationale: list[str]

class EvidenceConflictArbiter:
    def arbitrate(
        self,
        graph: EvidenceConsistencyGraph,
        route: RoutingDecision,
    ) -> ArbitrationResult:
        ...
```

实现方式：

- 输入 evidence graph 中的 contradiction/weak_prior/potential_leakage 边。
- 根据 source_type、confidence、traceable_to_raw、prior_flag、问题所需模态决定优先级。
- 对 `potential_leakage=True` 的知识项只允许作为背景，不允许作为事实来源。
- 输出 constraints，例如“不得声称价格数字，除非 OCR 或 ASR 中存在一致证据”。

MVP 难度：中。

风险：

- 当前 `EvidencePackage.traceable_to_raw=False`，真实仲裁缺少强证据来源。需要在说明书中把“可信证据包”定义为可接入原始帧、bbox、ASR 时间戳，而代码 MVP 先保留接口。
- 冲突检测不能只写自然语言 prompt，否则技术性不足；应明确冲突类型、分数、节点选择规则。

### 4. 可信证据包约束生成

目标：将路由和仲裁结果转化为生成阶段的硬约束或软约束，避免模型使用无来源知识、冲突证据或弱先验直接回答。

建议修改/新增文件：

- 修改 `code_refactor/reasoning/prompt_builder.py`
- 新增 `code_refactor/reasoning/constrained_prompt_builder.py`
- 新增 `code_refactor/tests/test_constrained_prompt_builder.py`

建议类/函数：

```python
@dataclass
class GenerationConstraint:
    constraint_id: str
    constraint_type: str  # must_cite, forbidden_claim, modality_required, uncertainty_required
    text: str
    evidence_ids: list[str]

def build_generation_constraints(
    route: RoutingDecision,
    arbitration: ArbitrationResult,
) -> list[GenerationConstraint]:
    ...

def build_constrained_prompt(
    question: str,
    packages: list[EvidencePackage],
    knowledge: list[RetrievedKnowledge],
    constraints: list[GenerationConstraint],
) -> str:
    ...
```

实现方式：

- 在 prompt 中加入 `Allowed Evidence`、`Forbidden Claims`、`Required Citations`、`Uncertainty Policy`。
- 要求答案每个事实性 claim 引用 `evidence_id`，营销知识只允许引用 `knowledge_id + supporting_evidence_ids`。
- 对高冲突结果要求模型输出“不确定/无法确认”，而不是强行生成。
- 与 `build_check_plan()` 联动：生成后检查答案 claim 是否满足对应 evidence modality。

MVP 难度：低到中。

风险：

- Prompt 约束不是严格解码约束。若要提高专利技术性，可在 MVP 中加入后处理 validator：不满足约束的答案标记为 invalid 或触发重生成。

## 建议的端到端 MVP 结构

建议新增脚本：

- `code_refactor/scripts/run_graph_routed_pipeline.py`

建议流程：

1. `AdsQALoader.load_samples()` 读取样本。
2. `build_text_evidence_package()` 构造基础证据包。
3. `build_evidence_graph()` 抽取证据节点并计算一致性/冲突边。
4. `QuestionDrivenEvidenceRouter.route()` 根据问题选择模态和检索模式。
5. `hybrid_retrieve()` 或 `graph_aware_retrieve()` 检索营销知识。
6. `EvidenceConflictArbiter.arbitrate()` 过滤或降权冲突证据。
7. `build_constrained_prompt()` 生成可信证据约束 prompt。
8. `build_check_plan()` 对输出答案做 claim-level 检查。
9. 输出 JSON，包含 graph、route、retrieved knowledge、arbitration、constraints、prompt、claim plan。

建议输出 schema：

```json
{
  "sample_id": "...",
  "evidence_package": {},
  "evidence_graph": {"nodes": [], "edges": [], "global_consistency_score": 0.0},
  "routing_decision": {},
  "retrieved_knowledge": [],
  "arbitration_result": {},
  "generation_constraints": [],
  "prompt": "...",
  "claim_check_plan": []
}
```

## 测试计划

### 单元测试

| 测试文件 | 覆盖点 | 关键断言 |
|---|---|---|
| `test_evidence_graph.py` | 证据节点、support/contradiction 边、一致性分数 | ASR/OCR 包含相同品牌时生成 support；价格冲突时生成 contradiction |
| `test_evidence_router.py` | 问题到模态路由 | 价格/数字问题必须包含 OCR；voice/audio 问题必须包含 ASR；营销策略问题包含 marketing_knowledge |
| `test_conflict_arbiter.py` | 冲突仲裁和降权 | 高置信 OCR 与弱先验冲突时拒绝弱先验；potential_leakage 只作为背景 |
| `test_constrained_prompt_builder.py` | 约束 prompt | prompt 包含 Allowed Evidence、Forbidden Claims、Required Citations；冲突 evidence 不出现在允许列表 |
| `test_graph_routed_pipeline.py` | 端到端 MVP | 输出 JSON 包含 graph/route/arbitration/constraints，且 prompt 引用 evidence_id |

### 回归测试

- 保留现有 `test_lightweight_pipeline.py` 和 `test_embedding_rag.py`，确保新增图谱路由不破坏原 pipeline。
- 对 `HashingEmbeddingBackend` 继续作为无依赖测试后端，真实模型测试作为可选集成测试。

### 实验验证

- 指标 1：可追溯率，答案中事实性 claim 带 evidence_id 的比例。
- 指标 2：冲突抑制率，构造冲突样本后错误强答比例下降。
- 指标 3：路由有效性，不同问题类型命中的必需模态比例。
- 指标 4：RAG 泄漏控制，`potential_leakage=True` 知识项被直接作为事实依据的比例。

## 哪些已经有基础

- `EvidencePackage` 已预留 ASR/OCR/Logo/meta/visual/ad evidence types/scores/traceability 字段，可直接扩展为图谱节点来源。
- `retrieve()` 和 `hybrid_retrieve()` 已能把 evidence text 与 marketing KB 联合打分，可扩展为 graph-aware retrieval。
- `RetrievedKnowledge` 已有 `supporting_evidence_ids`、`risk_notes`、`potential_leakage`，适合接入仲裁和约束生成。
- `build_structured_prompt()` 已要求引用 evidence_id 和 knowledge_id，可改造成约束 prompt。
- `claim_checker` 已能按 claim 类型推断所需证据，是问题驱动路由和生成后检查的直接基础。
- 测试框架已存在，新增测试成本不高。

## 哪些未实现

- 没有 `EvidenceNode`/`EvidenceEdge`/`EvidenceConsistencyGraph`，证据仍是扁平字段。
- 没有跨模态一致性分数，也没有 contradiction/support 边。
- 没有问题驱动路由器，当前检索 query 会拼接所有字段。
- 没有图谱感知检索，知识项排序未利用冲突状态或一致性分数。
- 没有冲突仲裁模块，`potential_leakage` 只是字段，没有被强制约束。
- 没有可信证据包约束生成器，prompt 只做自然语言要求，没有结构化约束对象。
- 没有真实多模态抽取器，OCR/Logo/视觉检测/帧级 bbox/时间戳仍需外部模型或数据源。
- 没有生成后 validator，只生成 claim check plan，没有验证答案是否违反 evidence constraints。

## MVP 工程排期

| 阶段 | 工作 | 预计时间 | 风险 |
|---|---|---:|---|
| MVP-1 | evidence graph 数据结构、节点抽取、简单 support/contradiction 边 | 0.5-1 天 | 规则粗糙 |
| MVP-2 | question-driven router 和受控 query builder | 0.5 天 | 问题类型覆盖不足 |
| MVP-3 | conflict arbiter 和 constraints 对象 | 1 天 | traceable_to_raw 弱 |
| MVP-4 | constrained prompt builder 和 graph routed pipeline | 0.5-1 天 | 仍依赖 prompt 执行 |
| MVP-5 | 单元测试、样例输出、README 实验说明 | 1 天 | 测试样例需手工构造冲突 |

最小可交付周期：3-5 天。

较完整工程周期：2-4 周，前提是接入 OCR、Logo、视觉标签、视频帧时间窗或已有多模态标注。

## 对新申请的代码实施例建议

新申请的实施例不应只写“把证据放进 prompt”。建议把技术方案落为以下可执行对象：

1. 证据一致性图谱构建模块：输入多模态证据包，输出节点、边和一致性分数。
2. 问题驱动证据路由模块：输入问题、任务类型和图谱，输出必需模态、选中证据和检索策略。
3. 冲突仲裁模块：输入图谱冲突和路由结果，输出可用证据、禁用证据和约束。
4. 可信证据包约束生成模块：输入仲裁结果，输出带引用要求、禁止声明、不确定性策略的生成约束。
5. 生成后检查模块：将答案 claim 映射回 required evidence，违反约束则触发重生成或拒答。

这套结构与现有代码衔接自然，同时比原先“营销知识库 + RAG + prompt”更容易形成可被权利要求保护的技术特征组合。
