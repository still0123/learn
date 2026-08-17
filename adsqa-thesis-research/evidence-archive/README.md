# AdsQA Research Evidence Archive

完整研究证据未写入 Git 历史，而是保存在私有 GitHub Release：

- Release: [adsqa-evidence-20260817](https://github.com/still0123/learn/releases/tag/adsqa-evidence-20260817)
- 文件数：5,469
- 原始大小：约 515 MiB
- 压缩归档：约 191 MiB

## 内容

| 资产 | 内容 |
|---|---|
| `artifacts.tar.zst` | 实验结果、预测、裁判记录、脚本快照和审计材料 |
| `remote_staging.tar.zst` | 远端实验暂存代码、图片和结构化结果 |
| `local_review.tar.zst` | 本地人工复核图片与标注记录 |
| `inventory.tsv` | 文件分类、相对路径、字节数和逐文件 SHA256 |
| `SOURCE_SHA256SUMS` | 恢复后逐文件校验清单 |
| `SHA256SUMS` | Release 交付文件校验清单 |

## 下载与验证

```bash
gh release download adsqa-evidence-20260817 \
  --repo still0123/learn \
  --dir adsqa-evidence-20260817

cd adsqa-evidence-20260817
shasum -a 256 -c SHA256SUMS
```

恢复命令见 Release 中的 `README.md`。该归档包含机器裁判和审阅材料，仅用于私有灾备、复现与审计，不应随仓库转为公开。
