# I1-V1 rank 001-040 官方正文核验汇总

## 执行范围

- 输入合同：`00_brief.md`
- 输入队列：`01g_fulltext_verification_queue.jsonl`
- 处理范围：仅 `rank=1-40`
- 队列快照 SHA256：`309fd5ce5c8af3075132dabf25f092f769d174866f86b14d90f0b3faadbbc032`
- 输出：`01v1_verified_001_040.jsonl`
- 未执行专利构思、正式稿修改或 Git 操作。

## 结果计数

| 指标 | 数量 |
|---|---:|
| 总记录 | 40 |
| 新抓取成功 | 6 |
| 复用既有全文核验 | 34 |
| 失败 | 0 |
| `FULL_TEXT_UNAVAILABLE` | 0 |
| `pool_eligible=true` | 22 |
| 背景记录 | 18 |

所有 40 条均为 `verified_from_full_text=true`。复用记录标记为
`REUSED_VERIFIED_FULL_TEXT`，新抓取记录标记为 `VERIFIED_FULL_TEXT`。

## 新抓取记录

| rank | 论文 | 正文入口 | HTTP | 正式 venue | 核验重点 |
|---:|---|---|---:|---|---|
| 35 | VideoSEAL | `https://arxiv.org/html/2605.12571` | 200 | ICML 2026 | Planner/Inspector 回答权分离、二元充分性门、预算耗尽 fallback、Appendix C.9 限制 |
| 36 | Seeing the Scene Matters | `https://arxiv.org/html/2603.27259` | 200 | CVPR 2026 Highlight | SceneBench、Scene-RAG、多模态场景记忆、跨场景遗忘及标注限制 |
| 37 | Reasoning for Social Audio-Visual QA | `https://arxiv.org/html/2608.13239` | 200 | HCMIW @ ECCV 2026 | IntentBench-Prime、Vanilla SFT、Question/Caption SFT 反向对照、Limitations |
| 38 | When and Where to Look | `https://arxiv.org/html/2608.03918` | 200 | 未核验到正式 venue | EcoFrame、熵门控预算、attention 时间先验、边际效用重选、Appendix C 限制 |
| 39 | Adversarial Robustness under Visual Token Compression | `https://arxiv.org/html/2601.21531` | 200 | ICML 2026 | CAGE、存活概率加权扰动、排名-扰动对齐、压缩感知防御与 Appendix G 限制 |
| 40 | Less Is More -- Until It Breaks | `https://arxiv.org/html/2601.12042` | 200 | 未核验到正式 venue | CAA/T-CAA、token 排名不稳定、压缩状态特有失效、效率-安全权衡 |

六篇 arXiv HTML 均首次请求成功，无 5xx/超时重试，也未触发
HTML、PDF、作者仓库或 DOI 后备入口。正式 venue 与最早公开日期由
arXiv API 元数据交叉核验。

## 核验结论

- rank 35 是强近邻：独立 Inspector 掌握停止和回答权，但充分性仍可能误判，预算耗尽会强制最终检查。
- rank 36 证明场景跨度增加会加剧遗忘；Scene-RAG 缓解但依赖离线场景切分和多模型记忆构建。
- rank 37 是强反向证据：简单 SFT 可匹配复杂推理方法，问题无关 caption 与完整音视频表现接近。
- rank 38 以输出熵和帧级 attention 低开销调度证据；熵不是正确性证书，极短事件仍可能漏检。
- rank 39、40 均表明视觉 token 压缩引入额外攻击面；标准全 token 测试可能高估低预算部署的鲁棒性。

## 完整性校验

- JSONL 行数：40
- rank 范围：1-40
- 唯一 rank：40
- 要求字段：23/23 全部存在且顺序一致
- JSON 解析：通过
- 队列标题及继承字段逐条一致：通过
- 非空正文核验章节、机制、控制流、数据结构、效果与限制：通过
- `error_code != null`：0

## SHA256

| 文件 | SHA256 |
|---|---|
| `00_brief.md` | `48113d5c3e9680ffeadc489c6174828c9c8aa1c5f61f75532883001c9ec3705d` |
| `01a_sources_papers.jsonl` | `4a42d3c4bd8a1522b7efd8f2ec8fc444695ea4fb63f6c289bf38cf43f90b5f24` |
| `01b_sources_papers.jsonl` | `a3b10aa3259773b34dcdf7e77aebb242f73aad887d1e3425818854c3e073a847` |
| `01g_fulltext_verification_queue.jsonl` | `309fd5ce5c8af3075132dabf25f092f769d174866f86b14d90f0b3faadbbc032` |
| `01h_verified_seed_papers.jsonl` | `961e84fdd33b809e2687148965563dcb2ef073840ea74f699f9890f1d72972c4` |
| `01v1_verified_001_040.jsonl` | `7d0cf750de856a7aefb08fb1a95f13ac0937d0b2c4e0810498092819c50ec986` |
