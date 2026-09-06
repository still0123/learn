# SoftwareCopyright-Skill 本地改动恢复归档

此归档仅保存本机 `SoftwareCopyright-Skill` 工作树相对上游 `main` 的一项本地改动；不复制第三方仓库的完整历史或无关文件。

## 来源与边界

- 上游：`Fokkyp/SoftwareCopyright-Skill`
- 基线提交：`0a27d1143eca253b7b7e953794a24ef6e5488b0d`
- 本机提交：`07954dfd51e77206c4a3b7f81229343b7fbf6d90`
- 改动文件：`software-copyright-materials/scripts/build_docx_from_md.py`

`payload/patch/local-change.patch` 是不含作者、邮件或提交头的纯 diff；`payload/software-copyright-materials/scripts/build_docx_from_md.py` 是改动后的完整文件。归档前对两项 payload 做了公司标记、高置信凭据和泛凭据字段扫描，结果均为 0。

## 恢复方式

1. 从上游取得基线提交。
2. 校验 `SHA256SUMS`。
3. 应用 `payload/patch/local-change.patch`，或在确认路径一致后使用 payload 中的完整文件替换目标文件。

原工作树保留在本机，不因本归档而移动。
