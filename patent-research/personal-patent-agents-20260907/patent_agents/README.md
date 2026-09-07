# patent_agents

本目录提供本地专利多 Agent 工作流的**确定性辅助层**，不替代真正的专利判断。

职责边界：

- 生成材料清单；
- 对本地文本做稳定切块；
- 对本地材料做关键词/正则搜索；
- 拼装每轮运行报告；
- 校验运行目录结构和必要门禁项；

不负责：

- 自动判定创造性；
- 自动生成法律结论；
- 自动决定某创新点可直接提交；

这些结论必须由 `P0-P9` 工作流产生，并经 `gates.md` 约束。

## 目录结构

```text
patent_agents/
  config/
  schemas/
  scripts/
  index/
```

## 脚本说明

### `scripts/build_material_manifest.py`

扫描项目中的关键专利、审查、论文、代码材料，生成 `config/material_manifest.yaml`。

示例：

```bash
python3 patent_agents/scripts/build_material_manifest.py
```

### `scripts/chunk_source_texts.py`

将 `source_texts/` 下的长文本切为稳定 chunk，输出到 `index/source_chunks.jsonl`。

示例：

```bash
python3 patent_agents/scripts/chunk_source_texts.py --chunk-size 1200 --overlap 150
```

### `scripts/keyword_search.py`

对材料清单中的文件做本地关键词/正则搜索，输出 Markdown 报告或 JSON 结果。

示例：

```bash
python3 patent_agents/scripts/keyword_search.py --query "链式校验" --query "RAG" --out runs/demo/search.md
```

### `scripts/assemble_round_report.py`

将某一轮 `runs/patent-analysis-.../` 目录中的主要文档拼成一个总览报告。

示例：

```bash
python3 patent_agents/scripts/assemble_round_report.py --run-dir runs/patent-analysis-20260623-round01
```

### `scripts/validate_outputs.py`

检查运行目录结构、关键标题、gate 文件和明显占位残留。

示例：

```bash
python3 patent_agents/scripts/validate_outputs.py runs/patent-analysis-20260623-round01
```

## 推荐使用顺序

1. 先运行 `build_material_manifest.py`。
2. 再运行 `chunk_source_texts.py`，构建稳定文本索引。
3. 用 `keyword_search.py` 做问题驱动检索。
4. 多 Agent 工作流产出各报告。
5. 用 `assemble_round_report.py` 拼装总览。
6. 用 `validate_outputs.py` 做最终结构校验。

## 设计原则

- 所有路径默认指向 `/Users/bytedance/vqa_thesis_continue`。
- 默认只使用 Python 标准库，避免额外依赖。
- 输出优先使用 UTF-8 文本、Markdown、JSONL。
- 不静默截断关键材料；必要时必须显式切块并记录 chunk id。
