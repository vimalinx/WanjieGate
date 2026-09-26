/* WanjieGate v1 — 决策模型驱动的自适应界面
 * 渲染循环(60fps) 与 决策循环(~3Hz) 解耦:KEV 只产出"目标态",
 * 每个组件的 materialize 标量 m 通过弹簧趋近目标,概率直接映射为透明度。
 */
"use strict";

const $ = s => document.querySelector(s);
const stage = $("#stage"), input = $("#input"), conn = $("#conn"), pulse = $("#pulse"), debug = $("#debug");

const MOCK = new URLSearchParams(location.search).has("mock");
const DEBOUNCE_MS = 320;
const TAU_IN = 0.16, TAU_OUT = 0.5;        // 进场快、退场慢(秒)
const MOUNT_P = 0.03, GHOST_LO = 0.15, SOLID = 0.55;
const STRIP_H = 54;
const EASE = "cubic-bezier(.22,1.2,.3,1)";

let manifest = null;
let cards = new Map();      // id -> {el, m, target, prob, bound, rect, applied}
let layoutMode = "empty", densityCap = 1, emphasis = "none";
let intent = {choice: "explore", confidence: 0};
let committed = false;      // 意图已定:摘幽灵态,卡片直奔实体
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
    renderCard("intent-chip"); renderCard("action-bar");
  }
  if (a.layout) layoutMode = a.layout.choice;
  if (a.density) densityCap = [0, 2, 4, 7, 10][Math.round(a.density.score)] ?? 4;
  if (a.emphasis) emphasis = a.emphasis.choice;
  const probs = {};
  for (const id of Object.keys(manifest.components))
    probs[id] = a["vis_" + id]?.noul ?? 0;
  // 布局容量裁剪:非 pin 组件按概率排序放行前 N 个;pin 组件(alert/HUD)只过幽灵阈值
  const cap = {empty: 0, focus: 1, split: 4, dashboard: 9}[layoutMode] ?? 4;
  const limit = Math.min(cap, densityCap);
  const pinned = id => !!manifest.components[id].pin;
  const allowed = new Set(
    Object.entries(probs).filter(([id, p]) => pinned(id) && p > GHOST_LO).map(([id]) => id));
  Object.entries(probs).filter(([id]) => !pinned(id)).sort((x, y) => y[1] - x[1])
    .slice(0, limit).filter(([, p]) => p > GHOST_LO).forEach(([id]) => allowed.add(id));
  for (const [id, p] of Object.entries(probs)) {
    // 已定:判定即裁决,p>=SOLID 才实体化,其余退场;未定:概率即透明度(幽灵层)
    const want = allowed.has(id) && (!committed || p >= SOLID);
    setTarget(id, p, want ? (committed ? 1 : p) : 0);
  }
  for (const [id, c] of Object.entries(manifest.components))
    if (c.bind && a["bind_" + id]) setBinding(id, a["bind_" + id].choice);
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

/* ---------- DOM ---------- */
function mount(id) {
  const el = document.createElement("div");
  el.className = "card"; el.dataset.id = id;
  stage.appendChild(el);
  const c = {id, el, m: 0, target: 0, prob: 0, bound: defaultBinding(id), rect: null, applied: ""};
  cards.set(id, c); renderCard(id);
  dirty.layout = true;
  return c;
}

function defaultBinding(id) {
  const b = manifest.components[id].bind;
  return b ? Object.keys(b.options)[0] : null;
}

/* ---------- 空间分划:留白 + 主附分区 ----------
 * 顶/底条带与中部主区/侧栏之间留 16-20px 空白;组内区域间 10px;
 * 每条边界都是独立的描边矩形,线不互相连接。
 */
const PAD = 20, GUT = 20, GAP = 14, GAP_IN = 10;
function zoneOf(id) {
  if (id === "alert-banner") return "top";
  if (id === "action-bar") return "bottom";
  if (id === emphasis) return "main";
  const d = manifest.components[id];
  return (d.minH >= 3 || d.span >= 6) ? "main" : "rail";
}

function pack() {
  const W = stage.clientWidth, H = stage.clientHeight;
  const order = Object.keys(manifest.components);
  const vis = [...cards.values()].filter(c => c.target > 0 || c.m > MOUNT_P)
    .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
  const tops  = vis.filter(c => zoneOf(c.id) === "top");
  const bots  = vis.filter(c => zoneOf(c.id) === "bottom");
  const mains = vis.filter(c => zoneOf(c.id) === "main");
  const rails = vis.filter(c => zoneOf(c.id) === "rail");
  const Wi = W - PAD * 2, Hi = H - PAD * 2;

  let y = PAD;
  for (const c of tops) { c.rect = {x: PAD, y, w: Wi, h: STRIP_H}; y += STRIP_H + GAP; }
  let by = H - PAD;
  for (const c of bots) { by -= STRIP_H; c.rect = {x: PAD, y: by, w: Wi, h: STRIP_H}; by -= GAP; }
  const midY = y, midH = Math.max(0, by - midY);   // 条带循环里已含间隔

  const narrow = Wi < 720;
  let mainW = Wi;
  if (mains.length && rails.length && !narrow)
    mainW = Math.round(Wi * (layoutMode === "split" ? 0.52 : 0.60));
  else if (!mains.length) mainW = 0;

  // 一列区域内按 minH 权重铺满,组内 10px 间隔,最后一个吃掉舍入余量
  const stack = (list, x0, w, y0, h) => {
    const tot = list.reduce((s, c) => s + (manifest.components[c.id].minH || 1), 0);
    let cy = y0;
    list.forEach((c, i) => {
      const ch = i === list.length - 1 ? y0 + h - Math.round(cy)
        : Math.round((h - GAP_IN * (list.length - 1)) * (manifest.components[c.id].minH || 1) / tot);
      c.rect = {x: x0, y: Math.round(cy), w, h: Math.max(0, ch)};
      cy += ch + GAP_IN;
    });
  };
  if (narrow) stack([...mains, ...rails], PAD, Wi, midY, midH);
  else {
    if (mains.length) stack(mains, PAD, mainW, midY, midH);
    if (rails.length) stack(rails, mains.length ? PAD + mainW + GUT : PAD, mains.length ? Wi - mainW - GUT : Wi, midY, midH);
  }
}

/* ---------- 渲染循环 ---------- */
let last = performance.now();
function tick(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (dirty.layout) { pack(); dirty.layout = false; }
  for (const c of [...cards.values()]) {
    const tau = c.target > c.m ? TAU_IN : TAU_OUT;
    c.m += (c.target - c.m) * (1 - Math.exp(-dt / tau));
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
    if (ghosting) {
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
  const idx = String(Object.keys(manifest.components).indexOf(id) + 1).padStart(2, "0");
  return `<i class="fc tl"></i><i class="fc tr"></i><i class="fc bl"></i><i class="fc br"></i>` +
    `<div class="fui-idx">${idx}</div>` + (tag ? `<div class="fui-tag">${esc(tag)}</div>` : "");
}

function renderCard(id) {
  const c = cards.get(id); if (!c) return;
  const el = c.el, t = latestText;
  const lines = t.split("\n").map(s => s.trim()).filter(Boolean);
  const first = lines[0] || "", lastLine = lines[lines.length - 1] || "";
  switch (id) {
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
      el.innerHTML = `<i class="fc tl"></i><i class="fc tr"></i><i class="fc bl"></i><i class="fc br"></i>
        <span class="dot"></span><div class="btxt">${esc(first || "需要关注")}</div><div class="fui-tag">alrt · ${ts}</div>`;
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
  const intentMap = [["analyze-data", /数据|指标|销售|营收|data|metric/i], ["report-issue", /错误|故障|bug|挂了|alert/i], ["plan-work", /计划|任务|步骤|plan|todo/i], ["monitor-status", /监控|状态|monitor|latency/i], ["write-document", /写|文章|文档|note|draft/i]];
  const top = intentMap.find(([, kw]) => kw.test(latestText));
  const ip = {}; for (const [k] of intentMap) ip[k] = 0.05; ip.explore = 0.1;
  if (top) ip[top[0]] = 0.7; else ip.explore = 0.6;
  answers.intent = {type: "choice", choice: top ? top[0] : "explore", confidence: top ? 0.7 : 0.3, probabilities: ip};
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
  committed = false; layoutMode = "empty";
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
