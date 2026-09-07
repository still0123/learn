# Round33 材料清单

- 主稿：`deliverables/patent/基于视频证据双差分许可的视频问答答案更新控制专利申请初稿_V4.6_20260824.md`
- 查新基线：`runs/patent-analysis-20260824-round32/`
- 代码支撑：`code_refactor/evidence/evidence_package.py`、`code_refactor/reflection/claim_checker.py`、`code_refactor/scripts/run_rag_qwen3_inference.py`
- 补证预注册：`docs/创新点一多模态证据覆盖选择实验预注册_20260804.md`
- 定向近案：通用动态污点检测、数据血缘、独立原始输入重算、见证原子超图准入、当前—候选视频证据替换及匹配反事实

## 事实边界

当前本地代码只部分支持证据 ID、时间窗、全局/局部视图、OCR/ASR 字段和可追溯载荷，未实现 V4.6 的许可服务、读取域隔离、四时点、迁移—许可配准和闭包事务。任何算法细化只能写成可实施方案，不能写成已经运行或已经取得效果。
