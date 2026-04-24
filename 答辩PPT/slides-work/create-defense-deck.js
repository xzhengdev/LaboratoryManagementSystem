const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const {
  autoFontSize,
  imageSizingCrop,
  imageSizingContain,
  svgToDataUri,
  safeOuterShadow,
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers");

const pptx = new pptxgen();
pptx.defineLayout({ name: "DEFENSE_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "DEFENSE_WIDE";
pptx.author = "Codex";
pptx.subject = "支持跨校区协作的分布式实验室管理系统毕业答辩";
pptx.title = "支持跨校区协作的分布式实验室管理系统设计与实现";
pptx.company = "毕业设计";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};

const W = 13.333;
const H = 7.5;
const FONT = "Microsoft YaHei";
const MONO = "Consolas";
const C = {
  paper: "F7F4EC",
  paper2: "EEF3EE",
  ink: "132A34",
  muted: "627279",
  faint: "D9E1DC",
  white: "FFFFFF",
  teal: "174E63",
  tealDark: "113A48",
  blue: "2D6F8F",
  sage: "7BA36D",
  gold: "C28A3A",
  rust: "B75F32",
  red: "B9473F",
};

const projectRoot = path.resolve(__dirname, "..", "..");
const outDir = path.resolve(__dirname, "..");
const outPptx = path.join(outDir, "支持跨校区协作的分布式实验室管理系统-毕业答辩.pptx");
const outNotes = path.join(outDir, "答辩PPT讲稿.md");
const campusDir = path.join(projectRoot, "frontend", "static", "campuses");
const assets = {
  logo: path.join(projectRoot, "frontend", "static", "logo.png"),
  cover: path.join(campusDir, "zhongyangminzudaxue.jpg"),
  haidian: path.join(campusDir, "haidian.jpg"),
  fengtai: path.join(campusDir, "fengtai.jpg"),
  hainan: path.join(campusDir, "hainan.jpg"),
  mainCampus: path.join(campusDir, "zhongyangminzudaxue.jpg"),
};

function addBg(slide, color = C.paper) {
  slide.background = { color };
}

function addText(slide, text, x, y, w, h, opts = {}) {
  const fontSize = opts.auto
    ? fitText(text, {
        x,
        y,
        w,
        h,
        fontSize: opts.fontSize || 16,
        minFontSize: opts.minFontSize || 8,
        maxFontSize: opts.maxFontSize || opts.fontSize || 16,
        bold: opts.bold,
      })
    : opts.fontSize || 16;
  slide.addText(text, {
    x,
    y,
    w,
    h,
    margin: opts.margin === undefined ? 0 : opts.margin,
    fontFace: opts.fontFace || FONT,
    fontSize,
    bold: !!opts.bold,
    color: opts.color || C.ink,
    align: opts.align || "left",
    valign: opts.valign || "top",
    breakLine: opts.breakLine,
    fit: "shrink",
    paraSpaceAfterPt: opts.paraSpaceAfterPt || 0,
    breakLine: false,
    rotate: opts.rotate || 0,
    transparency: opts.transparency,
  });
}

function fitText(text, opts) {
  try {
    return autoFontSize(text, FONT, {
      ...opts,
      mode: "shrink",
      leading: 1.15,
    }).fontSize;
  } catch (_err) {
    return opts.fontSize || 14;
  }
}

function rect(slide, x, y, w, h, fill, line = fill, opts = {}) {
  slide.addShape(pptx.ShapeType[opts.round ? "roundRect" : "rect"], {
    x,
    y,
    w,
    h,
    rectRadius: opts.radius,
    fill: { color: fill, transparency: opts.transparency || 0 },
    line: { color: line, transparency: opts.lineTransparency || 0, width: opts.lineWidth || 1 },
    shadow: opts.shadow,
  });
}

function line(slide, x1, y1, x2, y2, color = C.teal, width = 1.5, opts = {}) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1,
    y: y1,
    w: x2 - x1,
    h: y2 - y1,
    line: {
      color,
      width,
      beginArrowType: opts.beginArrowType,
      endArrowType: opts.endArrowType,
      transparency: opts.transparency || 0,
    },
  });
}

function header(slide, idx, title, dark = false) {
  const fg = dark ? C.paper : C.ink;
  const sub = dark ? "C8D8D2" : C.muted;
  addText(slide, idx, 0.52, 0.28, 0.7, 0.22, {
    fontSize: 10,
    color: sub,
    bold: true,
    fontFace: MONO,
  });
  addText(slide, title, 1.34, 0.22, 8.2, 0.34, {
    fontSize: 18,
    color: fg,
    bold: true,
  });
  line(slide, 0.52, 0.78, 12.8, 0.78, dark ? "6E8780" : C.faint, 1);
}

function footer(slide, dark = false) {
  addText(slide, "支持跨校区协作的分布式实验室管理系统设计与实现", 0.52, 7.07, 7.0, 0.16, {
    fontSize: 7.5,
    color: dark ? "BFD1CB" : "91A09B",
  });
}

function sectionTag(slide, text, x, y, color = C.gold) {
  addText(slide, text, x, y, 1.6, 0.18, {
    fontSize: 9.5,
    color,
    bold: true,
    fontFace: MONO,
  });
  line(slide, x, y + 0.29, x + 1.28, y + 0.29, color, 2);
}

function pill(slide, text, x, y, w, color = C.teal, fill = "DDEAE5") {
  rect(slide, x, y, w, 0.33, fill, fill, { round: true });
  addText(slide, text, x + 0.08, y + 0.085, w - 0.16, 0.1, {
    fontSize: 8.5,
    color,
    bold: true,
    align: "center",
  });
}

function card(slide, x, y, w, h, title, body, accent = C.teal) {
  rect(slide, x, y, w, h, C.white, C.faint, {
    round: true,
    shadow: safeOuterShadow("50605A", 0.14, 45, 1.5, 1),
  });
  rect(slide, x, y, 0.08, h, accent, accent);
  addText(slide, title, x + 0.22, y + 0.2, w - 0.42, 0.28, {
    fontSize: 14.5,
    bold: true,
    color: C.ink,
  });
  addText(slide, body, x + 0.22, y + 0.64, w - 0.42, h - 0.78, {
    fontSize: 10.2,
    color: C.muted,
    auto: true,
  });
}

function node(slide, text, x, y, w, h, fill = C.white, accent = C.teal) {
  rect(slide, x, y, w, h, fill, C.faint, { round: true });
  addText(slide, text, x + 0.08, y + h / 2 - 0.08, w - 0.16, 0.16, {
    fontSize: 10.5,
    bold: true,
    color: accent,
    align: "center",
  });
}

function addImageCrop(slide, imagePath, x, y, w, h) {
  if (fs.existsSync(imagePath)) {
    slide.addImage({ path: imagePath, ...imageSizingCrop(imagePath, x, y, w, h) });
  }
}

function addImageContain(slide, imagePath, x, y, w, h) {
  if (fs.existsSync(imagePath)) {
    slide.addImage({ path: imagePath, ...imageSizingContain(imagePath, x, y, w, h) });
  }
}

function iconData(label, color = C.teal) {
  const svg = `
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
    <rect x="8" y="8" width="48" height="48" rx="12" fill="#F7F4EC" stroke="#${color}" stroke-width="3"/>
    <text x="32" y="39" text-anchor="middle" font-family="Arial" font-size="20" font-weight="700" fill="#${color}">${label}</text>
  </svg>`;
  return svgToDataUri(svg);
}

function addIcon(slide, label, x, y, color) {
  slide.addImage({ data: iconData(label, color), x, y, w: 0.44, h: 0.44 });
}

function addNotes(slide, text) {
  slide.addNotes(text);
}

function slideCover() {
  const s = pptx.addSlide();
  addBg(s, C.paper);
  rect(s, 0, 0, 5.08, H, C.tealDark, C.tealDark);
  addImageCrop(s, assets.cover, 5.08, 0, 8.25, H);
  addImageContain(s, assets.logo, 0.75, 0.55, 0.5, 0.5);
  addText(s, "毕业设计答辩", 1.38, 0.67, 2.3, 0.22, {
    fontSize: 13.5,
    color: "D7E5DF",
    bold: true,
  });
  addText(s, "支持跨校区协作的\n分布式实验室\n管理系统", 0.78, 1.4, 4.0, 1.78, {
    fontSize: 29,
    color: C.paper,
    bold: true,
    auto: true,
  });
  line(s, 0.8, 3.48, 3.65, 3.48, C.gold, 2.25);
  addText(s, "设计与实现", 0.8, 3.72, 2.0, 0.22, {
    fontSize: 13,
    color: "D7E5DF",
    bold: true,
  });
  addText(s, "Flask + SQLAlchemy + uni-app + 微信小程序 + Agent 智能助手", 0.82, 4.12, 3.75, 0.46, {
    fontSize: 10.6,
    color: "D7E5DF",
    auto: true,
  });
  pill(s, "跨校区资源", 0.82, 4.9, 1.15);
  pill(s, "预约审批", 2.12, 4.9, 1.0);
  pill(s, "权限控制", 3.26, 4.9, 1.0);
  pill(s, "智能助手", 0.82, 5.34, 1.05);
  addText(s, "答辩人：________    指导教师：________    专业：________", 0.82, 6.6, 4.0, 0.18, {
    fontSize: 10.5,
    color: "E8F0EC",
  });
  addNotes(s, "各位老师好，我的毕业设计题目是《支持跨校区协作的分布式实验室管理系统设计与实现》。系统面向高校多校区实验室资源管理与预约审批场景，采用 Flask 后端、SQLAlchemy 数据模型、uni-app Web/H5 端和微信小程序端，并加入面向预约业务的 Agent 智能助手。");
}

function slideAgenda() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "00", "汇报提纲");
  const rows = [
    ["01", "背景与问题", "多校区资源分散，线下预约与审批难以形成闭环。", C.teal],
    ["02", "系统设计", "围绕角色、资源、预约、审批、统计建立统一架构。", C.blue],
    ["03", "关键实现", "后端分层、冲突检测、权限边界、Agent 工具体系。", C.gold],
    ["04", "测试总结", "验证核心业务流程，并说明不足与后续优化方向。", C.sage],
  ];
  rows.forEach(([n, t, b, color], i) => {
    const y = 1.32 + i * 1.18;
    addText(s, n, 0.82, y + 0.06, 0.55, 0.26, { fontSize: 17, color, bold: true, fontFace: MONO, align: "center" });
    line(s, 1.72, y + 0.29, 2.62, y + 0.29, color, 2);
    addText(s, t, 2.92, y, 2.25, 0.32, { fontSize: 19, color: C.ink, bold: true });
    addText(s, b, 5.2, y + 0.04, 6.5, 0.26, { fontSize: 12.5, color: C.muted });
  });
  rect(s, 0.76, 6.32, 11.8, 0.46, C.tealDark, C.tealDark);
  addText(s, "答辩主线：从真实管理痛点出发，说明系统如何用工程结构和智能助手提升规范性、透明度和效率。", 1.0, 6.48, 11.3, 0.12, {
    fontSize: 9.6,
    color: C.paper,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "本次汇报主要分为四个部分：首先说明研究背景与管理痛点；然后介绍系统目标、角色模块和总体架构；接着重点说明预约规则、权限控制和 Agent 智能助手；最后给出测试结论、总结与后续展望。");
}

function slideBackground() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "01", "研究背景与问题");
  addText(s, "多校区办学让实验室管理从“登记问题”升级为“协同问题”。", 0.78, 1.08, 5.5, 0.8, {
    fontSize: 24,
    bold: true,
    auto: true,
  });
  const cards = [
    ["资源分散", "不同校区实验室类型、设备配置、开放时间和管理人员存在差异，师生难以及时判断可用资源。", C.teal],
    ["流程滞后", "线下登记、人工沟通和表格维护容易造成重复预约、审批延迟与信息遗漏。", C.rust],
    ["统计困难", "审批记录、使用情况和操作日志分散，管理人员缺少可追踪的数据依据。", C.sage],
  ];
  cards.forEach(([t, b, c], i) => card(s, 0.78 + i * 4.04, 2.25, 3.72, 2.15, t, b, c));
  rect(s, 0.82, 5.18, 11.74, 0.8, C.tealDark, C.tealDark);
  addText(s, "课题目标：建立统一后端、多端访问、权限隔离、可追踪审批与自然语言辅助的实验室管理平台。", 1.1, 5.46, 11.15, 0.18, {
    fontSize: 12.8,
    color: C.paper,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "多校区办学后，实验室资源不再集中在单一地点，开放时间、容量、设备状态和管理人员都可能不同。传统线下登记或表格管理容易带来信息不透明、预约冲突、审批滞后和统计困难等问题。因此本课题希望用统一系统解决跨校区协同管理问题。");
}

function slideGoals() {
  const s = pptx.addSlide();
  addBg(s, C.tealDark);
  header(s, "02", "系统建设目标与研究内容", true);
  sectionTag(s, "OBJECTIVES", 0.78, 1.15, C.gold);
  addText(s, "一个平台覆盖\n资源、预约、审批、统计与智能问答", 0.78, 1.58, 4.4, 0.95, {
    fontSize: 24,
    bold: true,
    color: C.paper,
    auto: true,
  });
  const goals = [
    ["统一资源组织", "校区、实验室、设备、用户与预约数据集中建模"],
    ["规范预约流程", "开放时间、容量、状态、冲突检测和审批流转统一校验"],
    ["角色权限隔离", "学生、教师、实验室管理员、系统管理员分权访问"],
    ["智能交互入口", "通过 Agent 降低查询路径和预约操作成本"],
  ];
  goals.forEach(([t, b], i) => {
    const x = i % 2 === 0 ? 5.35 : 9.05;
    const y = 1.25 + Math.floor(i / 2) * 2.05;
    rect(s, x, y, 3.35, 1.38, C.paper, "CAD8D2", { round: true });
    addText(s, t, x + 0.24, y + 0.22, 2.9, 0.22, { fontSize: 14.8, color: C.tealDark, bold: true });
    addText(s, b, x + 0.24, y + 0.66, 2.78, 0.42, { fontSize: 9.8, color: C.muted, auto: true });
  });
  addText(s, "核心原则：业务规则集中在后端 Service 层，多端共享同一套判断结果。", 0.82, 5.9, 4.25, 0.24, {
    fontSize: 10.6,
    color: "D7E5DF",
    bold: true,
  });
  footer(s, true);
  addNotes(s, "系统目标可以概括为四点：统一资源组织、规范预约流程、角色权限隔离和智能交互入口。尤其是预约相关规则全部在后端服务层统一校验，保证 Web 端、小程序端和 Agent 调用的业务结果一致。");
}

function slideRolesModules() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "03", "用户角色与功能模块");
  const roles = [
    ["学生", "student", "仅自己", "查看实验室、提交预约、查看/取消个人预约"],
    ["教师", "teacher", "仅自己", "教学或科研实践预约，跟踪审批状态"],
    ["实验室管理员", "lab_admin", "本校区", "维护本校区资源，处理审批与统计"],
    ["系统管理员", "system_admin", "全局", "维护全部校区、用户、实验室与统计"],
  ];
  roles.forEach(([role, id, scope, desc], i) => {
    const x = 0.68 + i * 3.12;
    rect(s, x, 1.16, 2.64, 1.32, ["E5F0EA", "F1F3EE", "F8EBCD", "E6EEF2"][i], C.faint, { round: true });
    addText(s, role, x + 0.12, 1.38, 2.4, 0.2, { fontSize: 14.2, bold: true, align: "center" });
    addText(s, id, x + 0.12, 1.76, 2.4, 0.16, { fontSize: 8.5, fontFace: MONO, color: C.teal, bold: true, align: "center" });
    addText(s, `权限范围：${scope}`, x + 0.12, 2.08, 2.4, 0.14, { fontSize: 8.6, color: C.muted, bold: true, align: "center" });
  });
  const modules = [
    ["认证与资料", "登录鉴权、资料维护", C.teal],
    ["资源管理", "校区、实验室、设备", C.sage],
    ["预约管理", "提交、冲突检测、取消", C.gold],
    ["审批管理", "通过/拒绝、审批意见", C.rust],
    ["统计分析", "总览、校区、利用率", C.blue],
    ["Agent 助手", "查询、推荐、创建", C.teal],
  ];
  modules.forEach(([t, b, c], i) => {
    const x = 0.82 + (i % 3) * 4.08;
    const y = 3.35 + Math.floor(i / 3) * 1.3;
    card(s, x, y, 3.53, 0.94, t, b, c);
  });
  footer(s);
  addNotes(s, "系统包含学生、教师、实验室管理员和系统管理员四类角色。学生和教师主要完成查询、预约和个人预约管理；实验室管理员负责本校区资源维护和审批；系统管理员负责全局数据维护和统计管理。");
}

function slideArchitecture() {
  const s = pptx.addSlide();
  addBg(s, C.paper2);
  header(s, "04", "系统总体架构设计");
  sectionTag(s, "ARCHITECTURE", 0.78, 1.1, C.teal);
  const layers = [
    ["客户端层", "Web/H5 管理端\n微信小程序端", "E2F0EA", C.teal],
    ["接口服务层", "Flask Blueprints\n统一 /api 路由", "F8EBCD", C.gold],
    ["业务服务层", "预约 / 审批 / 统计\nAgent 工具执行", "E6EEF2", C.blue],
    ["数据持久层", "SQLAlchemy ORM\nMySQL / SQLite", C.white, C.sage],
  ];
  layers.forEach(([t, b, fill, color], i) => {
    const x = 0.92 + i * 3.05;
    rect(s, x, 1.86, 2.45, 3.15, fill, "C8D6D0", { round: true });
    addIcon(s, String(i + 1), x + 1.0, 2.08, color);
    addText(s, t, x + 0.2, 2.68, 2.05, 0.22, { fontSize: 15.8, bold: true, align: "center" });
    line(s, x + 0.45, 3.1, x + 2.0, 3.1, color, 2);
    addText(s, b, x + 0.28, 3.45, 1.9, 0.64, { fontSize: 11, color: C.muted, align: "center", auto: true });
    if (i < 3) addText(s, "→", x + 2.57, 3.13, 0.28, 0.2, { fontSize: 18, color: C.teal, bold: true, align: "center" });
  });
  rect(s, 0.95, 5.72, 11.45, 0.52, C.tealDark, C.tealDark);
  addText(s, "多端不重复实现核心业务规则，统一由后端服务层校验预约冲突、容量、开放时间和权限边界。", 1.18, 5.91, 11.0, 0.12, {
    fontSize: 10.2,
    color: C.paper,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "系统采用前后端分离与分层架构。前端包括 Web/H5 和微信小程序，统一调用 Flask 提供的 RESTful API。后端分为 API 层、Service 层、Model 层和 Utils 层，其中 Service 层集中处理预约冲突检测、审批流转、统计聚合和 Agent 工具执行。");
}

function slideDataModel() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "05", "核心数据模型");
  const entities = [
    ["User", "用户 / 角色 / 校区", 0.85, 1.48],
    ["Campus", "校区资源", 4.1, 1.14],
    ["Laboratory", "容量 / 开放时间", 7.35, 1.48],
    ["Equipment", "设备状态", 10.15, 2.78],
    ["Reservation", "预约时段 / 状态", 4.1, 3.55],
    ["Approval", "审批记录", 7.35, 3.55],
    ["OperationLog", "操作日志", 0.95, 4.78],
  ];
  entities.forEach(([name, desc, x, y]) => {
    rect(s, x, y, 2.55, 0.82, C.white, C.faint, { round: true });
    addText(s, name, x + 0.15, y + 0.13, 2.25, 0.16, { fontSize: 11.4, fontFace: MONO, color: C.teal, bold: true, align: "center" });
    addText(s, desc, x + 0.15, y + 0.45, 2.25, 0.14, { fontSize: 8.4, color: C.muted, align: "center" });
  });
  [
    [3.4, 1.9, 4.1, 1.58],
    [6.65, 1.58, 7.35, 1.9],
    [5.38, 1.96, 5.38, 3.55],
    [8.65, 2.3, 8.65, 3.55],
    [9.9, 3.18, 10.15, 3.18],
    [3.5, 5.13, 4.1, 3.95],
  ].forEach(([x1, y1, x2, y2]) => line(s, x1, y1, x2, y2, "9FB1AB", 1, { endArrowType: "triangle" }));
  rect(s, 0.82, 6.05, 11.7, 0.48, C.paper2, "CFDCD5", { round: true });
  addText(s, "模型主线：以“校区 - 实验室 - 预约”为核心，叠加审批记录和操作日志，支撑跨校区查询、权限隔离与审计追踪。", 1.1, 6.22, 11.15, 0.12, {
    fontSize: 10.2,
    color: C.tealDark,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "数据模型围绕校区、实验室、设备、预约、审批和操作日志展开。校区与实验室是一对多关系，实验室关联设备和预约记录，预约再关联审批记录。这样的设计既能支持跨校区查询，也能支持校区级权限隔离。");
}

function slideReservationFlow() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "06", "预约业务流程与规则");
  const steps = [
    ["1", "提交申请", "校区、实验室、日期、时间、人数、用途", C.teal],
    ["2", "基础校验", "必填、实验室状态、校区一致性", C.blue],
    ["3", "时段校验", "开始早于结束，并处于开放时间", C.gold],
    ["4", "容量与冲突", "人数不超容量，不与有效预约重叠", C.rust],
    ["5", "审批流转", "学生/教师待审批，管理员可自动通过", C.sage],
  ];
  steps.forEach(([n, t, b, color], i) => {
    const x = 0.64 + i * 2.54;
    rect(s, x, 1.48, 2.08, 2.68, C.white, C.faint, { round: true });
    rect(s, x + 0.2, 1.76, 0.48, 0.48, color, color, { round: true });
    addText(s, n, x + 0.2, 1.89, 0.48, 0.12, { fontSize: 12, color: C.white, bold: true, align: "center", fontFace: MONO });
    addText(s, t, x + 0.18, 2.47, 1.72, 0.22, { fontSize: 13.4, bold: true, align: "center" });
    addText(s, b, x + 0.22, 3.03, 1.62, 0.55, { fontSize: 8.9, color: C.muted, auto: true, align: "center" });
    if (i < 4) addText(s, "→", x + 2.17, 2.7, 0.22, 0.14, { fontSize: 15.5, color: C.teal, bold: true, align: "center" });
  });
  rect(s, 0.96, 5.15, 11.38, 0.86, C.tealDark, C.tealDark);
  addText(s, "关键判断：冲突检测、开放时间、容量限制、权限边界都在服务层裁决，Agent 与前端不能绕过规则。", 1.22, 5.45, 10.86, 0.18, {
    fontSize: 12.2,
    color: C.paper,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "预约创建时，系统会依次校验必填字段、实验室状态、校区一致性、时间范围、开放时段、容量限制和预约冲突。学生和教师提交后默认进入待审批状态，管理员预约可按规则自动通过。");
}

function slideSecurity() {
  const s = pptx.addSlide();
  addBg(s, C.tealDark);
  header(s, "07", "权限与安全控制", true);
  const guards = [
    ["JWT 登录鉴权", "登录后签发 token，敏感接口统一校验身份，适配前后端分离的无状态认证。", C.sage],
    ["RBAC 角色权限", "按 student、teacher、lab_admin、system_admin 分配功能入口和接口权限。", C.gold],
    ["校区数据边界", "实验室管理员只能管理本校区实验室、设备、预约和统计，系统管理员维护全局。", C.blue],
  ];
  guards.forEach(([t, b, accent], i) => {
    const x = 0.82 + i * 4.15;
    rect(s, x, 1.42, 3.55, 3.45, C.paper, "CAD8D2", { round: true });
    rect(s, x, 1.42, 3.55, 0.1, accent, accent);
    addText(s, t, x + 0.25, 1.88, 3.02, 0.24, { fontSize: 15.8, color: C.tealDark, bold: true, align: "center" });
    addText(s, b, x + 0.32, 2.62, 2.86, 0.9, { fontSize: 10.8, color: C.muted, align: "center", auto: true });
  });
  addText(s, "模型负责理解和规划，系统负责校验和执行：智能能力被纳入权限边界之内。", 0.95, 5.82, 11.45, 0.25, {
    fontSize: 14,
    color: C.paper,
    bold: true,
    align: "center",
  });
  footer(s, true);
  addNotes(s, "系统采用 JWT 进行登录鉴权，并结合 RBAC 思想控制不同角色的接口权限。对于实验室管理员，系统进一步限制其只能管理所属校区的数据。Agent 创建预约时同样走后端服务层，因此不能绕过权限和业务校验。");
}

function slideMultiTerminal() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "08", "多端协同访问与前端组织");
  rect(s, 0.8, 1.22, 5.62, 3.55, C.white, C.faint, { round: true });
  addText(s, "Web / H5 管理端", 1.1, 1.7, 4.9, 0.3, { fontSize: 18.5, bold: true });
  addText(s, "面向系统管理员和实验室管理员，用于用户维护、校区/实验室/设备管理、审批处理、统计分析。", 1.1, 2.3, 4.72, 1.05, {
    fontSize: 12.5,
    color: C.muted,
    auto: true,
  });
  line(s, 1.1, 3.92, 5.55, 3.92, C.teal, 2);
  addText(s, "高频管理任务集中处理，适合桌面端信息密度。", 1.1, 4.16, 4.8, 0.15, { fontSize: 9.2, color: C.teal, bold: true });
  rect(s, 6.94, 1.22, 5.62, 3.55, C.white, C.faint, { round: true });
  addText(s, "微信小程序端", 7.24, 1.7, 4.9, 0.3, { fontSize: 18.5, bold: true });
  addText(s, "面向学生和教师，用于浏览校区、查询实验室、提交预约、查看个人预约、使用 Agent 助手。", 7.24, 2.3, 4.72, 1.05, {
    fontSize: 12.5,
    color: C.muted,
    auto: true,
  });
  line(s, 7.24, 3.92, 11.68, 3.92, C.gold, 2);
  addText(s, "轻量查询与预约入口更适合移动场景。", 7.24, 4.16, 4.8, 0.15, { fontSize: 9.2, color: C.gold, bold: true });
  rect(s, 1.0, 5.65, 11.3, 0.46, C.paper2, "CFDCD5", { round: true });
  addText(s, "前端结构：api / common / components / config / pages 分层，路由、会话、平台差异和页面壳集中管理。", 1.25, 5.82, 10.8, 0.12, {
    fontSize: 10.2,
    color: C.tealDark,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "Web/H5 端主要面向管理人员，小程序端主要面向学生和教师。两端共享同一套后端 API，前端负责展示和交互，核心业务规则不重复写在不同端，降低了维护成本。前端按 api、common、components、config 和 pages 分层组织。");
}

function slideResourceShowcase() {
  const s = pptx.addSlide();
  addBg(s, C.paper2);
  header(s, "09", "系统页面与资源展示");
  [assets.haidian, assets.fengtai, assets.hainan, assets.mainCampus].forEach((img, i) => {
    const x = 0.76 + i * 3.13;
    addImageCrop(s, img, x, 1.3, 2.63, 1.5);
  });
  addText(s, "系统将校区、实验室、设备和预约记录统一组织，用户可按校区浏览资源，管理员可按校区维护数据。", 0.82, 3.42, 4.8, 0.56, {
    fontSize: 17,
    bold: true,
    auto: true,
  });
  const stats = [
    ["4", "类用户角色", C.teal],
    ["8+", "核心业务模块", C.gold],
    ["2", "访问终端", C.blue],
    ["1", "统一后端 API", C.sage],
  ];
  stats.forEach(([num, label, color], i) => {
    const x = 6.08 + (i % 2) * 3.16;
    const y = 3.28 + Math.floor(i / 2) * 1.16;
    rect(s, x, y, 2.63, 0.84, C.white, C.faint, { round: true });
    addText(s, num, x + 0.22, y + 0.14, 0.72, 0.24, { fontSize: 20, color, bold: true, align: "center", fontFace: MONO });
    addText(s, label, x + 1.02, y + 0.26, 1.42, 0.14, { fontSize: 9.3, color: C.muted, bold: true });
  });
  addText(s, "展示重点不只是页面数量，而是多端共用同一套后端规则，减少系统维护和数据不一致风险。", 0.82, 5.86, 11.6, 0.16, {
    fontSize: 11.2,
    color: C.tealDark,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "系统将校区、实验室、设备和预约记录统一组织。用户可按校区浏览资源，管理员可按校区维护数据。展示重点不只是页面数量，而是多端共用同一套后端规则，减少系统维护和数据不一致风险。");
}

function slideAgentDesign() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "10", "Agent 智能助手设计");
  addText(s, "Agent 不是直接操作数据库，而是自然语言入口和任务规划器。", 0.78, 1.12, 5.0, 0.62, {
    fontSize: 22,
    bold: true,
    auto: true,
  });
  const blocks = [
    ["规则抽取", "日期、时间、人数、用途、校区、实验室偏好", C.teal],
    ["DeepSeek 规划", "根据上下文选择下一步工具与参数", C.gold],
    ["工具执行", "查询排期、推荐实验室、检查可用性、创建预约", C.blue],
    ["服务层校验", "冲突、容量、开放时间、权限边界最终裁决", C.sage],
  ];
  blocks.forEach(([t, b, color], i) => {
    const x = 0.9 + i * 3.08;
    const y = 2.45;
    rect(s, x, y, 2.55, 1.46, ["E5F0EA", "F8EBCD", "E6EEF2", C.white][i], C.faint, { round: true });
    addText(s, t, x + 0.18, y + 0.24, 2.15, 0.2, { fontSize: 13.4, bold: true, align: "center", color: C.ink });
    addText(s, b, x + 0.18, y + 0.72, 2.15, 0.38, { fontSize: 8.7, color: C.muted, align: "center", auto: true });
    if (i < 3) addText(s, "→", x + 2.66, y + 0.58, 0.28, 0.14, { fontSize: 17, color: C.teal, bold: true, align: "center" });
  });
  rect(s, 0.96, 5.32, 11.3, 0.6, C.tealDark, C.tealDark);
  addText(s, "价值：保留自然语言交互体验，同时保证业务系统可控、可审计、可降级。", 1.18, 5.54, 10.85, 0.13, {
    fontSize: 11.5,
    color: C.paper,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "Agent 的定位不是直接操作数据库，而是自然语言入口和任务规划器。系统先用规则抽取日期、时间、人数、校区等字段，再由 DeepSeek 判断下一步调用哪个工具，最后由后端工具和 Service 层执行业务。");
}

function slideAgentTools() {
  const s = pptx.addSlide();
  addBg(s, C.paper2);
  header(s, "11", "Agent 工具体系与预约链路");
  const tools = [
    "query_labs",
    "query_schedule",
    "check_availability",
    "recommend_lab",
    "recommend_time",
    "create_reservation",
    "my_reservations",
    "cancel_reservation",
    "explain_rules",
  ];
  tools.forEach((t, i) => {
    const x = 0.72 + (i % 3) * 4.12;
    const y = 1.22 + Math.floor(i / 3) * 0.64;
    rect(s, x, y, 3.34, 0.43, C.white, C.faint, { round: true });
    addText(s, t, x + 0.08, y + 0.13, 3.18, 0.11, { fontSize: 8.8, fontFace: MONO, color: C.teal, bold: true, align: "center" });
  });
  const chain = ["用户输入", "抽取表单", "选择工具", "后端执行", "业务校验", "回复/跳转"];
  chain.forEach((t, i) => {
    const x = 0.72 + i * 2.09;
    rect(s, x, 4.22, 1.66, 0.72, "E5F0EA", "CFDCD5", { round: true });
    addText(s, t, x + 0.08, 4.47, 1.5, 0.12, { fontSize: 9.8, bold: true, align: "center" });
    if (i < chain.length - 1) addText(s, "→", x + 1.73, 4.42, 0.25, 0.12, { fontSize: 14, color: C.teal, bold: true, align: "center" });
  });
  addText(s, "多轮会话保存 last_labs、last_recommended_time 等上下文，支持“就第一个”“就这个时间”等省略表达。", 0.9, 5.9, 11.5, 0.15, {
    fontSize: 10.8,
    color: C.muted,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "Agent 支持查询实验室、查询排期、检查可用性、推荐实验室、推荐时间、创建预约、查询我的预约和取消预约等工具。同时会保存上一次推荐结果，使用户可以用“就第一个”“就这个时间”这类自然表达继续操作。");
}

function slideHighlights() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "12", "关键实现亮点");
  const highlights = [
    ["后端分层清晰", "API 层处理入口，Service 层承载业务，Model 层管理实体关系，Utils 层提供通用响应和校验。", C.teal],
    ["预约冲突集中", "预约创建统一检测有效状态下的时间重叠，避免 Web、小程序和 Agent 出现规则差异。", C.gold],
    ["Agent 可降级", "大模型不可用时保留规则模式，个人预约、排期查询、取消预约等基础功能仍可运行。", C.sage],
    ["操作可追踪", "审批、预约和管理操作写入日志，为系统审计、问题回溯和答辩说明提供依据。", C.blue],
  ];
  highlights.forEach(([t, b, c], i) => {
    const x = 0.78 + (i % 2) * 6.08;
    const y = 1.25 + Math.floor(i / 2) * 2.12;
    card(s, x, y, 5.38, 1.5, t, b, c);
  });
  footer(s);
  addNotes(s, "本系统的实现亮点包括：后端分层清晰、预约冲突检测集中、Agent 可降级和操作可追踪。尤其是可降级设计可以保证大模型不可用时，基础查询和预约辅助功能仍可运行。");
}

function slideTesting() {
  const s = pptx.addSlide();
  addBg(s, C.tealDark);
  header(s, "13", "系统测试与结果", true);
  const tests = [
    ["功能测试", "登录、资源管理、预约、审批、统计、Agent 对话", C.sage],
    ["权限测试", "角色入口、接口鉴权、校区级数据范围", C.gold],
    ["边界测试", "容量超限、时间非法、预约冲突、缺参", C.blue],
    ["稳定性测试", "LLM 不可用时规则兜底，接口统一错误返回", C.rust],
  ];
  tests.forEach(([t, b, color], i) => {
    const x = 0.9 + (i % 2) * 6.05;
    const y = 1.35 + Math.floor(i / 2) * 1.62;
    rect(s, x, y, 5.25, 1.02, C.paper, "CAD8D2", { round: true });
    addText(s, t, x + 0.22, y + 0.2, 1.3, 0.2, { fontSize: 13, color: C.tealDark, bold: true });
    addText(s, b, x + 1.55, y + 0.2, 3.35, 0.35, { fontSize: 9.6, color: C.muted, auto: true });
    rect(s, x, y, 0.08, 1.02, color, color);
  });
  s.addChart(
    pptx.ChartType.bar,
    [
      {
        name: "通过用例",
        labels: ["功能", "权限", "边界", "Agent"],
        values: [7, 4, 3, 5],
      },
    ],
    {
      x: 1.25,
      y: 4.72,
      w: 4.8,
      h: 1.18,
      catAxisLabelFontFace: FONT,
      catAxisLabelFontSize: 8,
      valAxisLabelFontFace: FONT,
      valAxisLabelFontSize: 8,
      showLegend: false,
      showTitle: false,
      showValue: true,
      valAxisMinVal: 0,
      valAxisMaxVal: 8,
      chartColors: [C.gold],
      valGridLine: { color: "52736B", transparency: 70 },
      showCatName: true,
      showValAxis: false,
    }
  );
  addText(s, "测试结论：系统能够覆盖多角色、多校区、多终端条件下的核心实验室预约管理需求。", 6.45, 5.12, 5.55, 0.34, {
    fontSize: 15.5,
    color: C.paper,
    bold: true,
    auto: true,
  });
  footer(s, true);
  addNotes(s, "测试主要覆盖功能测试、权限测试、边界测试、稳定性测试和 Agent 模块测试。结果表明，系统能够支持多角色、多校区和多终端条件下的实验室预约管理需求，并能对越权、冲突、容量超限和开放时间外预约等异常情况进行限制。");
}

function slideSummary() {
  const s = pptx.addSlide();
  addBg(s);
  header(s, "14", "总结与展望");
  addText(s, "已完成工作", 0.78, 1.15, 5.2, 0.34, { fontSize: 22, bold: true });
  const done = [
    "跨校区实验室资源模型",
    "预约冲突检测与审批流转",
    "Web/H5 与微信小程序多端访问",
    "面向预约场景的 Agent 智能助手",
  ];
  done.forEach((t, i) => {
    node(s, t, 0.92, 1.92 + i * 0.55, 4.9, 0.36, "E5F0EA", C.teal);
  });
  addText(s, "后续优化方向", 7.02, 1.15, 5.2, 0.34, { fontSize: 22, bold: true });
  const future = [
    "接入统一身份认证与校园门户",
    "增加消息通知与审批提醒",
    "扩展统计预测与资源优化算法",
    "增强 Agent 多轮规划和解释能力",
  ];
  future.forEach((t, i) => {
    node(s, t, 7.14, 1.92 + i * 0.55, 4.9, 0.36, "F8EBCD", C.gold);
  });
  rect(s, 0.86, 5.5, 11.66, 0.72, C.tealDark, C.tealDark);
  addText(s, "核心贡献：把跨校区资源协同、权限控制、预约业务规则和智能助手整合为一套可运行系统。", 1.12, 5.76, 11.12, 0.18, {
    fontSize: 12.2,
    color: C.paper,
    bold: true,
    align: "center",
  });
  footer(s);
  addNotes(s, "本课题完成了跨校区实验室管理系统的设计与实现，并在传统预约系统基础上加入 Agent 智能助手。后续可以继续扩展统一身份认证、消息通知、资源利用率预测、Agent 日志可解释性和移动端体验优化。");
}

function slideThanks() {
  const s = pptx.addSlide();
  addBg(s, C.tealDark);
  addText(s, "谢谢各位老师", 0.88, 1.65, 11.6, 0.86, {
    fontSize: 40,
    color: C.paper,
    bold: true,
    align: "center",
  });
  addText(s, "欢迎批评指正", 1.8, 3.0, 9.8, 0.36, {
    fontSize: 22,
    color: "D7E5DF",
    align: "center",
  });
  line(s, 3.1, 4.0, 10.24, 4.0, C.gold, 2.2);
  addText(s, "支持跨校区协作的分布式实验室管理系统设计与实现", 1.55, 4.65, 10.3, 0.28, {
    fontSize: 16,
    color: C.paper,
    bold: true,
    align: "center",
  });
  addNotes(s, "我的汇报到此结束，欢迎各位老师批评指正。");
}

function buildNotesMarkdown() {
  const sections = [
    ["1. 封面", "各位老师好，我的毕业设计题目是《支持跨校区协作的分布式实验室管理系统设计与实现》。系统面向高校多校区实验室资源管理与预约审批场景，采用 Flask 后端、SQLAlchemy 数据模型、uni-app Web/H5 端和微信小程序端，并加入面向预约业务的 Agent 智能助手。"],
    ["2. 汇报提纲", "本次汇报主要分为四个部分：研究背景与管理痛点；系统目标、角色模块和总体架构；预约规则、权限控制和 Agent 智能助手；测试结论、总结与后续展望。"],
    ["3. 研究背景与问题", "多校区办学后，实验室资源不再集中在单一地点，开放时间、容量、设备状态和管理人员都可能不同。传统线下登记或表格管理容易带来信息不透明、预约冲突、审批滞后和统计困难等问题。"],
    ["4. 系统建设目标与研究内容", "系统目标可以概括为四点：统一资源组织、规范预约流程、角色权限隔离和智能交互入口。尤其是预约相关规则全部在后端服务层统一校验，保证 Web 端、小程序端和 Agent 调用的业务结果一致。"],
    ["5. 用户角色与功能模块", "系统包含学生、教师、实验室管理员和系统管理员四类角色。学生和教师主要完成查询、预约和个人预约管理；实验室管理员负责本校区资源维护和审批；系统管理员负责全局数据维护和统计管理。"],
    ["6. 系统总体架构设计", "系统采用前后端分离与分层架构。前端包括 Web/H5 和微信小程序，统一调用 Flask 提供的 RESTful API。后端分为 API 层、Service 层、Model 层和 Utils 层，其中 Service 层集中处理预约冲突检测、审批流转、统计聚合和 Agent 工具执行。"],
    ["7. 核心数据模型", "数据模型围绕校区、实验室、设备、预约、审批和操作日志展开。校区与实验室是一对多关系，实验室关联设备和预约记录，预约再关联审批记录。这样的设计既能支持跨校区查询，也能支持校区级权限隔离。"],
    ["8. 预约业务流程与规则", "预约创建时，系统会依次校验必填字段、实验室状态、校区一致性、时间范围、开放时段、容量限制和预约冲突。学生和教师提交后默认进入待审批状态，管理员预约可按规则自动通过。"],
    ["9. 权限与安全控制", "系统采用 JWT 进行登录鉴权，并结合 RBAC 思想控制不同角色的接口权限。对于实验室管理员，系统进一步限制其只能管理所属校区的数据。Agent 创建预约时同样走后端服务层，因此不能绕过权限和业务校验。"],
    ["10. 多端协同访问与前端组织", "Web/H5 端主要面向管理人员，小程序端主要面向学生和教师。两端共享同一套后端 API，前端负责展示和交互，核心业务规则不重复写在不同端，降低了维护成本。"],
    ["11. 系统页面与资源展示", "系统将校区、实验室、设备和预约记录统一组织。用户可按校区浏览资源，管理员可按校区维护数据。展示重点不只是页面数量，而是多端共用同一套后端规则。"],
    ["12. Agent 智能助手设计", "Agent 的定位不是直接操作数据库，而是自然语言入口和任务规划器。系统先用规则抽取日期、时间、人数、校区等字段，再由 DeepSeek 判断下一步调用哪个工具，最后由后端工具和 Service 层执行业务。"],
    ["13. Agent 工具体系与预约链路", "Agent 支持查询实验室、查询排期、检查可用性、推荐实验室、推荐时间、创建预约、查询我的预约和取消预约等工具。同时会保存上一次推荐结果，使用户可以用“就第一个”“就这个时间”这类自然表达继续操作。"],
    ["14. 关键实现亮点", "本系统的实现亮点包括：后端分层清晰、预约冲突检测集中、Agent 可降级和操作可追踪。尤其是可降级设计可以保证大模型不可用时，基础查询和预约辅助功能仍可运行。"],
    ["15. 系统测试与结果", "测试主要覆盖功能测试、权限测试、边界测试、稳定性测试和 Agent 模块测试。结果表明，系统能够支持多角色、多校区和多终端条件下的实验室预约管理需求。"],
    ["16. 总结与展望", "本课题完成了跨校区实验室管理系统的设计与实现，并在传统预约系统基础上加入 Agent 智能助手。后续可以继续扩展统一身份认证、消息通知、资源利用率预测、Agent 日志可解释性和移动端体验优化。"],
    ["17. 结束页", "我的汇报到此结束，欢迎各位老师批评指正。"],
  ];
  return `# 毕业答辩 PPT 讲稿\n\n${sections
    .map(([h, body]) => `## ${h}\n${body}`)
    .join("\n\n")}\n`;
}

function buildDeck() {
  slideCover();
  slideAgenda();
  slideBackground();
  slideGoals();
  slideRolesModules();
  slideArchitecture();
  slideDataModel();
  slideReservationFlow();
  slideSecurity();
  slideMultiTerminal();
  slideResourceShowcase();
  slideAgentDesign();
  slideAgentTools();
  slideHighlights();
  slideTesting();
  slideSummary();
  slideThanks();
}

async function main() {
  buildDeck();
  pptx._slides.forEach((slide) => {
    warnIfSlideHasOverlaps(slide, pptx, {
      muteContainment: true,
      ignoreLines: true,
      ignoreDecorativeShapes: true,
    });
    warnIfSlideElementsOutOfBounds(slide, pptx);
  });
  fs.writeFileSync(outNotes, buildNotesMarkdown(), "utf8");
  await pptx.writeFile({ fileName: outPptx });
  console.log(outPptx);
  console.log(outNotes);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
