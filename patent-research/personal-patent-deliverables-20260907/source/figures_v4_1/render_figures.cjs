const fs = require('fs');
const path = require('path');

const outDir = __dirname;

function esc(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function svgStart(width, height) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#000"/></marker>
    <style>
      text { font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 18px; fill: #000; }
      .small { font-size: 16px; }
      .box { fill: #fff; stroke: #000; stroke-width: 1.7; }
      .dash { fill: #fff; stroke: #000; stroke-width: 1.7; stroke-dasharray: 8 6; }
      .line { fill: none; stroke: #000; stroke-width: 1.7; marker-end: url(#arrow); }
      .plain { fill: none; stroke: #000; stroke-width: 1.7; }
      .dashed-line { fill: none; stroke: #000; stroke-width: 1.7; stroke-dasharray: 7 5; marker-end: url(#arrow); }
    </style>
  </defs>
  <rect width="${width}" height="${height}" fill="#fff"/>`;
}

function box(x, y, w, h, lines, cls = 'box') {
  const lineHeight = 24;
  const startY = y + h / 2 - ((lines.length - 1) * lineHeight) / 2 + 6;
  const tspans = lines.map((line, i) => `<tspan x="${x + w / 2}" y="${startY + i * lineHeight}">${esc(line)}</tspan>`).join('');
  return `<rect class="${cls}" x="${x}" y="${y}" width="${w}" height="${h}" rx="3"/><text text-anchor="middle">${tspans}</text>`;
}

function diamond(cx, cy, w, h, lines) {
  const pts = `${cx},${cy - h / 2} ${cx + w / 2},${cy} ${cx},${cy + h / 2} ${cx - w / 2},${cy}`;
  const lineHeight = 23;
  const startY = cy - ((lines.length - 1) * lineHeight) / 2 + 6;
  const tspans = lines.map((line, i) => `<tspan x="${cx}" y="${startY + i * lineHeight}">${esc(line)}</tspan>`).join('');
  return `<polygon class="box" points="${pts}"/><text text-anchor="middle">${tspans}</text>`;
}

function arrow(x1, y1, x2, y2, label = '') {
  const text = label ? `<text class="small" x="${(x1 + x2) / 2 + 8}" y="${(y1 + y2) / 2 - 7}">${esc(label)}</text>` : '';
  return `<path class="line" d="M${x1},${y1} L${x2},${y2}"/>${text}`;
}

function polyArrow(points, label = '', dashed = false) {
  const d = points.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ');
  const mid = points[Math.floor(points.length / 2)];
  const text = label ? `<text class="small" x="${mid[0] + 8}" y="${mid[1] - 7}">${esc(label)}</text>` : '';
  return `<path class="${dashed ? 'dashed-line' : 'line'}" d="${d}"/>${text}`;
}

function save(name, content) {
  fs.writeFileSync(path.join(outDir, name), content, 'utf8');
}

function fig1() {
  const W = 1200, H = 1900, cx = 600, bw = 600, bh = 72, gap = 38;
  let y = 40;
  let s = svgStart(W, H);
  const addBox = (lines) => { const yy = y; s += box(cx - bw / 2, yy, bw, bh, lines); y += bh + gap; return yy; };
  const ys = [];
  ys.push(addBox(['101 获取视频与用户问题']));
  ys.push(addBox(['102 基于初始证据集 E0 生成初始答案 A0']));
  ys.push(addBox(['103 拆分 A0 原子声明并确定支持状态']));
  const dy1 = y + 5; s += diamond(cx, dy1 + 60, 650, 120, ['104 必填语义槽是否存在', '无声明或非支持状态？']); y += 170;
  ys.push(addBox(['106 从 E0 未覆盖位置获取 ΔE']));
  ys.push(addBox(['107 冻结 E+ = E0 ∪ ΔE']));
  ys.push(addBox(['108 仅由问题与 E+ 生成 A2', '生成请求不含 A0 文本']));
  ys.push(addBox(['109 同一 E+、同一配置核验 A0 与 A2']));
  ys.push(addBox(['110 建立声明迁移记录', '事实槽—差异槽—见证ID—目标状态']));
  ys.push(addBox(['111 构建下游写入闭包与上游只读证明上下文']));
  const dy2 = y + 5; s += diamond(cx, dy2 + 60, 680, 120, ['112 迁移、见证与闭包', '一致性条件是否全部满足？']); y += 170;
  const branchY = y;
  s += box(120, branchY, 400, 82, ['113 原子提交闭包候选目标状态']);
  s += box(680, branchY, 400, 82, ['114 不写入候选状态并执行', 'E+ 下安全状态转移']);
  y += 140;
  s += box(cx - bw / 2, y, bw, 82, ['115 仅由已提交或保留状态重组', '并执行无新增声明终检']);
  const finalY = y + 145;
  s += box(cx - bw / 2, finalY, bw, 82, ['116 输出答案、结构化证据不足标识或拒答']);

  for (let i = 0; i < 2; i++) s += arrow(cx, ys[i] + bh, cx, ys[i + 1]);
  s += arrow(cx, ys[2] + bh, cx, dy1);
  s += arrow(cx, dy1 + 120, cx, ys[3], '是');
  s += polyArrow([[cx - 325, dy1 + 60], [80, dy1 + 60], [80, y + 41], [cx - bw / 2, y + 41]], '否');
  for (let i = 3; i < ys.length - 1; i++) s += arrow(cx, ys[i] + bh, cx, ys[i + 1]);
  s += arrow(cx, ys[ys.length - 1] + bh, cx, dy2);
  s += polyArrow([[cx - 200, dy2 + 105], [320, branchY]], '是');
  s += polyArrow([[cx + 200, dy2 + 105], [880, branchY]], '否');
  s += polyArrow([[320, branchY + 82], [320, y + 41], [cx - bw / 2, y + 41]]);
  s += polyArrow([[880, branchY + 82], [880, y + 41], [cx + bw / 2, y + 41]]);
  s += arrow(cx, y + 82, cx, finalY);
  s += '</svg>';
  save('fig1_overall_method.svg', s);
}

function fig2() {
  const W = 1500, H = 820;
  let s = svgStart(W, H);
  s += box(60, 80, 340, 86, ['201 原始视频时间轴']);
  s += box(60, 240, 340, 86, ['202 E0 已覆盖片段']);
  s += box(60, 430, 340, 86, ['203 E0 未覆盖片段']);
  s += box(500, 210, 360, 105, ['204 初始证据集合 E0', '帧、OCR、ASR及位置']);
  s += box(500, 410, 360, 105, ['207 增量视频证据 ΔE', '帧、区域或语音时间段']);
  s += box(950, 300, 430, 120, ['208 不可变扩展证据快照', 'E+ = E0 ∪ ΔE']);
  s += box(950, 570, 430, 115, ['209 A0 与 A2 使用同一 E+', '及同一核验配置']);
  s += box(500, 40, 360, 92, ['205 A0及其原子声明']);
  s += box(950, 65, 430, 92, ['206 声明支持缺口与取证需求']);
  s += arrow(230, 166, 230, 240);
  s += arrow(230, 166, 230, 430);
  s += arrow(400, 283, 500, 263);
  s += arrow(400, 473, 500, 463);
  s += arrow(680, 210, 680, 132);
  s += arrow(860, 86, 950, 111);
  s += polyArrow([[1165, 157], [1440, 157], [1440, 740], [230, 740], [230, 516]]);
  s += `<text class="small" x="1190" y="728">限定未覆盖位置</text>`;
  s += arrow(860, 263, 950, 340);
  s += arrow(860, 463, 950, 380);
  s += arrow(1165, 420, 1165, 570);
  s += '</svg>';
  save('fig2_evidence_snapshots.svg', s);
}

function fig3() {
  const W = 1500, H = 900;
  let s = svgStart(W, H);
  s += `<rect class="dash" x="55" y="70" width="420" height="700" rx="8"/><text x="265" y="110" text-anchor="middle">307 上游只读证明上下文</text>`;
  s += `<rect class="dash" x="690" y="70" width="730" height="700" rx="8"/><text x="1055" y="110" text-anchor="middle">308 下游事务写入闭包</text>`;
  s += box(115, 190, 300, 100, ['301 商品身份前提']);
  s += box(115, 450, 300, 100, ['303 促销时间前提']);
  s += box(760, 250, 300, 110, ['302 实质变化声明', '价格槽']);
  s += box(1080, 250, 270, 110, ['304 下游声明', '优惠条件']);
  s += box(1080, 500, 270, 110, ['305 下游声明', '最终结论']);
  s += box(560, 690, 420, 105, ['306 迁移记录', '事实槽—必要差异槽—ΔE见证ID—目标状态']);
  s += arrow(415, 240, 760, 285);
  s += arrow(415, 500, 760, 325);
  s += arrow(1060, 305, 1080, 305);
  s += arrow(1215, 360, 1215, 500);
  s += polyArrow([[770, 690], [770, 560], [910, 360]], '见证约束', true);
  s += polyArrow([[850, 690], [1050, 650], [1215, 610]], '见证约束', true);
  s += '</svg>';
  save('fig3_dependency_closure.svg', s);
}

function fig4() {
  const W = 1500, H = 1200;
  let s = svgStart(W, H);
  s += box(520, 45, 460, 80, ['401 获取 A0 支持状态']);
  s += diamond(750, 230, 600, 125, ['402 是否存在必填槽', '无声明或非支持状态？']);
  s += box(520, 345, 460, 80, ['403 获取 ΔE 并冻结 E+']);
  s += box(520, 475, 460, 95, ['404 生成 A2 并在同一 E+ 下', '配对核验 A0/A2']);
  s += box(520, 620, 460, 95, ['405 建立迁移记录及闭包']);
  s += diamond(750, 830, 620, 125, ['406 闭包接受条件', '是否全部满足？']);
  s += box(80, 970, 380, 88, ['407 原子提交闭包']);
  s += box(560, 970, 380, 88, ['408 执行 E+ 下安全状态转移']);
  s += box(1040, 970, 380, 88, ['409 无补证时保留受支持 A0']);
  s += box(500, 1100, 500, 78, ['410 受限重组并输出或拒答']);
  s += arrow(750, 125, 750, 168);
  s += arrow(750, 293, 750, 345, '是');
  s += arrow(750, 425, 750, 475);
  s += arrow(750, 570, 750, 620);
  s += arrow(750, 715, 750, 767);
  s += polyArrow([[600, 885], [270, 970]], '是');
  s += polyArrow([[900, 885], [750, 970]], '否');
  s += polyArrow([[1050, 230], [1230, 230], [1230, 970]], '否');
  s += polyArrow([[270, 1058], [270, 1139], [500, 1139]]);
  s += arrow(750, 1058, 750, 1100);
  s += polyArrow([[1230, 1058], [1230, 1139], [1000, 1139]]);
  s += '</svg>';
  save('fig4_state_transition.svg', s);
}

function fig5() {
  const W = 1500, H = 1200;
  let s = svgStart(W, H);
  const x = 480, w = 540, h = 82, gap = 42;
  const items = [
    ['501 输入获取模块', '视频、问题和 E0'],
    ['502 初始答案与支持评估模块', 'A0、原子声明及支持状态'],
    ['503 增量证据获取模块', '未覆盖位置 ΔE 与 E+'],
    ['504 独立候选生成模块', '仅由问题和 E+ 生成 A2'],
    ['505 映射与闭包构造模块', '迁移记录、写入闭包和证明上下文'],
    ['506 见证核验与提交控制模块', '同 E+ 复评、提交或安全状态'],
    ['507 受约束输出模块', '重组与无新增声明终检']
  ];
  const ys = [];
  items.forEach((it, i) => { const y = 40 + i * (h + gap); ys.push(y); s += box(x, y, w, h, it); if (i) s += arrow(x + w / 2, ys[i - 1] + h, x + w / 2, y); });
  s += box(80, 340, 270, 105, ['508 存储器', '保存证据快照、声明与状态']);
  s += box(1150, 340, 270, 105, ['509 处理器', '执行各功能模块']);
  s += polyArrow([[350, 392], [480, 392]], '数据');
  s += polyArrow([[1150, 392], [1020, 392]], '控制');
  s += '</svg>';
  save('fig5_device_modules.svg', s);
}

fig1();
fig2();
fig3();
fig4();
fig5();
console.log('Rendered 5 local SVG patent figures in', outDir);
