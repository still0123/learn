# Safe historical zsh backup archive

This archive preserves two historical `.zshrc` backup files from the home directory:

- `.zshrc.bak.20260702204908`
- `.zshrc.bak.20260702205145`

Both files were scanned for company/internal-platform markers, private keys, Tokens, recovery codes, passwords, and high-confidence credential formats before upload; no such marker was found. The current `.zshrc`, shell/Git/npm configuration files, and the one historical backup that contains a company marker remain local and are not included.

These are inactive historical backups rather than the current shell startup file. After remote verification, their local originals may be kept in reversible `已备份待删除` staging.
