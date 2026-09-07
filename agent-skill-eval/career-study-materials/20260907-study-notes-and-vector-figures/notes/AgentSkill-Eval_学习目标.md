# AgentSkill-Eval 学习目标

## 总目标

在能解释源码、实验边界和真实结果的前提下，把 AgentSkill-Eval 作为一段可信的 AI Agent 工程项目写入秋招简历。

## 可验收目标

### 知识

- 能区分 Agent、Skill、Tool、Runner、Oracle、Trace。
- 能解释配对实验、控制变量、FAIL/INVALID、W/T/L、bootstrap、数据泄漏。
- 能解释 search、regression、confirmation、locked test 的目的与边界。

### 源码

- 能顺着 `planning.py -> execution.py -> runner adapter -> store.py -> statistics.py` 讲清一次实验。
- 能顺着 `proposal.py -> search.py -> final_evaluation.py -> promotion_workflow.py` 讲清 Skill v1 到 v2 的门禁。
- 能现场修改一个小需求，例如：给 Run 输出添加上限，或给 Dataset split 增加来源校验。

### 实验

- 能区分训练证据、搜索证据、回归证据和独立终评证据。
- 能解释当前 V2 正在运行的结果应如何标注，避免用已暴露数据证明泛化。
- 能报告成功率、W/T/L、INVALID、Token、时延和成本，而不是只报单一分数。

### 面试

- 完成 30 秒、2 分钟和 5 分钟三种项目讲述。
- 准备一个真实失败复盘。
- 不夸大为“生产 Sandbox”“不可篡改链”“全自动优化”或“显著泛化提升”。

## 交付清单

- `AgentSkill-Eval_秋招知识与源码手册.md`
- `AgentSkill-Eval_一天速成版.md`
- `AgentSkill-Eval_三天速成版.md`
- `AgentSkill-Eval_通透理解.md`
- Nature 风格架构/流程图导出文件

