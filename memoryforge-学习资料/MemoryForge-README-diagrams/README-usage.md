# MemoryForge README 图片使用建议

本目录包含 6 张 1600×900（16:9）图片，每张同时提供：

- `PNG`：建议直接用于 GitHub README，跨浏览器显示稳定。
- `SVG`：用于后续改字、无损缩放或导出更高分辨率版本。

> 图 2、图 3 是依据当前 Portal 信息架构制作的**示例数据高保真模拟图**，不是伪装成真实运行数据的截图。

## 推荐出现顺序

### 1. README 首屏：产品主图

```md
![MemoryForge：把多来源资料编译成本地技术 Wiki](assets/01-memoryforge-hero.png)
```

文件：`01-memoryforge-hero.png`

### 2. 产品形态：Portal 首页

```md
![MemoryForge 本地知识门户首页示意图](assets/02-memoryforge-portal-home.png)
```

文件：`02-memoryforge-portal-home.png`

### 3. 核心差异化：ChangeSet 审核页

```md
![MemoryForge ChangeSet 审核与 Diff 预览](assets/03-memoryforge-changeset-review.png)
```

文件：`03-memoryforge-changeset-review.png`

图中刻意将 `approve` 与 `apply` 画成两个动作：先记录独立授权，再写入 Wiki 与 Git。

### 4. “工作原理”章节：知识发布链

```md
![MemoryForge 知识发布链](assets/04-memoryforge-publish-pipeline.png)
```

文件：`04-memoryforge-publish-pipeline.png`

可替换 README 中现有的发布链 Mermaid。

### 5. 查询说明：渐进式查询与拒答链

```md
![MemoryForge 渐进式查询与拒答流程](assets/05-memoryforge-query-pipeline.png)
```

文件：`05-memoryforge-query-pipeline.png`

图中包含 `INDEX/FTS5` 路由、默认最多 3 个 Wiki 页面、support score 门禁、`unknown` 拒答和按需 L3 原文核验。

### 6. “和普通 RAG 的区别”章节：对比卡片

```md
![MemoryForge 与普通 RAG 的区别](assets/06-memoryforge-vs-rag.png)
```

文件：`06-memoryforge-vs-rag.png`

## 建议的 README 排列

1. 标题与一句话介绍
2. 图 1 产品主图
3. “一眼看懂”
4. 图 2 Portal 首页
5. “核心产品”
6. 图 3 审核页
7. “和普通 RAG 的区别”
8. 图 6 对比卡片
9. “工作原理”
10. 图 4 发布链
11. 查询机制说明
12. 图 5 查询链

## 视觉规范

- 主色：`#1664FF`
- 强调蓝：`#0B55E8`
- 薄荷绿：`#18A980`
- 背景：`#F5F8FF`
- 正文：`#1F2329`
- 字体回退：Noto Sans CJK SC / PingFang SC / Microsoft YaHei / sans-serif
