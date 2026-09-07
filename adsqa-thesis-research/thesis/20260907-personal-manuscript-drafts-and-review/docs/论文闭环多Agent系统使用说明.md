# 论文闭环多 Agent 系统使用说明

已创建可执行 workflow：

```text
.claude/workflows/thesis-closed-loop.js
```

## 目标

围绕 AdsQA 广告视频问答毕业论文，执行：

```text
资料读取 → 文献补充 → 写作规划 → 方法/实验章节草稿 → 技术/创新/语言审查 → 返修定稿
```

## 主要 Agent

- A0 主编/总控：统一论文主线、术语、结果口径。
- A1 资料检索：补参考文献、标注风险引用。
- A2 方法写作：生成方法章节正文。
- A7 实验写作：生成实验章节正文。
- A3 技术审查：检查方法、实验、公平性。
- A4 创新性审查：防止写成模块拼接。
- A5 语言结构审查：检查论文语言与结构。
- A6 修改 Agent：根据审查意见返修。

## 推荐调用

在 Claude Code 中运行 workflow：

```js
Workflow({
  scriptPath: "/Users/bytedance/vqa_thesis_continue/.claude/workflows/thesis-closed-loop.js",
  args: {
    task: "根据当前 AdsQA 实验结果、开题报告、中期答辩材料和已有论文草稿，生成方法章节和实验章节的可并入论文版本，并给出审稿意见和返修稿。",
    targetSections: ["第3章 方法", "第5章 实验", "相关工作补充", "审稿意见与返修"],
    thesisTitle: "基于视听协同感知与链式校验的广告视频问答方法",
    projectRoot: "/Users/bytedance/vqa_thesis_continue"
  }
})
```

## 内置当前实验口径

workflow 已内置当前阶段性结论：

- balanced2500 主表；
- BGE top2 当前主方法；
- BGE top3、type-aware、verifier 的消融结果；
- Qwen2.5 baseline 与 Qwen3 方法对比公平性风险；
- Qwen3 no-RAG/raw baseline 为待补实验。

若后续实验结果更新，应在调用 args 或 workflow 文件中更新 `KNOWN_RESULTS`。

## 注意

- workflow 只生成写作与审查内容，不直接覆盖论文正文。
- 不编造实验数据；缺失结果标注为“待补”。
- 参考文献必须核查后再写入正式论文。
- 论文主线应写为“视听证据筛选 + 类型感知营销知识检索 + 低噪声知识注入 + 受约束推理”，避免写成简单的 RAG/CoT/Reflection 拼接。
