const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const outDir = path.join(__dirname, 'mermaid_figures');
fs.mkdirSync(outDir, { recursive: true });

const W = 1600;
const H = 1240;

function esc(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function box(x, y, w, h, lines, cls = 'box', fontSize = 18) {
  const lineHeight = fontSize + 7;
  const startY = y + h / 2 - ((lines.length - 1) * lineHeight) / 2 + 6;
  const text = lines
    .map((line, i) => `<tspan x="${x + w / 2}" y="${startY + i * lineHeight}">${esc(line)}</tspan>`)
    .join('');
  return `<rect class="${cls}" x="${x}" y="${y}" width="${w}" height="${h}" rx="4"/>` +
    `<text text-anchor="middle" style="font-size:${fontSize}px">${text}</text>`;
}

function group(x, y, w, h, title) {
  return `<rect class="group" x="${x}" y="${y}" width="${w}" height="${h}" rx="8"/>` +
    `<text x="${x + w / 2}" y="${y + 38}" text-anchor="middle">${esc(title)}</text>`;
}

function arrow(points, dashed = false) {
  const d = points.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ');
  return `<path class="${dashed ? 'dashline' : 'line'}" d="${d}"/>`;
}

function plain(points, dashed = false) {
  const d = points.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ');
  return `<path class="${dashed ? 'dashplain' : 'plain'}" d="${d}"/>`;
}

let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#000"/></marker>
  <style>
    text { font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 18px; fill: #000; }
    .box { fill: #fff; stroke: #000; stroke-width: 1.7; }
    .group { fill: #fff; stroke: #000; stroke-width: 1.7; stroke-dasharray: 9 7; }
    .barrier { fill: #f7f7f7; stroke: #000; stroke-width: 1.7; stroke-dasharray: 6 5; }
    .line { fill: none; stroke: #000; stroke-width: 1.7; marker-end: url(#arrow); }
    .dashline { fill: none; stroke: #000; stroke-width: 1.7; stroke-dasharray: 7 5; marker-end: url(#arrow); }
    .plain { fill: none; stroke: #000; stroke-width: 1.7; }
    .dashplain { fill: none; stroke: #000; stroke-width: 1.7; stroke-dasharray: 7 5; }
  </style>
</defs>
<rect width="${W}" height="${H}" fill="#fff"/>`;

svg += box(500, 35, 600, 75, ['视频 V、问题 Q、任务规则']);
svg += box(500, 150, 600, 82, ['I0 初始状态单元', '形成 E0 与 A0']);
svg += box(500, 275, 600, 82, ['增量证据单元', '取得 ΔE 并冻结 E+']);

svg += group(45, 425, 650, 455, '第一读取域：证据许可域');
svg += box(115, 500, 510, 78, ['P1 可读：Q、规则、E0、ΔE、E+']);
svg += box(115, 620, 510, 78, ['P2 同槽模式观测与证据差分']);
svg += box(115, 740, 510, 78, ['P3 冻结证据差分许可']);
svg += box(195, 825, 350, 62, ['控制存储区：许可摘要'], 'box', 16);

svg += group(905, 425, 650, 455, '第二读取域：候选生成域');
svg += box(975, 500, 510, 78, ['G1 可读：Q 与 E+ 原始视频证据表示']);
svg += box(975, 640, 510, 78, ['G2 独立生成并冻结 A2']);
svg += box(1055, 790, 350, 62, ['候选存储区：A2 摘要'], 'box', 16);

svg += box(735, 505, 130, 270, [
  '逻辑隔离边界',
  'A0 与许可字段',
  '不得进入候选域',
  '候选结果不得',
  '反向影响许可'
], 'barrier', 16);

svg += box(65, 980, 360, 95, ['A0 语义存储区', '两读取域均无读取权限'], 'box', 16);
svg += box(620, 950, 360, 112, ['联合控制单元', 'A2 冻结后首次读取 A0、A2 与许可', '同 E+ 完成迁移—许可配准'], 'box', 16);
svg += box(1130, 970, 400, 82, ['依赖闭包与原子写入门禁']);
svg += box(1130, 1100, 400, 82, ['受限重组、终检或安全状态输出']);

svg += arrow([[800, 110], [800, 150]]);
svg += arrow([[800, 232], [800, 275]]);
svg += plain([[800, 357], [800, 395], [370, 395]]);
svg += plain([[800, 395], [1230, 395]]);
svg += arrow([[370, 395], [370, 500]]);
svg += arrow([[1230, 395], [1230, 500]]);

svg += arrow([[370, 578], [370, 620]]);
svg += arrow([[370, 698], [370, 740]]);
svg += arrow([[370, 818], [370, 825]]);
svg += arrow([[1230, 578], [1230, 640]]);
svg += arrow([[1230, 718], [1230, 790]]);

svg += arrow([[370, 887], [370, 915], [710, 915], [710, 950]], true);
svg += arrow([[1230, 852], [1230, 915], [890, 915], [890, 950]]);
svg += arrow([[425, 1027], [620, 1027]]);
svg += arrow([[980, 1006], [1130, 1006]]);
svg += arrow([[1330, 1052], [1330, 1100]]);

svg += plain([[545, 780], [705, 780]], true);
svg += plain([[705, 768], [705, 792]]);
svg += plain([[895, 605], [865, 605]], true);
svg += plain([[895, 593], [895, 617]]);

svg += `</svg>`;

const svgPath = path.join(outDir, 'fig_001_v2.svg');
const pngPath = path.join(outDir, 'fig_001_v2.png');
fs.writeFileSync(svgPath, svg, 'utf8');

sharp(Buffer.from(svg))
  .png({ compressionLevel: 9 })
  .toFile(pngPath)
  .then(() => console.log(`Rendered ${svgPath} and ${pngPath}`))
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
