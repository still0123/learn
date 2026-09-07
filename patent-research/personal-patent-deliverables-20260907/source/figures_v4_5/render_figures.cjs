const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const outDir = __dirname;
const previewDir = path.join(outDir, 'preview');
fs.mkdirSync(previewDir, { recursive: true });

function esc(value) {
  return String(value)
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
      .tiny { font-size: 14px; }
      .box { fill: #fff; stroke: #000; stroke-width: 1.7; }
      .dash { fill: #fff; stroke: #000; stroke-width: 1.7; stroke-dasharray: 8 6; }
      .line { fill: none; stroke: #000; stroke-width: 1.7; marker-end: url(#arrow); }
      .plain { fill: none; stroke: #000; stroke-width: 1.7; }
      .dashed-line { fill: none; stroke: #000; stroke-width: 1.7; stroke-dasharray: 7 5; marker-end: url(#arrow); }
      .blocked-line { fill: none; stroke: #000; stroke-width: 1.7; stroke-dasharray: 7 5; }
    </style>
  </defs>
  <rect width="${width}" height="${height}" fill="#fff"/>`;
}

function box(x, y, width, height, lines, cls = 'box', textClass = '') {
  const lineHeight = textClass === 'tiny' ? 20 : textClass === 'small' ? 22 : 24;
  const startY = y + height / 2 - ((lines.length - 1) * lineHeight) / 2 + 6;
  const tspans = lines
    .map((line, index) => `<tspan x="${x + width / 2}" y="${startY + index * lineHeight}">${esc(line)}</tspan>`)
    .join('');
  return `<rect class="${cls}" x="${x}" y="${y}" width="${width}" height="${height}" rx="3"/><text class="${textClass}" text-anchor="middle">${tspans}</text>`;
}

function diamond(cx, cy, width, height, lines, textClass = '') {
  const points = `${cx},${cy - height / 2} ${cx + width / 2},${cy} ${cx},${cy + height / 2} ${cx - width / 2},${cy}`;
  const lineHeight = textClass === 'small' ? 22 : 24;
  const startY = cy - ((lines.length - 1) * lineHeight) / 2 + 6;
  const tspans = lines
    .map((line, index) => `<tspan x="${cx}" y="${startY + index * lineHeight}">${esc(line)}</tspan>`)
    .join('');
  return `<polygon class="box" points="${points}"/><text class="${textClass}" text-anchor="middle">${tspans}</text>`;
}

function label(x, y, lines, anchor = 'middle', textClass = '') {
  const lineHeight = textClass === 'tiny' ? 20 : textClass === 'small' ? 22 : 24;
  const tspans = lines.map((line, index) => `<tspan x="${x}" y="${y + index * lineHeight}">${esc(line)}</tspan>`).join('');
  return `<text class="${textClass}" text-anchor="${anchor}">${tspans}</text>`;
}

function arrow(x1, y1, x2, y2, text = '', textX = null, textY = null) {
  const tx = textX ?? (x1 + x2) / 2 + 8;
  const ty = textY ?? (y1 + y2) / 2 - 7;
  const caption = text ? `<text class="small" x="${tx}" y="${ty}">${esc(text)}</text>` : '';
  return `<path class="line" d="M${x1},${y1} L${x2},${y2}"/>${caption}`;
}

function polyArrow(points, text = '', dashed = false, textPoint = null) {
  const d = points.map((point, index) => `${index ? 'L' : 'M'}${point[0]},${point[1]}`).join(' ');
  const point = textPoint ?? points[Math.floor(points.length / 2)];
  const caption = text ? `<text class="small" x="${point[0] + 8}" y="${point[1] - 7}">${esc(text)}</text>` : '';
  return `<path class="${dashed ? 'dashed-line' : 'line'}" d="${d}"/>${caption}`;
}

function blockedLine(x1, y1, x2, y2, text = '') {
  const horizontal = Math.abs(x2 - x1) >= Math.abs(y2 - y1);
  const bar = horizontal
    ? `<path class="plain" d="M${x2},${y2 - 12} L${x2},${y2 + 12}"/>`
    : `<path class="plain" d="M${x2 - 12},${y2} L${x2 + 12},${y2}"/>`;
  const caption = text ? `<text class="small" x="${(x1 + x2) / 2}" y="${(y1 + y2) / 2 - 10}" text-anchor="middle">${esc(text)}</text>` : '';
  return `<path class="blocked-line" d="M${x1},${y1} L${x2},${y2}"/>${bar}${caption}`;
}

function group(x, y, width, height, title) {
  return `<rect class="dash" x="${x}" y="${y}" width="${width}" height="${height}" rx="8"/>${label(x + width / 2, y + 38, [title])}`;
}

function saveSvg(name, content) {
  const svg = `${content}</svg>`;
  fs.writeFileSync(path.join(outDir, name), svg, 'utf8');
  return svg;
}

function fig1() {
  const W = 1200;
  const H = 1900;
  const cx = 600;
  const bw = 640;
  const bh = 78;
  let y = 35;
  let svg = svgStart(W, H);
  const positions = [];
  const add = (lines, height = bh) => {
    const yy = y;
    svg += box(cx - bw / 2, yy, bw, height, lines);
    positions.push({ y: yy, h: height });
    y += height + 34;
    return yy;
  };

  add(['101 获取视频、问题、初始证据快照 E0', '并基于 E0 生成初始答案 A0'], 88);
  add(['102 根据问题与任务规则确定规范化事实槽', '证据许可通道不读取 A0 候选事实值'], 88);
  add(['103 获取 E0 未使用的增量视频证据 ΔE', '并冻结扩展视频证据快照 E+'], 88);
  add(['104 比较事实槽在 E0 与 E+ 下的观测状态', '形成由 ΔE 见证的证据事实差分 ΔObs'], 88);
  add(['105 在 A2 生成前冻结证据差分许可 P', '许可值、状态和映射标识对生成器不可读'], 88);
  add(['106 隔离候选生成器', '仅由问题与 E+ 原始证据表示生成 A2'], 88);
  add(['107 冻结 A2 内容及版本标识', '随后开放 A0、A2 与许可的联合读取'], 88);
  add(['108 在同一 E+ 和同一配置下核验 A0 与 A2', '形成实质答案事实迁移 ΔAns'], 88);
  add(['109 迁移与许可按事实槽、上下文、规范化值', '及 ΔE 时空模态见证逐项配准'], 88);
  add(['110 根据有向事实依赖关系构造语义依赖闭包'], 78);
  const decisionY = y + 72;
  svg += diamond(cx, decisionY, 760, 144, ['111 闭包内全部实质迁移是否唯一配准，', '快照有效且不存在竞争事实？']);
  y = decisionY + 125;
  const branchY = y;
  svg += box(95, branchY, 430, 92, ['112 原子写入闭包的全部目标事实状态']);
  svg += box(675, branchY, 430, 92, ['113 禁止写入闭包的全部候选状态', '并执行 E+ 下安全状态转移']);
  const mergeY = branchY + 155;
  svg += box(cx - bw / 2, mergeY, bw, 92, ['114 仅由已提交目标事实和受支持旧事实重组', '并执行无新增事实终检']);
  const finalY = mergeY + 145;
  svg += box(cx - bw / 2, finalY, bw, 82, ['115 输出答案、证据不足状态或拒绝回答']);

  for (let i = 0; i < positions.length - 1; i += 1) {
    svg += arrow(cx, positions[i].y + positions[i].h, cx, positions[i + 1].y);
  }
  const last = positions[positions.length - 1];
  svg += arrow(cx, last.y + last.h, cx, decisionY - 72);
  svg += polyArrow([[cx - 210, decisionY + 60], [310, branchY]], '是', false, [390, decisionY + 86]);
  svg += polyArrow([[cx + 210, decisionY + 60], [890, branchY]], '否', false, [795, decisionY + 86]);
  svg += polyArrow([[310, branchY + 92], [310, mergeY + 46], [cx - bw / 2, mergeY + 46]]);
  svg += polyArrow([[890, branchY + 92], [890, mergeY + 46], [cx + bw / 2, mergeY + 46]]);
  svg += arrow(cx, mergeY + 92, cx, finalY);
  return saveSvg('fig1_overall_method.svg', svg);
}

function fig2() {
  const W = 1600;
  const H = 1050;
  let svg = svgStart(W, H);
  svg += box(65, 70, 360, 92, ['201 问题 Q、任务规则、E0、ΔE 与 E+']);
  svg += box(1175, 70, 360, 92, ['207 问题 Q 与 E+ 原始证据表示']);
  svg += group(45, 210, 650, 570, '213 证据许可通道');
  svg += group(905, 210, 650, 570, '214 候选生成通道');

  svg += box(115, 285, 510, 82, ['202 E0/E+ 观测抽取与规范化']);
  svg += box(115, 415, 510, 82, ['203 比较观测状态并形成 ΔObs']);
  svg += box(115, 545, 510, 82, ['204 在 A2 前冻结证据差分许可 P']);
  svg += box(195, 665, 350, 92, ['205 许可控制存储区', '许可值—状态—ID—映射键']);

  svg += box(975, 285, 510, 82, ['208 白名单候选生成接口', '拒绝 A0、许可及改写字段']);
  svg += box(975, 415, 510, 82, ['209 候选答案生成器']);
  svg += box(1055, 545, 350, 82, ['210 A2 存储区', '冻结内容与版本摘要']);

  svg += box(70, 840, 310, 86, ['206 A0 语义存储区']);
  svg += box(645, 820, 310, 106, ['211 控制服务', '仅在 A2 冻结后联合读取']);
  svg += box(1220, 840, 310, 86, ['212 双差分配准与闭包提交']);

  svg += arrow(245, 162, 245, 285);
  svg += arrow(1355, 162, 1355, 285);
  svg += arrow(370, 367, 370, 415);
  svg += arrow(370, 497, 370, 545);
  svg += arrow(370, 627, 370, 665);
  svg += arrow(1230, 367, 1230, 415);
  svg += arrow(1230, 497, 1230, 545);
  svg += blockedLine(545, 710, 960, 456, '候选生成器无读取权限');
  svg += blockedLine(225, 840, 225, 780, 'A0 语义无读取权限');
  svg += polyArrow([[370, 757], [370, 800], [700, 800], [700, 820]], 'A2 冻结后', true, [450, 800]);
  svg += polyArrow([[1210, 627], [1210, 790], [900, 790], [900, 820]], 'A2 摘要', false, [1090, 790]);
  svg += arrow(380, 883, 645, 873);
  svg += arrow(955, 873, 1220, 883);
  return saveSvg('fig2_dual_channel_isolation.svg', svg);
}

function fig3() {
  const W = 1500;
  const H = 1180;
  const cx = 750;
  let svg = svgStart(W, H);
  svg += box(490, 40, 520, 78, ['301 由问题与任务规则形成事实槽模式']);
  svg += box(490, 160, 520, 78, ['302 在 E0 下形成初始观测状态 O0']);
  svg += box(490, 280, 520, 88, ['303 从 E0 未使用的 ΔE 形成 E+ 观测状态 O+']);
  svg += box(440, 410, 620, 88, ['304 比较 O0/O+ 并绑定 ΔE 时空模态见证']);
  svg += diamond(cx, 615, 720, 135, ['305 是否存在由 ΔE 引起的', '实质事实差分？']);
  svg += box(75, 730, 390, 92, ['306 不产生写入许可', '继续取证或保持安全状态']);
  svg += diamond(1000, 775, 610, 130, ['307 同一事实槽与上下文中', '是否存在竞争事实？']);
  svg += box(745, 920, 360, 88, ['308 标记竞争歧义', '不产生正向写入许可']);
  svg += box(1150, 920, 300, 88, ['309 生成证据差分许可记录']);
  svg += box(1125, 1050, 350, 88, ['310 写入控制存储区', '并冻结许可摘要']);

  svg += arrow(cx, 118, cx, 160);
  svg += arrow(cx, 238, cx, 280);
  svg += arrow(cx, 368, cx, 410);
  svg += arrow(cx, 498, cx, 547);
  svg += polyArrow([[cx - 270, 655], [270, 730]], '否', false, [390, 686]);
  svg += polyArrow([[cx + 270, 655], [1000, 710]], '是', false, [890, 686]);
  svg += polyArrow([[850, 832], [925, 920]], '是');
  svg += polyArrow([[1150, 832], [1300, 920]], '否');
  svg += arrow(1300, 1008, 1300, 1050);

  svg += label(130, 965, ['311 冻结及联合读取时序']);
  svg += `<path class="plain" d="M120,1085 L890,1085"/>`;
  const points = [210, 415, 620, 825];
  const pointLabels = [
    ['t_p', '许可冻结'],
    ['t_s', '启动 A2'],
    ['t_a', 'A2 冻结'],
    ['t_j', '联合读取']
  ];
  points.forEach((x, index) => {
    svg += `<path class="plain" d="M${x},1068 L${x},1102"/>`;
    svg += label(x, 1035, [pointLabels[index][0], pointLabels[index][1]], 'middle', 'small');
  });
  svg += label(510, 1150, ['312  时序条件：t_p < t_s < t_a < t_j'], 'middle', 'small');
  return saveSvg('fig3_permit_freeze_sequence.svg', svg);
}

function fig4() {
  const W = 1600;
  const H = 1050;
  let svg = svgStart(W, H);
  svg += group(50, 55, 630, 500, '证据许可通道');
  svg += group(920, 55, 630, 500, '答案事实通道');
  svg += box(105, 145, 235, 88, ['401 E0 下观测', '状态 O0']);
  svg += box(390, 145, 235, 88, ['402 E+ 下观测', '状态 O+']);
  svg += box(185, 305, 360, 92, ['403 证据事实差分 ΔObs']);
  svg += box(135, 450, 460, 92, ['404 证据差分许可 P', '事实槽—上下文—值—ΔE见证']);

  svg += box(975, 145, 235, 88, ['405 A0 在 E+ 下', '事实集合 F0+']);
  svg += box(1260, 145, 235, 88, ['406 A2 在 E+ 下', '事实集合 F2+']);
  svg += box(1055, 305, 360, 92, ['407 答案事实差分 ΔAns']);
  svg += box(1005, 450, 460, 92, ['408 实质答案事实迁移', '新增—替换—撤回']);

  svg += box(570, 625, 460, 80, ['409 迁移—许可逐项配准']);
  svg += box(220, 770, 340, 80, ['410 事实槽及实体或事件一致']);
  svg += box(630, 770, 340, 80, ['411 谓词、限定上下文和值相容']);
  svg += box(1040, 770, 340, 80, ['412 ΔE见证与E0/E+快照一致']);
  svg += diamond(800, 935, 620, 115, ['413 是否存在唯一有效配准？']);
  svg += box(85, 915, 350, 88, ['414 标记迁移已授权', '进入闭包暂存']);
  svg += box(1165, 915, 350, 88, ['415 标记迁移未授权', '禁止写入目标状态']);

  svg += arrow(222, 233, 310, 305);
  svg += arrow(508, 233, 420, 305);
  svg += arrow(365, 397, 365, 450);
  svg += arrow(1092, 233, 1180, 305);
  svg += arrow(1378, 233, 1290, 305);
  svg += arrow(1235, 397, 1235, 450);
  svg += polyArrow([[365, 542], [365, 595], [690, 625]]);
  svg += polyArrow([[1235, 542], [1235, 595], [910, 625]]);
  svg += polyArrow([[800, 705], [390, 770]]);
  svg += arrow(800, 705, 800, 770);
  svg += polyArrow([[800, 705], [1210, 770]]);
  svg += polyArrow([[390, 850], [390, 875], [800, 875], [800, 878]]);
  svg += arrow(800, 850, 800, 878);
  svg += polyArrow([[1210, 850], [1210, 875], [800, 875], [800, 878]]);
  svg += polyArrow([[560, 955], [435, 955]], '是', false, [480, 940]);
  svg += polyArrow([[1040, 955], [1165, 955]], '否', false, [1080, 940]);
  return saveSvg('fig4_double_delta_matching.svg', svg);
}

function fig5() {
  const W = 1600;
  const H = 1500;
  let svg = svgStart(W, H);
  svg += group(45, 45, 450, 425, '517 上游只读证明上下文');
  svg += group(650, 45, 900, 425, '518 下游事务写入闭包');
  svg += box(105, 145, 330, 88, ['501 商品身份前提']);
  svg += box(105, 315, 330, 88, ['502 促销时间前提']);
  svg += box(720, 135, 300, 95, ['503 实质迁移', '促销价格']);
  svg += box(1110, 135, 300, 95, ['504 下游派生迁移', '优惠金额']);
  svg += box(1110, 315, 300, 95, ['505 下游结论迁移']);
  svg += box(585, 490, 430, 100, ['506 闭包记录', '写入集—证明引用集—迁移许可映射']);

  svg += arrow(435, 189, 720, 182);
  svg += arrow(435, 359, 720, 205);
  svg += arrow(1020, 182, 1110, 182);
  svg += arrow(1260, 230, 1260, 315);
  svg += polyArrow([[730, 490], [730, 330], [870, 230]], '许可约束', true);
  svg += polyArrow([[930, 490], [1080, 440], [1260, 410]], '许可约束', true);

  svg += diamond(800, 700, 760, 130, ['507 闭包内全部迁移是否唯一获许可，', '且快照有效、无竞争事实？']);
  svg += box(95, 815, 430, 90, ['508 原子提交闭包全部目标状态']);
  svg += box(1075, 815, 430, 90, ['509 丢弃闭包全部候选写入']);
  svg += diamond(1290, 1010, 480, 110, ['510 E+ 下旧事实状态？'], 'small');
  svg += box(505, 1110, 300, 82, ['511 保留受支持旧事实']);
  svg += box(865, 1110, 340, 82, ['512 继续取证或设为不确定']);
  svg += box(1265, 1110, 290, 82, ['513 撤回冲突旧事实']);
  svg += diamond(1000, 1285, 520, 110, ['514 必填事实槽', '是否可唯一填充？'], 'small');
  svg += box(330, 1400, 540, 70, ['515 仅由已提交或保留事实受限重组并输出'], 'box', 'small');
  svg += box(1110, 1400, 390, 70, ['516 输出证据不足状态或拒答'], 'box', 'small');

  svg += arrow(800, 590, 800, 635);
  svg += polyArrow([[570, 750], [310, 815]], '是', false, [430, 775]);
  svg += polyArrow([[1030, 750], [1290, 815]], '否', false, [1115, 775]);
  svg += polyArrow([[310, 905], [310, 1435], [330, 1435]]);
  svg += arrow(1290, 905, 1290, 955);
  svg += polyArrow([[1135, 1050], [655, 1110]], '支持', false, [900, 1060]);
  svg += polyArrow([[1290, 1065], [1035, 1110]], '证据不足', false, [1150, 1080]);
  svg += polyArrow([[1445, 1050], [1410, 1110]], '冲突', false, [1465, 1075]);
  svg += polyArrow([[655, 1192], [655, 1230], [900, 1230], [900, 1235]]);
  svg += polyArrow([[1035, 1192], [1035, 1235]]);
  svg += polyArrow([[1410, 1192], [1410, 1230], [1100, 1230], [1100, 1235]]);
  svg += polyArrow([[780, 1335], [600, 1400]], '是', false, [690, 1360]);
  svg += polyArrow([[1220, 1335], [1305, 1400]], '否', false, [1240, 1360]);
  return saveSvg('fig5_closure_state_control.svg', svg);
}

function fig6() {
  const W = 1500;
  const H = 1000;
  let svg = svgStart(W, H);
  const x = 455;
  const width = 590;
  const height = 76;
  const gap = 34;
  const modules = [
    ['601 初始状态生成单元', '获取视频、问题、E0并生成A0'],
    ['602 增量证据获取单元', '取得E0未用ΔE并冻结E+'],
    ['603 证据许可单元', '形成并冻结候选值盲化的证据差分许可'],
    ['604 隔离生成单元', '仅由问题与E+原始证据表示生成A2'],
    ['605 答案差分单元', '同E+形成A0至A2实质事实迁移'],
    ['606 迁移配准单元', '按槽、上下文、值和ΔE见证逐项配准'],
    ['607 闭包控制单元', '闭包原子写入或禁止候选状态'],
    ['608 受限输出单元', '输出答案、不确定状态或拒答']
  ];
  const ys = [];
  modules.forEach((module, index) => {
    const y = 35 + index * (height + gap);
    ys.push(y);
    svg += box(x, y, width, height, module);
    if (index > 0) {
      svg += arrow(x + width / 2, ys[index - 1] + height, x + width / 2, y);
    }
  });
  svg += box(60, 290, 300, 130, ['609 存储器', '证据快照、许可、A0/A2', '迁移、闭包及审计日志']);
  svg += box(1140, 290, 300, 130, ['610 处理器', '执行各功能单元']);
  svg += box(65, 600, 360, 145, ['611 访问控制与接口校验单元', '隔离许可、A0语义区', '及候选生成输入']);
  svg += polyArrow([[360, 355], [455, 355]], '数据');
  svg += polyArrow([[1140, 355], [1045, 355]], '控制');
  svg += polyArrow([[425, 650], [455, 650]], '权限控制', true);
  svg += polyArrow([[425, 690], [440, 690], [440, 475], [455, 475]], '', true);
  return saveSvg('fig6_device_modules.svg', svg);
}

async function render() {
  const figures = [
    ['fig1_overall_method.svg', fig1()],
    ['fig2_dual_channel_isolation.svg', fig2()],
    ['fig3_permit_freeze_sequence.svg', fig3()],
    ['fig4_double_delta_matching.svg', fig4()],
    ['fig5_closure_state_control.svg', fig5()],
    ['fig6_device_modules.svg', fig6()]
  ];

  for (const [name, svg] of figures) {
    const pngName = name.replace('.svg', '.png');
    await sharp(Buffer.from(svg))
      .png({ compressionLevel: 9 })
      .toFile(path.join(previewDir, pngName));
  }
  console.log(`Rendered ${figures.length} SVG patent figures and PNG previews in ${outDir}`);
}

render().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
