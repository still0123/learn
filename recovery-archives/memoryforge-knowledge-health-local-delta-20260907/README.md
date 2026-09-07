# MemoryForge 本地代码增量备份

备份日期：2026-09-07

此归档只保存个人 MemoryForge 工作树中、相对于 `e2fba0fee81fd4813a72121bf679f673274ab6ca` 的本地代码增量：

- `WORKTREE.patch`：对两个已跟踪 Python 源文件的二进制安全 Git 补丁；
- `untracked/src/memoryforge/storage/query_gaps.py`：唯一未跟踪的新增 Python 源文件。

未包含工作树的任何 ignored 内容、运行时、缓存、凭据、公司资料，或其他项目文件。

恢复方法：克隆 `still0123/MemoryForge`，检出上述基线提交，执行 `git apply --check WORKTREE.patch` 和 `git apply WORKTREE.patch`，再将 `untracked/` 下的文件按相对路径复制到工作树。`SHA256SUMS` 用于逐文件完整性核验。
