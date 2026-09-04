# AgentSkill-Eval 本地导出快照

该归档保存 2026-09-04 产生的一份无 `.git` 本地导出树。它与已推送的 AgentSkill-Eval 归档分支存在大量文件差异，因此作为恢复快照保留，不作为当前权威源码。

## 内容

- 原始文件数：399
- 原始逻辑大小：约 12 MiB
- 归档格式：`tar.zst`
- 文件级哈希：`SHA256SUMS.files`
- 归档哈希：`ARCHIVE.sha256`

上传前已检查：

- 未包含 `.git`、`.runtime`、虚拟环境、`node_modules`、构建目录或运行日志。
- 未发现真实 API Key、私钥、凭据文件或公司内部域名。
- 6 个 `*.bundle` 是公开 Python 项目的基准仓库包，保留在快照内。

恢复时先校验 `ARCHIVE.sha256`，再将归档解压到空目录，并使用 `SHA256SUMS.files` 校验 399 个原始文件。
