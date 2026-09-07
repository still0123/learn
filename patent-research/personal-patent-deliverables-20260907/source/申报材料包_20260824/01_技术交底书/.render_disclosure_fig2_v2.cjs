const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const outDir = path.join(__dirname, 'mermaid_figures');
fs.mkdirSync(outDir, { recursive: true });

const W = 1600;
const H = 1780;

function esc(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function box(x, y, w, h, lines, fontSize = 18) {
  const lh = fontSize + 7;
  const startY = y + h / 2 - ((lines.length - 1) * lh) / 2 + 6;
  const text = lines.map((line, i) => `<tspan x="${x + w / 2}" y="${startY + i * lh}">${esc(line)}</tspan>`).join('');
  return `<rect class="box" x="${x}" y="${y}" width="${w}" height="${h}" rx="4"/>` +
    `<text text-anchor="middle" style="font-size:${fontSize}px">${text}</text>`;
}

function diamond(cx, cy, w, h, lines, fontSize = 18) {
  const points = `${cx},${cy - h / 2} ${cx + w / 2},${cy} ${cx},${cy + h / 2} ${cx - w / 2},${cy}`;
  const lh = fontSize + 7;
  const startY = cy - ((lines.length - 1) * lh) / 2 + 6;
  const text = lines.map((line, i) => `<tspan x="${cx}" y="${startY + i * lh}">${esc(line)}</tspan>`).join('');
  return `<polygon class="box" points="${points}"/>` +
    `<text text-anchor="middle" style="font-size:${fontSize}px">${text}</text>`;
}

function arrow(points) {
  const d = points.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ');
  return `<path class="line" d="${d}"/>`;
}

function label(x, y, text, anchor = 'middle') {
  return `<text x="${x}" y="${y}" text-anchor="${anchor}" style="font-size:16px">${esc(text)}</text>`;
}

let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#000"/></marker>
  <style>
    text { font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif; fill: #000; }
    .box { fill: #fff; stroke: #000; stroke-width: 1.8; }
    .line { fill: none; stroke: #000; stroke-width: 1.8; marker-end: url(#arrow); }
  </style>
</defs>
<rect width="${W}" height="${H}" fill="#fff"/>`;

const xMain = 520;
const wMain = 600;
svg += box(xMain, 35, wMain, 72, ['S1 获取 V、Q 并形成 E0、A0']);
svg += box(xMain, 140, wMain, 72, ['S2 由 Q 和任务规则确定事实槽模式']);
svg += box(xMain, 245, wMain, 82, ['S3 取得相对 E0 未使用的 ΔE', '并冻结 E+']);
svg += box(xMain, 365, wMain, 82, ['S4 第一读取域比较 E0/E+ 观测状态']);
svg += diamond(820, 545, 720, 130, ['S5 是否存在由 ΔE 导致的', '实质证据差分']);

svg += diamond(265, 720, 430, 115, ['S6 是否仍有取证预算']);
svg += box(65, 875, 400, 90, ['S17 输出保留、不确定', '或拒答状态']);

svg += box(850, 675, 620, 82, ['S7 生成许可、冻结摘要并记录 t_p']);
svg += box(850, 790, 620, 82, ['S8 在 t_p 后独立生成 A2，记录 t_s']);
svg += box(850, 905, 620, 82, ['S9 冻结 A2 摘要及版本，记录 t_a']);
svg += box(850, 1020, 620, 82, ['S10 在 t_a 后首次联合读取，记录 t_j']);
svg += box(850, 1135, 620, 82, ['S11 在同一 E+ 下规范化并核验 A0/A2']);
svg += box(850, 1250, 620, 82, ['S12 形成答案事实迁移并逐项唯一配准许可']);
svg += box(850, 1365, 620, 82, ['S13 构造下游状态写入闭包', '及上游证明引用集']);
svg += diamond(1160, 1550, 680, 130, ['S14 闭包内全部迁移通过', '且不存在竞争事实']);
svg += box(540, 1670, 480, 82, ['S15 原子写入、受限重组', '及无新增事实终检']);
svg += box(1100, 1670, 430, 82, ['S16 整闭包禁写并进入安全状态机']);

svg += arrow([[820, 107], [820, 140]]);
svg += arrow([[820, 212], [820, 245]]);
svg += arrow([[820, 327], [820, 365]]);
svg += arrow([[820, 447], [820, 480]]);

svg += arrow([[460, 545], [265, 545], [265, 662]]);
svg += label(355, 530, '否');
svg += arrow([[1180, 545], [1210, 545], [1210, 655], [1160, 655], [1160, 675]]);
svg += label(1198, 530, '是');

svg += arrow([[265, 778], [265, 875]]);
svg += label(280, 830, '无');
svg += arrow([[50, 720], [30, 720], [30, 286], [520, 286]]);
svg += label(42, 700, '有', 'start');

svg += arrow([[1160, 757], [1160, 790]]);
svg += arrow([[1160, 872], [1160, 905]]);
svg += arrow([[1160, 987], [1160, 1020]]);
svg += arrow([[1160, 1102], [1160, 1135]]);
svg += arrow([[1160, 1217], [1160, 1250]]);
svg += arrow([[1160, 1332], [1160, 1365]]);
svg += arrow([[1160, 1447], [1160, 1485]]);

svg += arrow([[820, 1550], [780, 1550], [780, 1670]]);
svg += label(790, 1535, '是');
svg += arrow([[1500, 1550], [1540, 1550], [1540, 1650], [1315, 1650], [1315, 1670]]);
svg += label(1518, 1535, '否');

svg += `</svg>`;

const svgPath = path.join(outDir, 'fig_002_v2.svg');
const pngPath = path.join(outDir, 'fig_002_v2.png');
fs.writeFileSync(svgPath, svg, 'utf8');

sharp(Buffer.from(svg))
  .png({ compressionLevel: 9 })
  .toFile(pngPath)
  .then(() => console.log(`Rendered ${svgPath} and ${pngPath}`))
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
