# P8 代码实现映射

## 已运行的实验主机制

- MMR选择：问题相关性减帧间最大冗余，8个互不重复帧。
- 支持度验证：Qwen3+LoRA接收精确证据帧与候选答案，以supported/contradicted logits计算概率并执行视觉Token上限检查。
- 低支持触发：使用冻结阈值，仅对触发样本准备OCR、ASR和两个证据锚点。
- 保守替换：仅在A2支持度达到A0支持度加裕量且A2文本不同的情况下切换，否则保留A0。

## 仅脚手架或不宜主张

- `code_refactor/evidence/evidence_package.py`仅构建text-level bridge，`traceable_to_raw=False`。
- `code_refactor/reflection/claim_checker.py`仅为规则化检查计划，没有支持/冲突模型、触发或回退。
- RAG检索器是词法MVP，未构成最终主实验。
- 统一证据ID全链、动作路由独立优势、裁剪独立优势均未充分实现或验证。

