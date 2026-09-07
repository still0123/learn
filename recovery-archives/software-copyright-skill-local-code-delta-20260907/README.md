# SoftwareCopyright-Skill 本地代码增量备份

备份日期：2026-09-07

此归档只保存本地提交 `07954dfd51e77206c4a3b7f81229343b7fbf6d90` 相对于上游可达基线 `0a27d1143eca253b7b7e953794a24ef6e5488b0d` 的唯一代码修改：

- `software-copyright-materials/scripts/build_docx_from_md.py`

`WORKTREE.patch` 是二进制安全 Git 补丁。未包含 README、Skill 文档、申请表信息、DOCX/PDF、生成 demo、依赖、构建输出或任何其他工作树文件。

恢复方法：克隆 `Fokkyp/SoftwareCopyright-Skill`，检出上述基线提交，运行 `git apply --check WORKTREE.patch` 与 `git apply WORKTREE.patch`。`SHA256SUMS` 用于完整性核验。
