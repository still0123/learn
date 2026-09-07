# 材料清单

## 核心材料

| 材料 | 路径 | 用途 |
|---|---|---|
| 驳回决定 PDF | `/Users/bytedance/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_l0i79alm05q221_dd3c/msg/file/2026-08/CS2215-基于视听协同感知与链式校验的广告视频问答方法及系统-驳回决定.pdf` | 最终驳回依据 |
| 驳回提取文本 | `runs/patent-analysis-20260813-round01/rejection_extract.txt` | 行号引用 |
| 原申请文本 | `source_texts/patent_docx.txt` | 原权利要求与说明书 |
| 第二次审查意见 | `source_texts/patent_office_action_pdf_extract.txt` | 审查过程 |
| 最终意见陈述 | `专利相关/意见陈述书_合并修改后_二次润色.txt` | 申请人抗辩 |
| 新候选稿 | `deliverables/patent/广告视频问答专利申请候选稿.md` | 新申请方向 |

## 技术与实验材料

- `code_refactor/evidence/evidence_package.py`
- `code_refactor/reflection/claim_checker.py`
- `code_refactor/rag/retriever.py`
- `docs/论文思考记录.md`
- `docs/AdsQA最终结果交付_20260731.md`
- `docs/Luna_问题驱动证据选择与证据缺口工具补证实验SPEC_20260804.md`

## 对比文件

1. `CN121388101A`：迭代式多模态视频问答。
2. `CN117744802A`：法律大语言模型自验证与答案修正。
3. `CN121765049A`：全局/局部视觉与外部知识 RAG。
4. `CN121031606A`：多模态对齐、语义提取和约束解码。
5. `CN121350217A`：问题相关 Grad-CAM 关注区域。

## 事实边界

- 驳回决定最终仅以专利法第22条第3款创造性不足为理由。
- 驳回针对2026年5月22日提交的权利要求1-6。
- 2026年6月4日第二轮答复没有继续修改权利要求。
