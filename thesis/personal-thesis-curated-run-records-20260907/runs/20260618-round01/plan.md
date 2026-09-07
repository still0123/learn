# 20260618-round01 夜间执行计划

## 目标

在用户休息期间完成以下工作：

1. 固化闭环多 Agent 编排规范；
2. 建立题目与术语唯一真源；
3. 等待 deep-research 返回真实参考文献；
4. 使用闭环版第3章、第4章与第5章当前版整合完整论文；
5. 生成 Markdown 与 Word；
6. 生成明早检查清单。

## 输入

- docs/术语与题目真源.md
- docs/agent_orchestration_v2.md
- docs/第3章_闭环审查修订版.md
- docs/第4章_闭环审查修订版.md
- docs/第5章_实验设计与结果分析.md
- deep-research 结果（等待中）

## 输出

- docs/完整论文_题目不变_证据流闭环版.md
- docx/基于视觉特征压缩与链式反思的广告视频问答方法_完整论文_证据流闭环版.docx
- docs/真实参考文献核查清单.md
- docs/明早检查摘要.md

## Gates

- 题目不变
- 不编实验数据
- 未核查引用标注待核查
- 不写入 efs-mgr
