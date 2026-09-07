# P4 定向现有技术拥挤度矩阵

> 本文件是定向预检，不是完整查新、FTO、专利族核验或法律状态核验。

| 方向 | 接近公开 | 已公开核心 | 可争辩剩余差异 | 风险 |
|---|---|---|---|---|
| 1. 事件状态链 | [Semantic Event Graphs](https://arxiv.org/abs/2601.06097)、[TRACE](https://arxiv.org/abs/2410.05643)、[US11582485B1](https://patents.google.com/patent/US11582485B1/en) | 对象跟踪、事件序列、时间场景图、静态/动态节点 | 声明行为契约限定状态节点/边，并由路径完整性直接控制声明许可 | 高 |
| 2. 声明条件化证据行为 | [Query-Conditioned Evidential Keyframe Sampling](https://arxiv.org/abs/2604.01002)、[Active Video Perception](https://arxiv.org/abs/2512.05774)、[Select Less, Reason More](https://arxiv.org/abs/2510.15440) | query 条件证据价值、动态计划和证据充分性 | 条件对象是声明行为契约；同一观测在不同声明下形成不同轨迹聚合和支持状态 | 高 |
| 3. 文字生命周期 | [Gather and Trace](https://arxiv.org/abs/2508.04197)、[GoMatching](https://arxiv.org/abs/2401.07080)、[Video Text Rediscovery](https://doi.org/10.1111/coin.12686) | 文字实例聚合、长短期匹配、遮挡后重发现 | 生命周期状态控制问题时点有效文字版本和声明资格 | 高 |
| 4. 事实—营销意图分层 | [AD-MIR](https://openreview.net/forum?id=9vPBISqNVo)、[AdsQA](https://arxiv.org/abs/2509.08621)、[E-VAds](https://arxiv.org/abs/2602.08355) | 像素事实到说服逻辑、客观内容与营销/商业意图推理 | 事实状态撤销自动使依赖意图失效的可执行跨层关系 | 很高 |
| 5. 失败—未知—缺席 | [Video-LLM Answerability Alignment](https://openreview.net/forum?id=P9VdRQOyqu)、[SpatialUncertain](https://arxiv.org/abs/2605.30557)、[MM-AQA](https://arxiv.org/abs/2604.14799) | 不可回答、遮挡/视角歧义、证据充分性和拒答 | 检测失败独立建模，且覆盖证明控制 `NOT_DETECTED→VERIFIED_ABSENT→否定许可` | 中高 |

## 预检结论

- 纯事件状态图、纯 query 条件选证据和纯文字生命周期均处于高拥挤区。
- 方向 1 与方向 2 只有形成“声明契约→允许状态路径→声明许可”的不可拆分关系，才值得进入正式查新。
- 方向 5 的精确状态升级条件具有相对更清楚的剩余空间，但与拒答和不确定性建模仍有组合覆盖风险。
- 方向 4 不进入本轮推荐前三。
