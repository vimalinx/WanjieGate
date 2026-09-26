/* WanjieGate v1 — 决策模型驱动的自适应界面
 * 渲染循环(60fps) 与 决策循环(~3Hz) 解耦:KEV 只产出"目标态",
 * 每个组件的 materialize 标量 m 通过弹簧趋近目标,概率直接映射为透明度。
 */
"use strict";

const $ = s => document.querySelector(s);
const stage = $("#stage"), input = $("#input"), conn = $("#conn"), pulse = $("#pulse"), debug = $("#debug"), composer = $("#composer");

const MOCK = new URLSearchParams(location.search).has("mock");
const DEBOUNCE_MS = 320;
const TAU_IN = 0.16, TAU_OUT = 0.5;        // 进场快、退场慢(秒)
const MOUNT_P = 0.03, GHOST_LO = 0.15, SOLID = 0.55;
const STRIP_H = 54;
const EASE = "cubic-bezier(.22,1.2,.3,1)";

let manifest = null;
let cards = new Map();      // id -> {el, m, target, prob, bound, rect, applied, delay}
let layoutMode = "empty", densityCap = 1, emphasis = "none";
let intent = {choice: "explore", confidence: 0};
let committed = false;      // 意图已定:摘幽灵态,卡片直奔实体
let sceneId = null;         // 当前已定场景的页面 id(= 已承诺意图)
const COMMIT_MARGIN_IN = 0.30, COMMIT_MARGIN_OUT = 0.15;   // 意图判定走"头两名差距",比归一化置信度对小模型更稳
let latestText = "", seq = 0, inflight = null;
let dirty = {layout: true, debug: true};

/* ---------- manifest -> question set ---------- */
function buildQuestions() {
  const q = {};
  for (const [id, def] of Object.entries(manifest.questions))
    q[id] = {type: def.type, instructions: def.instructions, criteria: def.criteria};
  for (const [id, c] of Object.entries(manifest.components)) {
    q["vis_" + id] = {type: "noul", instructions: c.ask};
    if (c.bind) q["bind_" + id] = {type: "choice", instructions: c.bind.question, criteria: c.bind.options};
  }
  for (const [ctx, a] of Object.entries(manifest.attachments || {}))
    q["att_" + ctx] = {type: "noul", instructions: a.cue};
  return q;
}

function buildState() {
  return {
    role: "You are the layout engine of an adaptive UI canvas. Decide which interface elements fit the user's text.",
    note: manifest.stateNote,
    user_text_so_far: latestText,
    currently_visible: [...cards.values()].filter(c => c.m > 0.5).map(c => c.id),
  };
}

/* ---------- kev call ---------- */
async function decide() {
  const mySeq = ++seq;
  inflight?.abort();
  const ac = inflight = MOCK ? null : new AbortController();
  pulse.classList.add("thinking"); $("#pulse-text").textContent = "thinking";
  try {
    let answers;
    if (MOCK) ({answers} = await mockDecide());
    else {
      const res = await fetch(manifest.kev.baseUrl + "/v1/systemone", {
        method: "POST", headers: {"content-type": "application/json"},
        signal: ac.signal,
        body: JSON.stringify({state: buildState(), model: manifest.kev.model, questions: buildQuestions()}),
      });
      if (!res.ok) throw new Error("kev " + res.status);
      const body = await res.json();
      answers = body.answers;
      setConn("on", body.latency_ms);
    }
    if (mySeq !== seq) return;                 // 有更新的输入,丢弃旧决策帧
    applyAnswers(answers);
  } catch (e) {
    if (e.name === "AbortError") return;
    if (!MOCK) setConn("off");
  } finally {
    pulse.classList.remove("thinking"); $("#pulse-text").textContent = MOCK ? "mock" : "listening";
  }
}

function applyAnswers(a) {
  if (a.intent) {
    intent = a.intent;
    const ps = Object.values(intent.probabilities || {}).sort((x, y) => y - x);
    const margin = (ps[0] || 0) - (ps[1] || 0);
    committed = intent.choice !== "explore" && margin >= (committed ? COMMIT_MARGIN_OUT : COMMIT_MARGIN_IN);
    renderCard("intent-chip"); renderCard("action-bar"); renderCard("nav-rail");
  }
  if (a.layout) layoutMode = a.layout.choice;
  if (a.density) densityCap = [0, 2, 4, 7, 10][Math.round(a.density.score)] ?? 4;
  if (a.emphasis) emphasis = a.emphasis.choice;
  const scene = manifest.scenes?.[intent.choice] || {};
  { // 附件:模型 argmax (>0.3);未定时不兜底,已定时退回场景预设——每页都有成熟配套
    let best = "none", bp = 0;
    for (const ctx of Object.keys(manifest.attachments || {})) {
      const p = a["att_" + ctx]?.noul ?? 0;
      if (p > bp) { bp = p; best = ctx; }
    }
    setAttach(bp > 0.3 ? best : (committed ? scene.attach || "none" : "none"));
  }
  { // 场景提示词逐层披露:未定只露第一条(幽灵),已定露下一条(更深引导)
    const hints = scene.hints || [];
    const hint = intent.choice === "explore" ? "" : (hints[committed ? 1 : 0] || hints[0] || "");
    setHint(hint, !committed);
  }
  if (a.intent) {
    $("#mode").textContent = committed ? intent.choice : "";
    input.placeholder = (manifest.prompts || {})[intent.choice] || manifest.prompts?.explore || input.placeholder;
    composer.dataset.cmode = intent.choice;   // 输入框本身也是状态,随意图头名即时变形
  }
  const probs = {};
  const ensure = committed ? (scene.ensure || {}) : {};   // 已定时场景预设保底核心组件:页面总是成型的,模型只加强不缺席
  for (const id of Object.keys(manifest.components))
    probs[id] = Math.max(a["vis_" + id]?.noul ?? 0, ensure[id] ?? 0);
  probs["nav-rail"] = Math.max(probs["nav-rail"] ?? 0, latestText.trim() ? 0.6 : 0);  // 应用壳随内容常驻
  // 布局容量裁剪:非 pin 组件按概率排序放行前 N 个;pin 组件(alert/HUD)只过幽灵阈值
  const cap = {empty: 0, focus: 1, split: 4, dashboard: 9}[layoutMode] ?? 4;
  const limit = Math.min(cap, densityCap);
  const pinned = id => !!manifest.components[id].pin;
  const allowed = new Set(
    Object.entries(probs).filter(([id, p]) => (pinned(id) || ensure[id] != null) && p > GHOST_LO).map(([id]) => id));
  Object.entries(probs).filter(([id]) => !pinned(id)).sort((x, y) => y[1] - x[1])
    .slice(0, limit).filter(([, p]) => p > GHOST_LO).forEach(([id]) => allowed.add(id));
  for (const [id, p] of Object.entries(probs)) {
    // 已定:判定即裁决,p>=组件门槛才实体化,其余退场;未定:概率即透明度(幽灵层)。打断级组件可有更低 solid 门槛
    const gate = manifest.components[id].solid ?? SOLID;
    const want = allowed.has(id) && (!committed || p >= gate);
    setTarget(id, p, want ? (committed ? 1 : p) : 0);
  }
  for (const [id, c] of Object.entries(manifest.components))
    if (c.bind && a["bind_" + id]) setBinding(id, a["bind_" + id].choice);
  // 页面生命周期:已承诺意图切换 = 换页。旧场景卡片错峰退场,新场景错峰进场
  const newScene = committed ? intent.choice : null;
  if (newScene && newScene !== sceneId) {
    let eo = 0, io = 0;
    for (const c of cards.values()) {
      if (c.target === 0 && c.m > 0.05) c.delay = (eo++) * 0.03;
      else if (c.target > 0 && c.m < 0.5) c.delay = 0.14 + (io++) * 0.045;
    }
  }
  sceneId = newScene;
  dirty.layout = dirty.debug = true;
}

function setTarget(id, p, target) {
  let c = cards.get(id);
  if (!c && target > MOUNT_P) c = mount(id);
  if (!c) return;
  c.prob = p; c.target = target;
  c.el.dataset.p = p.toFixed(3); c.el.dataset.target = target.toFixed(3);   // 供自测/debug 读
}

function setBinding(id, key) {
  const c = cards.get(id);
  if (c && c.bound !== key && manifest.datasets[key]) { c.bound = key; renderCard(id); }
}

/* ---------- 输入框的自适应附件 + 场景提示 ---------- */
const attachEl = document.getElementById("attach"), hintEl = document.getElementById("hint");
let attachCtx = "";
function setHint(text, ghost) {
  const on = !!text;
  if ((hintEl.dataset.t || "") !== (text || ""))
    hintEl.innerHTML = on ? `<b>hint</b><span>${esc(text)}</span>` : "";
  hintEl.dataset.t = text || "";
  hintEl.classList.toggle("on", on);
  hintEl.style.opacity = on ? (ghost ? .45 : 1) : 0;
}
function setAttach(ctx) {
  if (ctx === attachCtx) { attachEl.style.opacity = committed ? 1 : .5; return; }
  attachCtx = ctx;
  const on = ctx && ctx !== "none";
  attachEl.innerHTML = on ? buildAttach(ctx) : "";
  attachEl.classList.toggle("on", on);
  attachEl.style.opacity = committed ? 1 : .5;
}

function buildAttach(ctx) {
  const items = manifest.attachments?.[ctx]?.items;
  const head = `<div class="a-head">${ctx}</div>`;
  switch (ctx) {
    case "photos":
      return head + `<div class="a-photos">${(items || []).map(p =>
        `<div class="a-ph" style="--h:${p.h}"><b>${p.time}</b><span>${esc(p.label)}</span></div>`).join("")}</div>`;
    case "news":
      return head + (items || []).map(n =>
        `<div class="a-row"><i>${n.time}</i><b>${esc(n.src)}</b><span>${esc(n.title)}</span></div>`).join("");
    case "logs":
      return head + (items || []).map(l =>
        `<div class="a-row"><i>${l.time}</i><b class="lv-${l.lvl}">${l.lvl}</b><span>${esc(l.msg)}</span></div>`).join("");
    case "tasks": {
      const d = manifest.datasets.tasks;
      return head + d.rows.map(r =>
        `<div class="a-row"><i class="tk ${r[1] === "完成" ? "done" : r[1] === "进行中" ? "doing" : ""}"></i><span>${esc(r[0])}</span><b>${r[1]}</b></div>`).join("");
    }
    case "datasets":
      return head + `<div class="a-chips">${Object.keys(manifest.datasets).map(k =>
        `<button class="a-chip" onclick="window.__rebind('${k}')">${k}</button>`).join("")}</div>`;
    case "moments":
      return head + (items || []).map(m =>
        `<div class="a-row"><i>${m.time}</i><b class="who" style="--h:${m.hue}">${esc(m.who)}</b><span>${esc(m.text)}</span><b>${m.meta}</b></div>`).join("");
    case "services":
      return head + `<div class="a-chips">${(items || []).map(s =>
        `<span class="a-svc ${s.ok ? "ok" : "bad"}"><i></i>${s.name}</span>`).join("")}</div>`;
    default: return "";
  }
}
window.__rebind = key => {
  for (const [id] of cards) if (manifest.components[id].bind) setBinding(id, key);
};

/* ---------- DOM ---------- */
function mount(id) {
  const el = document.createElement("div");
  el.className = "card"; el.dataset.id = id;
  stage.appendChild(el);
  const c = {id, el, m: 0, target: 0, prob: 0, bound: defaultBinding(id), rect: null, applied: "", delay: 0};
  cards.set(id, c); renderCard(id);
  dirty.layout = true;
  return c;
}

function defaultBinding(id) {
  const b = manifest.components[id].bind;
  return b ? Object.keys(b.options)[0] : null;
}

/* ---------- 应用壳分栏:nav | main | side ----------
 * 固定三栏(X 式应用版面):左导航栏、中主列、右信息列;
 * 顶/底条带横贯全宽;栏内卡片按 minH 权重铺满;窄屏退回单列。
 */
const PAD = 20, GAP = 14, GAP_IN = 12, COL_GAP = 26;
const NAV_W = 200, SIDE_W = 292;
function zoneOf(id) {
  const z = manifest.components[id].zone;
  if (z === "nav" || z === "top" || z === "bottom") return z;
  if (id === emphasis) return "main";
  return z || "main";
}

function pack() {
  const W = stage.clientWidth, H = stage.clientHeight;
  const order = Object.keys(manifest.components);
  const vis = [...cards.values()].filter(c => c.target > 0 || c.m > MOUNT_P)
    .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
  const tops  = vis.filter(c => zoneOf(c.id) === "top");
  const bots  = vis.filter(c => zoneOf(c.id) === "bottom");
  const navs  = vis.filter(c => zoneOf(c.id) === "nav");
  let mains   = vis.filter(c => zoneOf(c.id) === "main");
  let sides   = vis.filter(c => zoneOf(c.id) === "side");
  const Wi = W - PAD * 2;

  let y = PAD;
  for (const c of tops) { c.rect = {x: PAD, y, w: Wi, h: STRIP_H}; y += STRIP_H + GAP; }
  let by = H - PAD;
  for (const c of bots) { by -= STRIP_H; c.rect = {x: PAD, y: by, w: Wi, h: STRIP_H}; by -= GAP; }
  const midY = y, midH = Math.max(0, by - midY);   // 条带循环里已含间隔

  // 栏内卡片给"自然高"(minH*66)顶对齐堆叠,超出列高才按比例压缩;
  // 剩余高度留白——卡片自己找位置,不被撑成比例失调的大块
  const NAT = 66;
  const stack = (list, x0, w, y0, h) => {
    const hs = list.map(c => Math.max(52, (manifest.components[c.id].minH || 1) * NAT));
    const gaps = GAP_IN * (list.length - 1);
    const need = hs.reduce((s, v) => s + v, 0) + gaps;
    const k = need > h ? (h - gaps) / Math.max(1, need - gaps) : 1;
    let cy = y0;
    list.forEach((c, i) => {
      const ch = Math.round(hs[i] * k);
      c.rect = {x: x0, y: Math.round(cy), w, h: Math.max(0, ch)};
      cy += ch + GAP_IN;
    });
  };

  const narrow = Wi < 980;
  if (narrow) {                                     // 窄屏:导航变横条,侧列并入主列
    for (const c of navs) { c.el.classList.add("flat"); c.rect = {x: PAD, y, w: Wi, h: 46}; y += 46 + GAP_IN; }
    stack([...mains, ...sides], PAD, Wi, y, Math.max(0, by - y));
    return;
  }
  for (const c of navs) c.el.classList.remove("flat");

  let x = PAD;
  if (navs.length) { navs[0].rect = {x, y: midY, w: NAV_W, h: midH}; x += NAV_W + COL_GAP; }
  if (!mains.length) { mains = sides; sides = []; } // 主列空时侧列内容进主列
  const sideW = sides.length ? SIDE_W : 0;
  const mainW = Wi - (x - PAD) - sideW - (sides.length ? COL_GAP : 0);
  if (mains.length) stack(mains, x, mainW, midY, midH);
  if (sides.length) stack(sides, x + mainW + COL_GAP, sideW, midY, midH);
}

/* ---------- 渲染循环 ---------- */
let last = performance.now();
function tick(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (dirty.layout) { pack(); dirty.layout = false; }
  for (const c of [...cards.values()]) {
    if (c.delay > 0) c.delay -= dt;                 // 场景切换的错峰调度
    else {
      const tau = c.target > c.m ? TAU_IN : TAU_OUT;
      c.m += (c.target - c.m) * (1 - Math.exp(-dt / tau));
    }
    if (c.target === 0 && c.m < MOUNT_P) { c.el.remove(); cards.delete(c.id); dirty.layout = true; continue; }
    const r = c.rect; if (!r) continue;
    const m = c.m, lift = 1 - m;
    // left/top/宽高走 CSS transition(布局变化平滑);transform 每帧直写(材料化进度)
    const key = `${r.x}|${r.y}|${r.w}|${r.h}`;
    if (c.applied !== key) {
      c.applied = key;
      c.el.style.transition = `left .48s ${EASE}, top .48s ${EASE}, width .48s ${EASE}, height .48s ${EASE}, box-shadow .3s, border-color .3s`;
      c.el.style.left = r.x + "px"; c.el.style.top = r.y + "px";
      c.el.style.width = r.w + "px"; c.el.style.height = r.h + "px";
    }
    // 进场方式按组件声明:条带横向扫入,主区弹簧,其余缓升
    const enter = manifest.components[c.id].enter;
    if (enter === "wipe") c.el.style.clipPath = `inset(0 ${(lift * 100).toFixed(1)}% 0 0)`;
    else c.el.style.clipPath = "none";
    c.el.style.transform = enter === "wipe" ? "none"
      : enter === "zoom" ? `scale(${(0.94 + 0.06 * m).toFixed(4)})`
      : enter === "spring" ? `translateY(${(lift * 14).toFixed(1)}px) scale(${(0.97 + 0.03 * m).toFixed(4)})`
      : `translateY(${(lift * 8).toFixed(1)}px)`;
    c.el.style.opacity = m.toFixed(3);
    c.el.style.setProperty("--co", Math.pow(m, 1.5).toFixed(3));   // 字比线慢一点出现
    // 模糊只属于"运动过程":静止(m≈target)必须全清晰
    const motion = Math.abs(c.target - c.m);
    c.el.style.filter = motion > 0.015 ? `blur(${Math.min(4, motion * 7).toFixed(1)}px)` : "none";
    c.el.style.zIndex = c.id === emphasis ? 5 : 1;
    const ghosting = m < SOLID;
    c.el.classList.toggle("ghost", ghosting);
    c.el.classList.toggle("emph", c.id === emphasis && !ghosting);
    // 边界线随 m 拉出:幽灵=虚线轮廓;实体=发丝线(强调区用 accent)
    if (c.id === "nav-rail") {                      // 导航栏是壳的一部分:只有右缘发丝线
      c.el.style.outline = "none"; c.el.style.boxShadow = "none";
      c.el.style.borderRight = `1px ${ghosting ? "dashed" : "solid"} rgba(120,140,180,${(m * (ghosting ? 0.55 : 0.45)).toFixed(3)})`;
    } else if (ghosting) {
      c.el.style.boxShadow = "none";
      c.el.style.outline = `1px dashed rgba(120,140,190,${(m * 0.85).toFixed(3)})`;
      c.el.style.outlineOffset = "-4px";
    } else {
      c.el.style.outline = "none";
      const col = c.id === emphasis ? "94,234,212" : "120,140,180";
      c.el.style.boxShadow =
        `inset 0 0 0 1px rgba(${col},${(m * 0.75).toFixed(3)})` +
        (c.id === "alert-banner" ? `, inset 3px 0 0 rgba(255,143,143,${(m * 0.9).toFixed(3)})` : "");
    }
  }
  if (dirty.debug) { renderDebug(); dirty.debug = false; }
  requestAnimationFrame(tick);
}

/* ---------- 卡片内容(FUI 骨架 + 数据细节) ---------- */
function esc(s) { return s.replace(/[&<>"]/g, ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch])); }
function ds(key) { return manifest.datasets[key] || manifest.datasets.sales; }

function chrome(id, tag) {
  return tag ? `<div class="fui-tag">${esc(tag)}</div>` : "";
}

function renderCard(id) {
  const c = cards.get(id); if (!c) return;
  const el = c.el, t = latestText;
  const lines = t.split("\n").map(s => s.trim()).filter(Boolean);
  const first = lines[0] || "", lastLine = lines[lines.length - 1] || "";
  switch (id) {
    case "nav-rail": {
      const labels = manifest.questions.intent.labels || {};
      const probs = intent.probabilities || {};
      el.innerHTML = `<div class="nav-list">${Object.entries(labels).map(([k, zh]) =>
        `<div class="ni ${k === intent.choice ? "on" : ""}"><i></i><span>${esc(zh)}</span><b>${Math.round((probs[k] || 0) * 100)}</b></div>`).join("")}
        </div><div class="rail-foot">nav · kev</div>`;
      break;
    }
    case "intent-chip": {
      const seg = Array.from({length: 10}, (_, i) =>
        `<i class="${i < Math.round(intent.confidence * 10) ? "on" : ""}"></i>`).join("");
      el.innerHTML = chrome(id, "intent") + `<div class="c-title">detected intent</div>
        <div class="chip"><span class="val">${esc(intent.choice || "—")}</span>
        <span class="segbar">${seg}</span>
        <span class="c-sub">${(intent.confidence * 100) | 0}%</span></div>`;
      break;
    }
    case "summary-card": {
      const zh = /[一-鿿]/.test(t), words = t.split(/\s+/).filter(Boolean).length;
      el.innerHTML = chrome(id, "input") + `<div class="c-title">input summary</div>
        <div class="kv"><span>chars</span><b>${t.length}</b></div>
        <div class="kv"><span>lines</span><b>${lines.length}</b></div>
        <div class="kv"><span>lang</span><b>${zh ? "zh-CN" : "latin"}</b></div>
        <div class="kv"><span>words</span><b>${words}</b></div>`;
      break;
    }
    case "metric-card": {
      const d = ds(c.bound), s = d.series, mx = Math.max(...s), mn = Math.min(...s);
      const sp = s.map((v, i) => `${(i / (s.length - 1)) * 100},${20 - ((v - mn) / (mx - mn || 1)) * 18}`).join(" ");
      el.innerHTML = chrome(id, c.bound) + `<div class="c-title">${esc(d.title)}</div>
        <div class="c-big">${d.unit}${d.latest}</div>
        <div class="c-sub trend-${d.trend}">${d.trend === "up" ? "▲ 上升" : "▼ 下降"}</div>
        <svg class="spark" viewBox="0 0 100 22" preserveAspectRatio="none">
          <polyline points="${sp}" fill="none" stroke="var(--accent-2)" stroke-width="1" vector-effect="non-scaling-stroke"/></svg>`;
      break;
    }
    case "chart-card": {
      const d = ds(c.bound), s = d.series, max = Math.max(...s), min = Math.min(...s);
      const pts = s.map((v, i) => `${(i / (s.length - 1)) * 100},${36 - ((v - min) / (max - min || 1)) * 32}`).join(" ");
      const grid = [8, 16, 24, 32].map(y => `<line x1="0" x2="100" y1="${y}" y2="${y}" stroke="#1b2332" stroke-width="0.3"/>`).join("");
      const ly = 36 - ((s[s.length - 1] - min) / (max - min || 1)) * 32;
      el.innerHTML = chrome(id, c.bound) + `<div class="c-title">${esc(d.title)} · trend</div>
        <svg viewBox="0 0 100 40" preserveAspectRatio="none" class="chart">
          ${grid}<polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="1.4" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>
          <circle cx="100" cy="${ly}" r="1.8" fill="var(--accent)"/></svg>
        <div class="fui-axis">${d.rows.map(r => `<span>${esc(String(r[0]))}</span>`).join("")}</div>`;
      break;
    }
    case "table-card": {
      const d = ds(c.bound);
      el.innerHTML = chrome(id, c.bound) + `<div class="c-title">${esc(d.title)} · detail</div>
        <table class="rows"><tr class="th"><td>seq</td><td>item</td><td>val</td></tr>
        ${d.rows.map((r, i) => `<tr><td class="seq">${String(i + 1).padStart(2, "0")}</td><td>${esc(String(r[0]))}</td><td>${esc(String(r[1]))}</td></tr>`).join("")}</table>`;
      break;
    }
    case "alert-banner": {
      el.classList.add("banner");
      const ts = new Date().toLocaleTimeString("en-GB");
      el.innerHTML = `<span class="dot"></span><div class="btxt">${esc(first || "需要关注")}</div><div class="fui-tag">alrt · ${ts}</div>`;
      break;
    }
    case "action-bar": {
      const acts = {"analyze-data": ["导出报表", "下钻明细"], "report-issue": ["创建工单", "通知值班"], "plan-work": ["生成看板", "排期"], "write-document": ["润色", "归档"], "monitor-status": ["全屏监控", "设告警"], "explore": ["继续"]}[intent.choice] || ["继续"];
      el.innerHTML = chrome(id, "exec") + `<div class="actions"><span class="fui-lbl">exec</span>${acts.map((a, i) => `<button class="btn${i === 0 ? " primary" : ""}">${a}</button>`).join("")}<button class="btn">更多…</button></div>`;
      break;
    }
    case "timeline-card": {
      const steps = lines.filter(l => /^[-*\d•·]/.test(l)).map(l => l.replace(/^[-*\d•·.\s]+/, ""));
      const show = steps.length ? steps : ["起草", "细化", "评审", "发布"];
      el.innerHTML = chrome(id, "seq") + `<div class="c-title">timeline</div><div class="tl">${show.slice(0, 6).map((s, i) => `<div class="step"><em>${String(i + 1).padStart(2, "0")}</em><i></i><span>${esc(s)}</span></div>`).join("")}</div>`;
      break;
    }
    case "note-card":
      el.innerHTML = chrome(id, "note") + `<div class="c-title">note</div><div class="note">${esc(lastLine || first || "…")}</div>`;
      break;
    case "feed-card": {
      const items = manifest.attachments?.moments?.items || [];
      el.innerHTML = chrome(id, "feed") + `<div class="c-title">moments · feed</div>` +
        items.map(m => `<div class="feed-row"><i class="av" style="--h:${m.hue}">${esc(m.who[0])}</i>
          <div class="fbody"><div class="fhead"><b>${esc(m.who)}</b><i>${m.time}</i></div>
          <div class="ftext">${esc(m.text)}</div></div><b class="fmeta">${m.meta}</b></div>`).join("");
      break;
    }
    case "hero-stat": {
      const d = ds(c.bound);
      el.innerHTML = chrome(id, c.bound) + `<div class="c-title">${esc(d.title)}</div>
        <div class="hero-wrap"><i class="hl"></i><div class="hero-num">${d.unit}${d.latest}</div><i class="hl"></i></div>`;
      break;
    }
    case "progress-card": {
      const d = manifest.datasets.tasks, done = d.rows.filter(r => r[1] === "完成").length, pc = Math.round(done / d.rows.length * 100);
      el.innerHTML = chrome(id, "tasks") + `<div class="c-title">progress</div><div class="c-big">${pc}<span class="c-sub">%</span></div>
        <div class="c-sub">${done}/${d.rows.length} 完成</div><div class="prog"><i style="width:${pc}%"></i></div>`;
      break;
    }
  }
}

/* ---------- mock 决策源(无 GPU 时调手感) ---------- */
const MOCK_KW = {
  "metric-card": /指标|metric|kpi|数字|number|营收|sales/i,
  "chart-card": /图|chart|趋势|trend|走势|曲线/i,
  "table-card": /表|table|明细|列表|rows/i,
  "alert-banner": /警告|alert|error|错误|故障|挂了|紧急/i,
  "action-bar": /操作|action|button|执行|导出/i,
  "timeline-card": /时间线|timeline|步骤|计划|plan|流程/i,
  "note-card": /备注|note|记住|quote|记一下/i,
  "hero-stat": /hero|大字|总数|一共/i,
  "progress-card": /进度|progress|完成度/i,
  "summary-card": /总结|summary|统计/i,
  "feed-card": /朋友|大家|社交|feed|moments|朋友圈/i,
  "intent-chip": /./,
};
async function mockDecide() {
  await new Promise(r => setTimeout(r, 120 + Math.random() * 80));
  const answers = {};
  for (const [id, kw] of Object.entries(MOCK_KW)) {
    const hit = kw.test(latestText);
    const noise = 0.25 + (hit ? 0.55 : 0) + Math.random() * 0.15;
    answers["vis_" + id] = {type: "noul", noul: Math.min(0.98, latestText.length > 2 ? noise : noise * 0.4)};
  }
  const intentMap = [["analyze-data", /数据|指标|销售|营收|data|metric/i], ["report-issue", /错误|故障|bug|挂了|alert/i], ["plan-work", /计划|任务|步骤|plan|todo/i], ["monitor-status", /监控|状态|monitor|latency/i], ["write-document", /写|文章|文档|note|draft/i], ["check-social", /朋友|大家|谁.*咋样|friend|social/i]];
  const top = intentMap.find(([, kw]) => kw.test(latestText));
  const ip = {}; for (const [k] of intentMap) ip[k] = 0.05; ip.explore = 0.1;
  if (top) ip[top[0]] = 0.7; else ip.explore = 0.6;
  answers.intent = {type: "choice", choice: top ? top[0] : "explore", confidence: top ? 0.7 : 0.3, probabilities: ip};
  const ctxMap = [["photos", /日记|照片|今天.*拍|journal|diary/i], ["news", /文章|新闻|报道|article|news|essay/i], ["logs", /错误|日志|bug|报错|log/i], ["tasks", /任务|计划|安排|todo|task/i], ["datasets", /数据|营收|sales|traffic|chart/i], ["services", /服务|监控|status|service/i], ["moments", /朋友|大家|谁.*咋样|friend|social|朋友圈/i]];
  for (const [ctx, kw] of ctxMap) answers["att_" + ctx] = {type: "noul", noul: kw.test(latestText) ? 0.8 : 0.15};
  answers.layout = {type: "choice", choice: latestText.length < 4 ? "empty" : (Object.values(answers).filter(a => a.noul > SOLID).length > 3 ? "dashboard" : "split"), probabilities: {}};
  answers.density = {type: "score", score: latestText.length < 4 ? 0 : 3, probabilities: {}, legend: {}};
  answers.emphasis = {type: "choice", choice: "none", probabilities: {}};
  for (const [id, c] of Object.entries(manifest.components))
    if (c.bind) answers["bind_" + id] = {type: "choice", choice: /延迟|latency/.test(latestText) ? "latency" : /错误|error/.test(latestText) ? "errors" : "sales", probabilities: {}};
  return {answers};
}

/* ---------- 状态徽标 & debug ---------- */
function setConn(st, latency) {
  conn.className = "conn " + (MOCK ? "conn-mock" : st === "on" ? "conn-on" : "conn-off");
  conn.textContent = MOCK ? `kev · mock` : st === "on" ? `kev · ${Math.round(latency)}ms` : "kev · offline";
}
function renderDebug() {
  const rows = [`<div class="d-row"><b>layout</b><b>${layoutMode} · cap ${densityCap}</b></div>`,
    `<div class="d-row"><b>intent</b><b>${intent.choice} ${(intent.confidence * 100) | 0}% ${committed ? "· COMMITTED" : ""}</b></div>`];
  for (const [id, c] of [...cards.entries()].sort((a, b) => b[1].prob - a[1].prob))
    rows.push(`<div class="d-row"><span>${id}</span><b>${c.prob.toFixed(2)} → m ${c.m.toFixed(2)}</b></div><div class="d-bar"><i style="width:${c.prob * 100}%"></i></div>`);
  debug.innerHTML = rows.join("");
}

function clearScene() {
  committed = false; layoutMode = "empty"; sceneId = null;
  intent = {choice: "explore", confidence: 0};
  setAttach("none"); attachCtx = "";
  setHint("");
  attachEl.innerHTML = ""; attachEl.classList.remove("on");
  $("#mode").textContent = "";
  input.placeholder = manifest.prompts?.explore || "";
  composer.dataset.cmode = "";
  for (const c of cards.values()) { c.prob = 0; c.target = 0; c.el.dataset.p = "0"; c.el.dataset.target = "0"; }
  dirty.layout = dirty.debug = true;
}

/* ---------- 事件 ---------- */
let timer = null;
input.addEventListener("input", () => {
  latestText = input.value;
  const empty = latestText.trim() === "";
  document.getElementById("app").classList.toggle("idle", empty);
  if (empty) { clearTimeout(timer); clearScene(); return; }   // 清空 → 收回舞台,不再问模型
  for (const id of ["summary-card", "note-card", "timeline-card", "alert-banner"]) renderCard(id); // 本地派生属性即时刷新
  clearTimeout(timer); timer = setTimeout(decide, DEBOUNCE_MS);
});
addEventListener("keydown", e => { if (e.key === "`") debug.classList.toggle("hidden"); });
addEventListener("resize", () => { dirty.layout = true; });

/* ---------- boot ---------- */
(async () => {
  manifest = await (await fetch("manifest.json")).json();
  document.getElementById("app").classList.add("idle");
  setConn(MOCK ? "mock" : "off");
  requestAnimationFrame(tick);
})();
