# 本地工作区恢复快照（2026-09-06）

此目录只保存用户批准的、经 allowlist 过滤的个人源码改动与 Git 补丁。

## 恢复内容

| 快照 | 内容 |
|---|---|
| `skill-learning-engine` | 45 个当前文件和一份二进制 Git diff。 |
| `dshagent` | 5 个当前文件和一份二进制 Git diff。 |
| `qmemory-local-fix` | 仅保存针对第三方上游的二进制 Git diff。 |
| `memoryforge-dev` | 3 个当前源码文件和一份二进制 Git diff。 |
| `memoryforge-feishu-worktree` | 3 个当前源码文件和一份二进制 Git diff。 |
| `memoryforge-wiki-refactor` | 1 个当前源码文件和一份二进制 Git diff。 |
| `memoryforge-legacy-git-adapter` | 1 个当前源码文件和一份二进制 Git diff。 |

每个 `files/` 路径保留其相对于原工作区的路径；`git-diff.binary.patch` 可按 `PROVENANCE.tsv` 中的基线 commit 恢复。

## 安全边界

- 不包含 `.env`、密钥、恢复码、个人证件、照片、VQA reference answers、缓存、虚拟环境、调试日志或工作区数据。
- `memoryforge-feishu-worktree/tests/test_feishu_bot.py` 原本在候选范围内，但静态扫描发现其含有 `efs-mgr` / `filenas-mgr` 公司仓库夹具，已从本快照及补丁中剔除。本地原件没有改动。
- QMemory 是第三方上游工作区，因此仅备份本地修改的可应用 patch，不复制完整上游代码。
- `SHA256SUMS` 仅覆盖本目录中归档的源码文件和补丁（即 `MANIFEST.tsv` 所列负载），不覆盖本说明和核验元数据本身。

## 核验步骤

1. 在全新克隆的 `still0123/learn` 中执行 `shasum -a 256 -c SHA256SUMS`。
2. 对 `files/` 中的每个文件，和 `PROVENANCE.tsv` 指向的原工作区相对路径逐字节比较。
3. 对每个 patch，在对应基线 checkout 上运行 `git apply --check git-diff.binary.patch`。
4. 运行 `git fsck --full`；本快照不使用 Git LFS。

源工作区不因此移动或删除。
