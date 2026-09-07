# 远端 3000 样本实验状态

日期：2026-07-07

远端机器：`adsqa`

远端项目目录：

```text
/data1/rmx/projectb/AdsQA-main
```

## 样本设置

本轮采用 balanced3000，对 AdsQA 五个一级类型各采样 600 条：

| Type | 可用数 | 采样数 |
|---|---:|---:|
| Type_1 | 2173 | 600 |
| Type_2 | 947 | 600 |
| Type_3 | 2330 | 600 |
| Type_4 | 1468 | 600 |
| Type_5 | 941 | 600 |

生成文件：

```text
/data1/rmx/projectb/AdsQA-main/data/balanced600_by_primary_type_seed42_question.json
/data1/rmx/projectb/AdsQA-main/data/balanced600_by_primary_type_seed42_groundtruth.json
/data1/rmx/projectb/AdsQA-main/data/balanced600_by_primary_type_seed42_manifest.json
```

## 对比方法

| 顺序 | Run | 脚本 | 关键设置 | 目的 |
|---:|---|---|---|---|
| 1 | `qwen3_raw_uniform_norag_bal3000_20260707` | `evaluation/inference_qwen3_raw_uniform_20260629.py` | `rag_mode=none`, `top_k_frames=8`, `oversample_count=8` | 同底座 raw uniform baseline |
| 2 | `qwen3_evidence_norag_bal3000_20260707` | `evaluation/inference_ours_param_evidence.py` | `rag_mode=none`, `top_k_frames=16`, `oversample_count=32` | 当前最强 evidence no-RAG 基线 |
| 3 | `adslot_ir_norag_bal3000_20260707` | `evaluation/inference_adslot_ir_20260707.py` | `rag_mode=none`, `top_k_frames=16`, `oversample_count=32`, `adslot_mode=on`, `adslot_min_top_k=8`, `adslot_max_top_k=20` | Top1 广告证据槽输入重构 |

调度脚本：

```text
/data1/rmx/projectb/AdsQA-main/evaluation/scripts/run_adslot_ir_3000_20260707.py
```

主日志：

```text
/data1/rmx/projectb/AdsQA-main/evaluation/runs/adslot_ir_3000_20260707.log
/data1/rmx/projectb/AdsQA-main/evaluation/runs/adslot_ir_3000_20260707.nohup.log
```

## 已完成检查

| 检查项 | 结果 |
|---|---|
| SSH `adsqa` | 可连接 |
| 模型路径 `/data1/qky/Model/Qwen3Vl-8B` | 可用 |
| balanced3000 生成 | 已完成 |
| `inference_adslot_ir_20260707.py` 语法检查 | 通过 |
| adslot dry-run | 通过 |
| adslot 3 条真推理 smoke | 通过，`errors=0`, `missing=0`, evidence 中有 `adslot_route` |
| 本地防息屏 | 用户级 launchd 任务 `vqa_thesis_caffeinate` 已启动，运行 `/usr/bin/caffeinate -dimsu` |

## 当前进度快照

记录时间：2026-07-07 03:55 CST

| Run | prediction 数量 | 进程状态 |
|---|---:|---|
| `qwen3_raw_uniform_norag_bal3000_20260707` | 2793 / 3000 | GPU0 长尾运行中 |
| `qwen3_evidence_norag_bal3000_20260707` | 0 / 3000 | 等待 raw 完成后启动 |
| `adslot_ir_norag_bal3000_20260707` | 0 / 3000 | 等待 evidence 完成后启动 |

GPU 状态：6 张 A6000 均在运行 raw baseline，显存约 19GB，利用率约 80%-90%。

最近监控显示 raw baseline 在 02:04-02:19 期间从 224 增长到 567，增长稳定。02:10-02:18 的分钟级监控显示从 380 增长到 540，平均约 20 条/分钟。

注意：GPU0 shard 当前慢于其他 shard，显存约 46GB，但日志仍在推进；暂不重启，继续观察是否成为长尾。

02:20 检查：raw baseline 已到 596/3000，`error.json` 数量为 0。

02:31 检查：raw baseline 已到 863/3000，`error.json` 数量为 0。02:21-02:30 的分钟级监控显示从 620 增长到 831，约 21 条/分钟。

02:32 检查：raw baseline 已到 881/3000，三组 `error.json` 数量均为 0；runner 与 6 个 raw shard 进程均存活。runner 自身日志显示 02:24 为 702/3000，02:29 为 820/3000，alive=True。

02:39 检查：raw baseline 已到 1038/3000，三组 `error.json` 数量均为 0；raw 已超过 1000 条。

02:57 检查：raw baseline 已到 1471/3000，三组 `error.json` 数量均为 0；runner 自身日志 02:54 记录 1415/3000，alive=True。02:32-02:54 的 2 分钟监控显示从 891 增长到 1417，约 24 条/分钟。

02:58 检查：raw baseline 已到 1490/3000，三组 `error.json` 数量均为 0；接近 raw 半程。

03:19 检查：raw baseline 已到 1972/3000，三组 `error.json` 数量均为 0；03:00-03:16 的 2 分钟监控显示从 1548 增长到 1925，速度仍稳定。

03:20 检查：raw baseline 已到 1992/3000，三组 `error.json` 数量均为 0；runner 与 raw shard 进程均存活。

03:44 检查：raw baseline 已到 2579/3000，三组 `error.json` 数量均为 0；runner 自身日志 03:39 记录 2468/3000，alive=True。快 shard 已接近完成，GPU0 将成为明显长尾，但仍在推进。

03:55 检查：raw baseline 已到 2793/3000，三组 `error.json` 数量均为 0；GPU1-GPU5 shard 均已完成，当前仅 GPU0 shard 继续运行。GPU0 当前 297/500，约剩 203 条，显存约 44GB，利用率 100%。

03:58 尾段加速：由于仅 GPU0 shard0 剩余且预计长尾较久，启动 GPU1-GPU5 分担 shard0 后半段全局区间：

| GPU | start_idx | end_idx |
|---:|---:|---:|
| 1 | 2040 | 2232 |
| 2 | 2232 | 2424 |
| 3 | 2424 | 2616 |
| 4 | 2616 | 2808 |
| 5 | 2808 | 3000 |

这些进程与原始 raw run 共用输出目录，脚本会对已有 `prediction.json` 自动 skip。03:59 检查显示 raw 已到 2818/3000，GPU1-GPU5 均已加载模型并开始处理，各自约 3/32。

04:08 检查：所有 raw shard 结束后，唯一预测文件数为 2980。GPU0 原始 shard 有 18 条 OOM 错误，原因是 GPU0 上存在其他任务占用显存；另外 balanced3000 中有 2 个重复 `question_id`，所以最多只有 2998 个唯一预测目录。

04:10 修复：

- 停止旧 runner，避免它按唯一文件数 3000 误判后整组重启。
- 杀掉旧 runner 抢先误启动的 5 个 raw 重跑进程。
- 在 GPU1 单独补跑 `start_idx=1932,end_idx=2035,shard_id=0,num_shards=6`，覆盖 18 个 OOM 缺失样本。
- patch `evaluation/scripts/run_adslot_ir_3000_20260707.py`，将完成判据从唯一 `prediction.json` 文件数改为 `covered_rows`：对 3000 行 question 逐行检查对应 qid 是否已有 prediction。这样重复 qid 会被正确视为两行均覆盖。

04:15 检查：raw baseline 已达到 `covered_rows=3000/3000`，`unique_files=2998`，`missing_rows=0`。`collect_summary.json` 已生成，runner 已进入 raw 评分阶段。

04:27 检查：raw baseline 评分完成。评分脚本尾部有 3 个 DeepSeek API 请求长时间未返回，已单独断点补评并写回对应 `prediction.json`，随后重启 runner 继续主流程。

raw 当前汇总：

| 指标 | 数值 |
|---|---:|
| covered_rows | 3000 |
| unique_files | 2998 |
| missing | 0 |
| Answer: 1 | 1153 |
| Answer: 0.5 | 785 |
| Answer: 0 | 1062 |

04:27 runner 已启动 `qwen3_evidence_norag_bal3000_20260707`，使用 GPU1-GPU5；GPU0 因有其他用户任务占用显存，继续避开。启动命令参数为 `--rag_mode none --oversample_count 32 --top_k_frames 16`。

04:32 检查：evidence 推理健康推进，`unique_files=86/3000`，`error.json=0`。GPU1-GPU5 均在使用，吞吐约 18-20 条/分钟。

04:38 检查：evidence `unique_files=205/3000`，`error.json=0`，5 个 shard 均存活。

04:43 检查：evidence `unique_files=301/3000`，`error.json=0`，速度约 19 条/分钟，暂不干预。

04:58 检查：evidence `unique_files=589/3000`，`error.json=0`，持续稳定推进，约每 5 分钟增加 95 条。

05:28 检查：evidence `unique_files=1182/3000`，`error.json=0`，5 个 shard 均存活。04:33-05:28 从 113 增至 1182，约 19.4 条/分钟。

05:49 检查：evidence `unique_files=1570/3000`，`error.json=0`，已过半，5 个 shard 均存活。

06:14 检查：evidence `unique_files=2050/3000`，`error.json=0`，已超过三分之二，5 个 shard 均存活。

06:39 检查：evidence `unique_files=2529/3000`，`error.json=0`，剩余不到 500 条，5 个 shard 均存活。

07:07 检查：evidence 推理完成，`covered_rows=3000/3000`，`unique_files=2998`，`missing=0`，进入评分。

07:20 检查：evidence 评分完成。尾部 4 个空 score 和 2 个无效 `Answer` 已单独补评后重启 runner，最终汇总为 `Answer:1=1215, Answer:0.5=807, Answer:0=978`，strict=40.50%，relaxed=53.95%。

07:20 runner 已启动 `adslot_ir_norag_bal3000_20260707`，使用 GPU0-GPU5 六张卡；参数为 `--rag_mode none --oversample_count 32 --top_k_frames 16 --adslot_mode on --adslot_min_top_k 8 --adslot_max_top_k 20`。

07:25 检查：adslot `unique_files=96/3000`，`error.json=0`。6 个 shard 均已通过前 10 条样本，日志显示 `missing_video_or_frames=0, errors=0`，启动健康。

07:36 检查：adslot `unique_files=331/3000`，`error.json=0`，6 个 shard 均存活，速度约 22 条/分钟。

08:06 检查：adslot `unique_files=1012/3000`，`error.json=0`，6 个 shard 均存活，已超过 1000 条。

08:26 检查：adslot `unique_files=1464/3000`，`error.json=0`，6 个 shard 均存活，接近半程。

08:31 检查：adslot `unique_files=1584/3000`，`error.json=0`，已过半，6 个 shard 均存活。

08:51 检查：adslot `unique_files=2030/3000`，`error.json=0`，已超过三分之二，6 个 shard 均存活。

09:16 检查：adslot `unique_files=2588/3000`，`error.json=0`，剩余约 400 条，6 个 shard 均存活。

Shard 进度：

| GPU | shard 进度 |
|---:|---:|
| 0 | 297/500 |
| 1 | 完成，processed=499, skipped_existing=1, errors=0 |
| 2 | 完成，processed=500, errors=0 |
| 3 | 完成，processed=500, errors=0 |
| 4 | 完成，processed=500, errors=0 |
| 5 | 完成，processed=499, skipped_existing=1, errors=0 |

GPU shard 日志显示：

```text
missing_video_or_frames=0, errors=0
```

09:44 检查：adslot runner 完成，`covered_rows=3000/3000`，`unique_files=2998`，`missing=0`，`error.json=0`。评分器有 2 条返回畸形分数字段 `: 0`，重复补评后仍返回同样格式；按语义规范化为 `Answer: 0` 后重新汇总，`score_unknown=0`。

## 最终结果

balanced3000 中有 2 个重复 `question_id`，所以最终唯一预测目录数为 2998；完成率按 3000 行样本覆盖统计。

| Run | strict | relaxed | missing | errors | 备注 |
|---|---:|---:|---:|---:|---|
| `qwen3_raw_uniform_norag_bal3000_20260707` | 38.43% | 51.52% | 0 | 18 已补跑 | raw baseline；score=`1:1153,0.5:785,0:1062` |
| `qwen3_evidence_norag_bal3000_20260707` | 40.50% | 53.95% | 0 | 0 | evidence baseline；score=`1:1215,0.5:807,0:978` |
| `adslot_ir_norag_bal3000_20260707` | 41.87% | 55.28% | 0 | 0 | Top1 方法；score=`1:1256,0.5:805,0:939` |

提升幅度：

| 对比 | strict 提升 | relaxed 提升 |
|---|---:|---:|
| evidence no-RAG vs raw uniform | +2.07 pp | +2.43 pp |
| adslot vs evidence no-RAG | +1.37 pp | +1.33 pp |
| adslot vs raw uniform | +3.44 pp | +3.76 pp |

关键判断：

- AdSlot-IR 在 strict 和 relaxed 上均高于 evidence no-RAG，可以作为 Top1 主实验继续扩展消融。
- 下一步优先分析 `adslot_route` 分布、`effective_top_k_frames`、evidence 选择来源分布，以及按 Type / OCR / CTA / brand / product 子集的收益差异。
- 论文叙事可以从“广告证据槽对视觉广告问答的结构化输入重构”展开，再配合四维链或证据许可机制作为后续增强模块。
