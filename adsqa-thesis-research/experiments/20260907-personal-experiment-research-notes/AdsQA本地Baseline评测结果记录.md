# AdsQA 本地 Baseline 评测结果记录

记录日期：2026-07-07

远程机器与目录：

- SSH：`adsqa`
- 项目目录：`/data1/rmx/projectb/AdsQA-main`
- 结果来源：`evaluation/results*`
- 统计方式：读取各预测 JSON 中的 `score` 字段，按 `Answer: 1 / 0.5 / 0` 计算。
- 指标：`Strict = Answer:1 / N`；`Relaxed = (Answer:1 + 0.5 * Answer:0.5) / N`。

## 主口径结果

| 本地结果目录 | 模型/方法 | 样本数 | Answer:1 | Answer:0.5 | Answer:0 | Unknown | Strict | Relaxed | 备注 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `evaluation/results_qwen3_baseline` | `Qwen3-VL-Instruct` | 7812 | 2959 | 2070 | 2783 | 0 | 0.3788 | 0.5113 | Qwen3-Base |
| `evaluation/results` | `Qwen2.5-7B-VL-ReAd-R` | 7829 | 2709 | 2113 | 3007 | 0 | 0.3460 | 0.4810 | Qwen2.5-ReAd 主口径 |
| `evaluation/results222` | `Qwen2.5-VL-7B-Instruct` | 7829 | 1197 | 1643 | 4988 | 1 | 0.1529 | 0.2578 | 普通 Qwen2.5-VL |
| `evaluation/results_qwen2vl` | `Qwen2-VL-7B-Instruct` | 7829 | 1640 | 2055 | 4117 | 17 | 0.2095 | 0.3407 | Qwen2-VL |
| `evaluation/results_minicpm` | `MiniCPM-V-2_6` | 7839 | 1824 | 2070 | 3918 | 27 | 0.2327 | 0.3647 | MiniCPM |
| `evaluation/results_llava_ov` | `llava-onevision-qwen2-7b-ov-hf` | 7839 | 1163 | 1962 | 4687 | 27 | 0.1484 | 0.2735 | LLaVA-OneVision |

## 不作为主口径的结果

| 本地结果目录 | 模型/方法 | 样本数 | Strict | Relaxed | 不作为主口径原因 |
|---|---|---:|---:|---:|---|
| `evaluation/results copy` | `Qwen2.5-7B-VL-ReAd-R` | 6359 | 0.4336 | 0.5256 | 子集/拷贝目录，且有 462 个 `unknown` |
| `evaluation/results222_fixed` | `Qwen2.5-VL-7B-Instruct` | 7829 | 0.0392 | 0.0710 | `unknown=5806`，分数字段不可直接用 |
| `evaluation/results_cot_baseline` | `Qwen2.5-VL-7B-Instruct` | 6044 | 0.0470 | 0.0743 | 子集且 `unknown=4617` |

## 写论文时的口径提醒

- “最新三次实验”主要是 Qwen3VL-8B 内部消融，不能代表完整 baseline 对比表。
- 完整 baseline 对比应优先引用本文件“主口径结果”。
- `Qwen2.5-ReAd` 对应本地结果目录 `evaluation/results` 下的 `Qwen2.5-7B-VL-ReAd-R.json`。
- `Qwen3-Base` 对应本地结果目录 `evaluation/results_qwen3_baseline` 下的 `Qwen3-VL-Instruct.json`。
- 如果使用 2500 balanced 子集的新实验结果，需要单独标注为子集实验，避免与 7812/7829/7839 全量或近全量结果混比。

