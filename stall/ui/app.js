"use strict";
/* The page. It holds no truth of its own: every render is a picture of
   the last /api/state the server sent, and every button is a POST that
   comes back with the next one. The one piece of local state that is
   not the server's is which panels you have open.

   There is no reload button: edited agent.py is picked up by stopping
   the server and running `stall chat` again. */

const esc = s => String(s).replace(/[&<>"]/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const money = c => "$" + (c / 100).toFixed(2);
const kt = n => (n || 0).toLocaleString();

/* ═════════════ the two faces ═════════════ */
/* Her face is the one thing on this page the server does not send. The
   counter hands over an id and nothing else, so the colours are read
   off the id itself: a regular who comes back comes back looking like
   herself, and the next customer is visibly not her. */
const SKIN = ["#e6ab77", "#d99a63", "#f2c69b", "#c08349"];
const HAIR = ["#2f2a26", "#4a2f22", "#17140f", "#6d5a45"];
const TOP = [["#e0607e", "#ffd9e4", "#f3c9d6"], ["#5b9ec9", "#dcefff", "#a9d0e8"],
             ["#5fa86e", "#ddf3e0", "#a6d5b0"], ["#d9a13c", "#ffeec2", "#f0cd8c"],
             ["#9a7ac9", "#ece0fb", "#c7b4e6"]];
const hash = t => [...String(t)].reduce((a, c) => (a * 33 + c.charCodeAt(0)) >>> 0, 5381);

const CUSTOMER = (id) => {
  const h = hash(id);
  const skin = SKIN[h % SKIN.length], hair = HAIR[(h >>> 3) % HAIR.length];
  const [top, dot, cuff] = TOP[(h >>> 6) % TOP.length];
  return `<svg viewBox="60 40 200 300" aria-hidden="true">
  <g class="cb" stroke-linejoin="round">
    <path d="M110 192 q40-17 80 0 q15 80 9 170 q-49 15-98 0 q-6-91 9-170z" fill="${top}" stroke="#1e1811" stroke-width="4"/>
    <g fill="${dot}" opacity=".9"><circle cx="130" cy="228" r="5"/><circle cx="152" cy="248" r="5.5"/>
      <circle cx="176" cy="222" r="4.5"/><circle cx="122" cy="266" r="4"/></g>
    <path d="M132 188 l18 22 -10 14 -16-24z" fill="${cuff}" stroke="#1e1811" stroke-width="4"/>
    <path d="M168 188 l-18 22 10 14 16-24z" fill="${cuff}" stroke="#1e1811" stroke-width="4"/>
    <path d="M136 160 h28 v36 q-14 8-28 0z" fill="${skin}" stroke="#1e1811" stroke-width="4"/>
    <path d="M112 106 q-23 2-20 26 q3 23 22 16z" fill="${skin}" stroke="#1e1811" stroke-width="4"/>
    <path d="M188 106 q23 2 20 26 q-3 23-22 16z" fill="${skin}" stroke="#1e1811" stroke-width="4"/>
    <path d="M112 110 q0-42 38-42 t38 42 v20 q0 42-38 42 t-38-42z" fill="${skin}" stroke="#1e1811" stroke-width="4"/>
    <path d="M110 112 q-6-52 40-56 q46 4 40 56 q-4-12-10-16 q-2 10-8 12 q1-14-6-20 q-4 10-12 12 q0-12-8-16
             q-4 10-14 12 q-1-11-8-14 q-6 6-6 18 q-5 2-8 12z" fill="${hair}" stroke="#1e1811" stroke-width="4"/>
    <circle cx="118" cy="76" r="11" fill="${hair}" stroke="#1e1811" stroke-width="4"/>
    <circle cx="150" cy="62" r="12" fill="${hair}" stroke="#1e1811" stroke-width="4"/>
    <circle cx="182" cy="76" r="11" fill="${hair}" stroke="#1e1811" stroke-width="4"/>
    <circle cx="132" cy="120" r="14" fill="#ffffff" opacity=".18" stroke="#17130f" stroke-width="4"/>
    <circle cx="168" cy="120" r="14" fill="#ffffff" opacity=".18" stroke="#17130f" stroke-width="4"/>
    <path d="M146 120 h8" stroke="#17130f" stroke-width="4" stroke-linecap="round"/>
    <circle cx="132" cy="120" r="4" fill="#1e1811"/><circle cx="168" cy="120" r="4" fill="#1e1811"/>
    <path d="M120 100 q12-6 22-2 M178 100 q-12-6-22-2" stroke="#1e1811" stroke-width="3.6" fill="none" stroke-linecap="round"/>
    <path d="M138 148 q12 8 24 0" stroke="#1e1811" stroke-width="3.6" fill="none" stroke-linecap="round"/>
  </g></svg>`;
};

/* Tin Kaki — the round-3 winner, cropped to a bust for the side rail. */
const BOT_TIN=(mood)=>`<svg viewBox="60 30 200 280" aria-hidden="true">
<g class="cb" stroke-linejoin="round">
  <rect x="106" y="196" width="108" height="176" rx="16" fill="#c8a24a" stroke="#1e1811" stroke-width="4"/>
  <rect x="118" y="216" width="52" height="34" rx="4" fill="#241d13" stroke="#1e1811" stroke-width="4"/>
  <g class="tick" fill="#7ff0d8"><rect x="124" y="224" width="8" height="18"/><rect x="136" y="230" width="8" height="12"/>
    <rect x="148" y="220" width="8" height="22"/><rect x="160" y="232" width="4" height="10"/></g>
  <path d="M126 254 q34 10 68 0 l6 60 q-40 10-80 0z" fill="#f2ece0" stroke="#1e1811" stroke-width="4"/>
  <path d="M118 262 h84" stroke="#a8231c" stroke-width="9" fill="none"/>
  <rect x="146" y="176" width="28" height="24" fill="#8d949c" stroke="#1e1811" stroke-width="4"/>
  <rect x="100" y="86" width="120" height="94" rx="18" fill="#d9dde1" stroke="#1e1811" stroke-width="4"/>
  <rect x="106" y="92" width="42" height="82" rx="14" fill="#ffffff" opacity=".45"/>
  <rect x="114" y="104" width="92" height="46" rx="9" fill="#141b1e" stroke="#1e1811" stroke-width="4"/>
  ${mood==="err"
    ? `<g stroke="#ff6b5a" stroke-width="7" stroke-linecap="round">
         <path d="M132 118 l20 20 M152 118 l-20 20"/><path d="M170 118 l20 20 M190 118 l-20 20"/></g>`
    : `<g class="blinkeye" style="transform-origin:160px 127px">
         <circle cx="141" cy="127" r="11" fill="#7ff0d8"/><circle cx="185" cy="127" r="11" fill="#7ff0d8"/>
         <circle cx="145" cy="123" r="3.4" fill="#ffffff"/><circle cx="189" cy="123" r="3.4" fill="#ffffff"/></g>`}
  <path d="M134 162 q26 12 52 0" stroke="#5f676f" stroke-width="5" fill="none" stroke-linecap="round"/>
  <rect x="88" y="112" width="14" height="34" rx="5" fill="#8d949c" stroke="#1e1811" stroke-width="4"/>
  <rect x="218" y="112" width="14" height="34" rx="5" fill="#8d949c" stroke="#1e1811" stroke-width="4"/>
  <path d="M160 86 v-22" stroke="#1e1811" stroke-width="5"/>
  <circle cx="160" cy="56" r="11" fill="${mood==="err"?"#ff6b5a":"#ffd23f"}" stroke="#1e1811" stroke-width="4"/>
  <path d="M104 90 q56-34 112 0 q-6-40-56-40 t-56 40z" fill="#a8231c" stroke="#1e1811" stroke-width="4"/>
  <path d="M96 88 h128 q6 0 6 6 t-6 6 h-128 q-6 0-6-6 t6-6z" fill="#7c1d17" stroke="#1e1811" stroke-width="4"/>
</g></svg>`;


/* ═════════════ state ═════════════ */
const KINDS = [["llm", "LLM"], ["tool", "TOOL"], ["print", "PRINT"],
               ["world", "WORLD"], ["skill", "SKILL"], ["mem", "MEM"],
               ["file", "FILE"], ["raise", "RAISE"]];

const S = {
  data: null, draft: "", busy: false, pendingText: null, dead: false,
  modal: false, focus: null, submitOpen: false, toast: null,
  historyOpen: false, historyData: null,
  filters: Object.fromEntries(KINDS.map(([k]) => [k, true])),
};

const app = document.getElementById("app");
const D = () => S.data || {};
const cid = () => D().customer_id || "";
const turns = () => D().turns || [];
const pending = () => (S.busy ? { you: S.pendingText } : null);
const board = () => D().board || {};
const stall = () => D().stall || {};
const sub = () => D().submit;
const visible = e => S.filters[e.k] !== false;
const busyPhase = p => ["packing", "joining", "submitting", "running"].includes(p);

/* ═════════════ talking to the server ═════════════ */
async function call(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return await res.json();
}

/* Nothing in this page runs on a timer except a graded run you are
   watching in its own modal. Every other request it makes is one you
   caused — say, NEW, SUBMIT — so the page you are reading is
   the page that stays in front of you until you act on it.

   That includes noticing the server: there is no heartbeat, because
   the honest moment to find out that `stall chat` has stopped is when
   something you asked for cannot happen. Whatever fails, fails here. */
async function ask(path, body) {
  try {
    S.data = await call(path, body);
    S.dead = false;
    return S.data;
  } catch (e) {
    S.dead = true;
    return null;
  }
}

async function say(text) {
  if (!text || S.busy) return;
  // the turn is in flight: this is the only state the page holds that
  // the server has not told it, and it is gone the moment the reply is
  S.busy = true; S.pendingText = text; S.draft = ""; S.toast = null;
  render();
  await ask("/api/say", { text });
  S.busy = false; S.pendingText = null;
  announce();
  render();
}

async function fresh() {
  if (S.busy) return;
  await ask("/api/new", {});
  S.modal = false; S.focus = null; S.toast = null;
  render();
}

/* HISTORY is a fetch of its own, not a slice of /api/state — it does not
   belong to any conversation, and reusing ask() here would overwrite
   S.data (and so the whole page) with a payload that is only a list of
   runs. It fetches once, on open; nothing about a past run changes
   while you are looking at it. */
async function openHistory() {
  S.historyOpen = true;
  S.historyData = null;
  render();
  try {
    S.historyData = await call("/api/history");
  } catch (e) {
    S.historyData = { error: "the server did not answer" };
  }
  render();
}

function closeHistory() {
  S.historyOpen = false;
  S.historyData = null;
  render();
}

/* SUBMIT starts a run, or — when one is already in flight — reopens the
   one that is. While that modal is open the page does watch the run,
   because a modal reporting a run is the one place where waiting for
   news is the whole point of looking. It is the only timer in the page,
   it stops the moment the modal closes or the run lands, and it redraws
   only when the run's own state has changed. */
async function submit(extra) {
  S.submitOpen = true;
  await ask("/api/submit", extra || {});
  render();
  watchRun(busyPhase((sub() || {}).phase));
}

let runTicker = null;
function watchRun(on) {
  if (on && !runTicker) runTicker = setInterval(pollRun, 1500);
  if (!on && runTicker) { clearInterval(runTicker); runTicker = null; }
}

async function pollRun() {
  if (!S.submitOpen || !busyPhase((sub() || {}).phase)) { watchRun(false); return; }
  const before = JSON.stringify(sub());
  const data = await ask("/api/state");
  if (!data) { watchRun(false); render(); return; }
  // Closed while the fetch was in the air: there is no panel to write
  // into any more, and the plaque behind it still says RUN IN FLIGHT.
  if (!S.submitOpen) { watchRun(false); render(); return; }
  // Landed: the panel is a different panel now — the numbers, or a
  // structural error — so it is drawn the way every other panel is.
  if (!busyPhase((sub() || {}).phase)) { watchRun(false); render(); return; }
  // Still going. Same panel, so only what moved in it moves.
  if (JSON.stringify(sub()) !== before) drawRun();
}

/* The panel that is already on the page, with its new numbers written
   into it.

   A run is minutes of polling, and render() is a page rebuild: it takes
   the caret out of the sentence you were typing, closes the log you had
   open, and replays every animation on the page — the submit panel's own
   entrance among them, so the panel reporting the run flies in again
   every time the run says anything. That is what "the UI keeps
   refreshing" is. While the panel's shape is unchanged, the four things
   that move are written where they stand and the rest of the page is not
   touched at all. */
function drawRun() {
  const s = sub() || {};
  const win = document.querySelector(".subwin");
  const steps = document.getElementById("steps");
  const queue = document.getElementById("queue");
  const bar = win && win.querySelector(".prog");
  // Not the panel this thinks it is. A full draw is always correct and
  // only ever rude, so it is what anything unexpected falls back to.
  if (!win || !steps || !queue || !bar) { render(); return; }

  const head = win.querySelector(".sub");
  if (head) head.innerHTML = phaseLine(s);

  // Steps only ever grow, so the ones already on the page stay on the
  // page rather than being rewritten with the same words.
  const want = s.steps || [];
  if (steps.children.length > want.length) steps.innerHTML = "";
  want.forEach((x, i) => {
    let el = steps.children[i];
    if (!el) { el = document.createElement("div"); steps.appendChild(el); }
    const cls = x.ok ? "ok" : "no";
    if (el.className !== cls) el.className = cls;
    if (el.textContent !== x.text) el.textContent = x.text;
  });

  queue.innerHTML = queueHTML(s);

  const p = s.progress;
  const spin = !p || !p.total;
  if (spin !== bar.classList.contains("spin")) {
    // The sweep gives way to a real count. Once, at the first customer.
    bar.outerHTML = barHTML(s);
  } else if (!spin) {
    // Written on the element that is already there, so the bar slides to
    // its new width instead of appearing at it — and so the sweep, while
    // there is still one, is not restarted every poll.
    bar.firstElementChild.style.width = pct(p) + "%";
  }
}

/* The world moved while you were talking — worth one line in front of
   the student, not just a row in a log they have to open. */
function announce() {
  const last = turns()[turns().length - 1];
  const world = (last ? last.events : []).filter(e => e.k === "world")[0];
  if (!world) return;
  // it stays until you do something else — a banner that vanishes on a
  // timer is one more thing moving on a page that should be still
  S.toast = world.t;
}

/* ═════════════ the chit ═════════════ */
function heldName(canonical) {
  const held = board().held || {};
  if (held[canonical]) return held[canonical];
  const key = Object.keys(held).find(k => canonical.toLowerCase().includes(k.toLowerCase()));
  return key ? held[key] : 0;
}

function chitHTML() {
  const t = [...turns()].reverse().find(x => x.order && x.order.lines.length);
  if (!t) return `<div class="chitpeg"><div class="card empty">
    <div class="no">CHIT —</div><div class="said">nothing ordered yet.<br>
    it fills in as she talks.</div></div></div>`;
  const o = t.order;
  return `<div class="chitpeg"><div class="card">
    <div class="no">CHIT ${String(turns().length).padStart(2, "0")}<span class="live">● LIVE</span></div>
    ${o.lines.map(l => {
      if (!l.canonical) return `<div class="it bad"><span class="q">${l.qty}×</span>
        <span class="n">${esc(l.given)}</span><span class="tag sold">no such drink</span></div>`;
      const held = heldName(l.canonical);
      const tag = held ? `<span class="tag held">held</span>`
        : l.available === false ? `<span class="tag sold">sold out</span>` : "";
      return `<div class="it"><span class="q">${l.qty}×</span>
        <span class="n">${esc(l.canonical)}</span>${tag}
        <span class="p">${money(l.unit_cents * l.qty)}</span></div>`;
    }).join("")}
    ${(o.discounts || []).map(d => `<div class="promo"><span>${esc(d.name)}</span>
      <span>-${money(d.cents)}</span></div>`).join("")}
    <div class="tt"><span>TILL</span><span>${money(o.total_cents)}</span></div></div></div>`;
}

/* ═════════════ the conversation ═════════════ */
function custRow(t) {
  return `<div class="row cust">
    <div class="mini cust">${CUSTOMER(cid())}</div>
    <div class="stack"><div class="bub cust"><span class="who">THE CUSTOMER · ${esc(cid().toUpperCase())}</span>${esc(t.you)}</div></div></div>`;
}

function botRow(t, i) {
  const n = (t.events || []).filter(visible).length;
  if (t.error) return `<div class="row err" data-open="${i}">
    <div class="mini bot">${BOT_TIN("err")}</div>
    <div class="stack"><div class="bub err">${esc(t.error)}
      <div class="tip">▸ click — see what it did before it broke.
      in a graded run this case scores 0, and the tokens still count.</div></div></div></div>`;
  return `<div class="row bot" data-open="${i}">
    <div class="mini bot">${BOT_TIN("ok")}</div>
    <div class="stack"><div class="bub bot"><span class="who">KOPI KAKI · YOUR AGENT</span>${esc(t.reply)}
      <div class="open"><b>▸ SEE INSIDE</b><span class="sp"></span>${n} calls · ${kt(t.tokens)} tok
      · ${(t.ms / 1000).toFixed(1)}s</div></div></div></div>`;
}

function waitRow() {
  return `<div class="row bot">
    <div class="mini bot">${BOT_TIN("ok")}</div>
    <div class="stack"><div class="bub wait">
      <span class="dots"><i></i><i></i><i></i></span>
      your agent is working — the whole log lands with the reply
    </div></div></div>`;
}

function chatHTML() {
  const T = turns();
  const rows = T.map((t, i) => custRow(t) + botRow(t, i));
  if (pending()) rows.push(custRow({ you: pending().you }) + waitRow());
  if (!rows.length) return `<div class="row cust"><div class="mini cust">${CUSTOMER(cid())}</div>
    <div class="stack"><div class="bub cust"><span class="who">SHE HASN'T SAID ANYTHING YET</span>
    Type below and put the words in her mouth. There is no test set —
    imagining customers is the skill.</div></div></div>`;
  return rows.join("");
}

/* ═════════════ chrome ═════════════ */
function badgeHTML() {
  const st = stall();
  const head = st.reachable
    ? `LEVEL ${st.level} · ${esc((st.level_name || "").toUpperCase())}`
    : "STALL NOT ANSWERING";
  return `<div class="badge${st.reachable ? "" : " cold"}"><b>${head}</b>
    turn ${turns().length} · ${kt(D().tokens)} tok this conversation</div>`;
}

function worldLine() {
  const b = board();
  if (b.error) return `<div class="wl">the board is not answering</div>`;
  const held = Object.entries(b.held || {}).map(([item, q]) =>
    `${esc(item)} <b class="held">${q} HELD BY YOU</b>`);
  const rows = b.rows || [];
  const out = rows.filter(r => !r.left).map(r => `${esc(r.item)} <b class="out">HABIS</b>`);
  const last = rows.filter(r => r.left === 1).map(r => `${esc(r.item)} <b class="last">LAST 1</b>`);
  const bits = [...held, ...last, ...out].slice(0, 3);
  if (!bits.length) return `<div class="wl">practice board: a ${esc(b.day || "quiet")} day —
    everything in stock${b.day === "quiet" ? ", and nothing moves" : ""}</div>`;
  return `<div class="wl">${bits.join(" &nbsp;·&nbsp; ")}</div>`;
}

const plaqueHTML = () => {
  const running = busyPhase((sub() || {}).phase);
  return `<div class="plaque">
    <button data-new="1" title="a new customer, same code">+ NEW</button>
    <button data-history="1" title="your past submissions">☰ HISTORY</button>
    <button class="go${running ? " running" : ""}" data-submit="1">
    ${running ? "◉ RUN IN FLIGHT — TAP TO VIEW" : "▲ SUBMIT"}</button></div>`;
};

const sayHTML = () => `<div class="say">
  <input id="said" ${S.busy ? "disabled" : ""} value="${esc(S.draft)}"
    placeholder="${S.busy ? "your agent is thinking…" : "say it as her — eh uncle, one kopi c siew dai…"}">
  <button class="send" data-send="1" ${S.busy ? "disabled" : ""}>SAY</button></div>
  <div class="footnote"><span>agent <b>${esc(D().agent_dir || "")}/agent.py</b> — edited it?
  Ctrl-C the server and run <b>stall chat</b> again</span><span class="sp"></span>
  <span>conv <b>${esc((D().conv || "").slice(0, 8))}</b></span>
  <span>model <b>${esc(D().model || "")}</b></span></div>`;

/* ═════════════ the log ═════════════ */
function evHTML(e, dim) {
  const open = !dim && (e.k === "tool" || e.k === "world" || e.k === "raise");
  const diff = e.diff ? `<div class="diff">${e.diff.map(d => `<div>
    <span class="nm">${esc(d[0])}</span><span class="was">${esc(d[1])}</span>
    <span>→</span><span class="now">${esc(d[2])}</span></div>`).join("")}</div>` : "";
  return `<details class="ev ${e.k}${dim ? " dim" : ""}"${open ? " open" : ""}>
    <summary><span class="k">${e.k.toUpperCase()}</span>
    <span class="ttl">${esc(e.t)}</span><span class="n">${esc(e.n || "")}</span></summary>
    ${diff}${e.b ? `<pre>${esc(e.b)}</pre>` : ""}</details>`;
}

function modalHTML() {
  const T = turns();
  const fi = S.focus == null ? T.length - 1 : Math.min(S.focus, T.length - 1);
  const f = T[fi];
  const body = T.length ? T.map((t, i) => {
    const evs = (t.events || []).filter(visible), here = i === fi;
    return `<div class="turnsep${here ? " here" : ""}">TURN ${i + 1}
      <span class="said">"${esc(t.you)}"</span>
      <span>${kt(t.tokens)} TOK · ${((t.ms || 0) / 1000).toFixed(1)}S</span></div>`
      + (evs.length ? evs.map(e => evHTML(e, !here)).join("")
        : `<div class="turnsep" style="color:#463c22">— nothing yet —</div>`);
  }).join("") : `<div class="mblank">NOTHING BACK HERE YET</div>`;
  return `<div class="modal" data-close="1"><div class="win" data-stop="1">
    <div class="mhd"><b>INSIDE THE REPLY</b>
      <span class="q">turn ${fi + 1} — "${esc(f ? f.you : "")}"</span>
      <div class="meter">this conversation<b>${kt(D().tokens)} tok</b></div>
      <button class="x" data-close="1">CLOSE ✕</button></div>
    <div class="mchips">${KINDS.map(([k, l]) =>
      `<button class="${S.filters[k] ? "on" : ""}" data-f="${k}">${l}</button>`).join("")}</div>
    <div class="mbody">${body}</div></div></div>`;
}

/* ═════════════ submit ═════════════ */

/* A run in flight, as two elements rather than a scroll of lines: the
   counter line below, and the bar above it. The stall moves the counter
   every customer and the money only every fifth — see REVENUE_CHECKPOINT
   on the server — so the till says which customer it is counted through
   instead of looking like it is lagging by accident. */
function queueHTML(s) {
  const p = s.progress;
  if (!p) return `<div class="run">▸ the 25 customers are walking up…</div>
    <div class="wait">· revenue and token cost</div>`;
  const total = p.total || 25;
  // Before the first checkpoint there is no figure to show, so that
  // line stays the dim "not yet" it has always been; once there is one
  // it is real information and stops looking disabled.
  return `<div class="run">▸ ${p.done} of ${total} served</div>`
    + (p.through
      ? `<div class="till">· till ${money(p.revenue_cents || 0)}
         <span>through customer ${p.through}</span></div>`
      : `<div class="wait">· till counted every fifth customer</div>`)
    // Tokens are metered every customer, so unlike the till this one
    // is current as of the last one served.
    + (s.tokens ? `<div class="till">· ${kt(s.tokens)}
         <span>tokens spent</span></div>` : "");
}

const pct = p => Math.max(0, Math.min(100, (p.done / p.total) * 100)).toFixed(1);

function barHTML(s) {
  const p = s.progress;
  // No counter yet — packing, joining, or a run that has not started a
  // customer. An indeterminate sweep is the honest picture of that.
  if (!p || !p.total) return `<div class="prog spin"><i></i></div>`;
  return `<div class="prog"><i style="width:${pct(p)}%"></i></div>`;
}

/* Both of these are drawn twice — once into the panel when it opens, and
   once into the panel that is already open, by drawRun. */
const phaseLine = s => esc((s.stall_name || "your stall").toUpperCase())
  + " · " + esc((s.phase || "").toUpperCase());

const stepsHTML = s => (s.steps || []).map(
  x => `<div class="${x.ok ? "ok" : "no"}">${esc(x.text)}</div>`).join("");

/* The same five kinds and five buckets `stall submit` prints, in the
   same order and the same words. Two clients disagreeing about what a
   number is called is worse than either wording. */
const KIND_LABELS = [["baseline", "baseline"], ["menu", "menu-dependent"],
                     ["stock", "stock-dependent"], ["combo", "combo-eligible"],
                     ["regular", "returning regulars"]];
const FAIL_LABELS = [["unresolvable_item", "ordered something off no menu"],
                     ["wrong_qty_items", "wrong items or quantities"],
                     ["stock_mismatch", "right order, not servable"],
                     ["crashed", "your agent raised"],
                     ["timed_out", "your agent hung"]];
const HALTED = {
  token_ceiling: "at the token ceiling",
  run_deadline: "at the run deadline",
  respawns_exhausted: "respawns exhausted (harness kept crashing/hanging)",
};

/* Sales against attempts, per kind of customer, as a row of small bars.
   Which kinds are here is the stall's decision, not this page's: it
   windows them to the level the run was submitted at and sends only
   those, so drawing every key it sent is the whole rule. */
function catsHTML(r) {
  const by = r.by_kind || {};
  const rows = KIND_LABELS.filter(([k]) => by[k]).map(([k, label]) => {
    const c = by[k];
    const pct = c.total ? (c.sales / c.total) * 100 : 0;
    return `<div class="cat"><span>${esc(label)}</span>
      <i><b style="width:${pct.toFixed(1)}%"></b></i>
      <em>${c.sales}/${c.total}</em></div>`;
  });
  if (!rows.length) return "";
  return `<div class="brk"><h4>BY CATEGORY · THROUGH LEVEL ${r.level || 1}</h4>
    ${rows.join("")}</div>`;
}

/* Unwindowed, and labelled apart from the block above on purpose — a
   crash only a later level's customer triggers is counted here, so the
   two blocks are not meant to add up alike. */
function failsHTML(r) {
  const f = r.failure_reasons || {};
  const rows = FAIL_LABELS.filter(([k]) => f[k]).map(([k, label]) =>
    `<div class="fail"><span>${esc(label)}</span><em>${f[k]}</em></div>`);
  if (!rows.length) return "";
  return `<div class="brk"><h4>LOST CASES · ACROSS YOUR WHOLE RUN</h4>
    ${rows.join("")}</div>`;
}

/* About the run rather than about the agent, and absent on almost every
   run: two of the three only appear when they are not zero. */
function notesHTML(r) {
  const out = [];
  if (r.halted) {
    out.push(`<b>HALTED ${esc(HALTED[r.halt_reason] || "early")}</b>
      — scored on what it earned`);
  }
  // "before recovering" is only true if it did; when the budget is what
  // stopped the run the line above has already said so.
  if (r.respawns && r.halt_reason !== "respawns_exhausted") {
    out.push(`the harness respawned ${r.respawns} of 3 times before recovering`);
  }
  if (r.upstream_errors) {
    out.push(`upstream LLM errors: ${r.upstream_errors}`
      + " — the provider's trouble, not yours");
  }
  return out.length ? `<div class="note">${out.join("<br>")}</div>` : "";
}

function submitHTML() {
  const s = sub() || { phase: "needs", needs: "code", steps: [] };
  const close = `<button class="btn" data-closesubmit="1">${
    busyPhase(s.phase) ? "KEEP CHATTING WHILE IT RUNS" : "CLOSE"}</button>`;
  let inner;
  if (s.phase === "needs" && s.needs === "code") {
    inner = `<h3>YOUR JOIN CODE</h3>
      <div class="sub">IT IS ON THE PAPER SLIP</div>
      ${s.error ? `<div class="why">${esc(s.error)}</div>` : ""}
      <label>join code</label><input id="code" autofocus>
      <label>stall name — the projector shows it (leave blank and the stall names you)</label>
      <input id="name" value="${esc((D().identity || {}).name || "")}">
      <button class="btn" data-sendcode="1">SEND IT UP</button>`;
  } else if (s.phase === "needs" && s.needs === "name") {
    inner = `<h3>THAT NAME WAS REFUSED</h3>
      <div class="sub">THE STALL'S WORDS, NOT OURS</div>
      <div class="why">${esc(s.error || "")}</div>
      <label>another name</label><input id="name" autofocus>
      <button class="btn" data-sendname="1">TRY THAT ONE</button>`;
  } else if (s.phase === "structural") {
    inner = `<h3>STRUCTURAL ERROR</h3>
      <div class="sub">NO RUN CONSUMED · NO COOLDOWN</div>
      <pre>${esc(s.structural_error || "")}</pre>${close}`;
  } else if (s.phase === "error") {
    inner = `<h3>THE STALL SAID NO</h3><div class="sub">NOTHING WAS GRADED</div>
      <div class="why">${esc(s.error || "")}</div>${close}`;
  } else if (s.phase === "done") {
    const r = s.result || {};
    inner = `<h3>THE NUMBERS</h3>
      <div class="sub">RUN ${esc(r.id || "")} · ${esc(s.stall_name || "")}</div>
      <div class="numbers">
        revenue <b>${money(r.revenue_cents || 0)}</b> — ${r.sales} sold, ${r.lost} lost<br>
        token cost <b>${money(r.token_cost_cents || 0)}</b> — ${kt(r.tokens)} tokens
      </div>
      ${catsHTML(r)}${failsHTML(r)}${notesHTML(r)}
      <div class="cool"><span>no per-case feedback — the customers are hidden</span></div>
      ${close}`;
  } else {
    // The three ids are drawRun's handles: while a run is in flight the
    // page writes into these and leaves the rest of itself alone.
    inner = `<h3>SENDING YOUR STALL UP</h3>
      <div class="sub">${phaseLine(s)}</div>
      <div class="steps" id="steps">${stepsHTML(s)}</div>
      <div class="steps" id="queue">${queueHTML(s)}</div>
      ${barHTML(s)}
      <div class="cool"><span>no per-case feedback — the customers are hidden</span></div>
      ${close}`;
  }
  return `<div class="modal" data-closesubmit="1"><div class="subwin" data-stop="1">${inner}</div></div>`;
}

/* ═════════════ history ═════════════ */

/* One row per past submission — no by_kind, no failure_reasons: the
   stall already keeps the list lean (server.py:_run_summary), and a
   panel showing everything you have ever submitted has to stay
   scannable the same way `stall history` does in a terminal. */
function historyRowHTML(number, r) {
  const n = "RUN " + String(number).padStart(3, "0");
  if (r.status === "queued" || r.status === "running") {
    return `<div class="hrow ${r.status}">
      <div class="htop"><span class="hn">${n}</span><span class="hsp"></span>
        <span class="hstate">${r.status.toUpperCase()}</span></div>
      <div class="hbot"><span>${kt(r.tokens)} tok so far</span></div></div>`;
  }
  if (r.status === "failed") {
    return `<div class="hrow failed">
      <div class="htop"><span class="hn">${n}</span><span class="hsp"></span>
        <span class="hstate">FAILED</span></div>
      <div class="hbot"><span>the stall's bug, not yours</span></div></div>`;
  }
  return `<div class="hrow done${r.is_best ? " best" : ""}">
    <div class="htop"><span class="hn">${n}</span><span class="hsp"></span>
      ${r.halted ? `<span class="htag halted">HALTED</span>` : ""}
      ${r.is_best ? `<span class="htag best">★ LEADERBOARD</span>` : ""}</div>
    <div class="hbot">
      <span>${money(r.revenue_cents)} <i>${r.sales} sold · ${r.lost} lost</i></span>
      <span>${kt(r.tokens)} tok <i>${money(r.token_cost_cents)}</i></span>
    </div></div>`;
}

function historyHTML() {
  const close = `<button class="btn" data-closehistory="1">CLOSE</button>`;
  const d = S.historyData;
  let inner;
  if (d === null) {
    inner = `<h3>YOUR SUBMISSIONS</h3><div class="sub">FETCHING…</div>`;
  } else if (d.error) {
    inner = `<h3>YOUR SUBMISSIONS</h3><div class="sub">COULD NOT FETCH IT</div>
      <div class="why">${esc(d.error)}</div>${close}`;
  } else if (!d.joined) {
    inner = `<h3>YOUR SUBMISSIONS</h3><div class="sub">NO JOIN CODE YET</div>
      <div class="why">▲ SUBMIT once — that's what gets you one.</div>${close}`;
  } else if (!d.runs.length) {
    inner = `<h3>YOUR SUBMISSIONS</h3><div class="sub">NONE YET</div>
      <div class="why">▲ SUBMIT when you're ready.</div>${close}`;
  } else {
    inner = `<h3>YOUR SUBMISSIONS</h3>
      <div class="sub">${d.runs.length} SO FAR</div>
      <div class="hist">${d.runs.map((r, i) => historyRowHTML(i + 1, r)).join("")}</div>
      ${close}`;
  }
  return `<div class="modal" data-closehistory="1"><div class="subwin" data-stop="1">${inner}</div></div>`;
}

/* ═════════════ render ═════════════ */
function view() {
  if (!S.data) return `<div class="dead"><div><b>connecting…</b></div></div>`;
  return `<div class="app">
    <div class="topbar">${badgeHTML()}<span class="sp"></span>${worldLine()}${plaqueHTML()}</div>
    <div class="main">
      <div class="rail"><div class="fig">${CUSTOMER(cid())}</div>
        <div class="lbl">${esc(cid().toUpperCase())}<br>THE CUSTOMER</div></div>
      <div class="center">
        <div class="chat" id="chat">${chatHTML()}</div>
        ${S.toast ? `<div class="toast" data-toast="1" title="dismiss">${esc(S.toast.toUpperCase())}</div>` : ""}
        <div class="sayrow">${sayHTML()}</div>
      </div>
      <div class="rail right"><div class="fig" data-open="last">${BOT_TIN(
        turns().some(t => t.error) ? "err" : "ok")}</div>
        <div class="lbl">KOPI KAKI<br>YOUR AGENT</div>
        <div class="chitdock">${chitHTML()}</div></div>
    </div>
    ${S.modal ? modalHTML() : ""}
    ${S.submitOpen ? submitHTML() : ""}
    ${S.historyOpen ? historyHTML() : ""}
    ${S.dead ? deadHTML() : ""}</div>`;
}

const deadHTML = () => `<div class="dead"><div><b>the server has stopped</b>
  this page is a window onto <code>stall chat</code>, and it is no longer running —
  which is why what you just asked for did not happen.<br>
  start it again in your terminal: <code>stall chat</code>, then open this page
  afresh — which is also how an edit to <code>agent.py</code> is picked up.</div></div>`;


function render() {
  const chat = document.getElementById("chat");
  const stuck = !chat || chat.scrollTop + chat.clientHeight >= chat.scrollHeight - 40;
  // what the person was doing, so rebuilding the page does not take it
  const was = document.activeElement;
  const typing = was && was.id === "said"
    ? [was.selectionStart, was.selectionEnd] : null;
  const held = was && was.id ? was.id : null;

  app.innerHTML = view();

  const now = document.getElementById("chat");
  if (now && stuck) now.scrollTop = now.scrollHeight;
  const first = document.querySelector(".subwin input[autofocus]");
  if (first) { first.focus(); return; }
  const input = document.getElementById("said");
  if (!input || S.modal || S.submitOpen) return;
  // the caret goes back where it was; a click elsewhere keeps its focus
  if (typing) {
    input.focus();
    input.setSelectionRange(typing[0], typing[1]);
  } else if (!held && (!was || was === document.body)) {
    input.focus();
  }
}

/* ═════════════ events ═════════════ */
document.addEventListener("input", e => {
  if (e.target.id === "said") S.draft = e.target.value;
});
document.addEventListener("keydown", e => {
  if (e.target.id === "said" && e.key === "Enter") { say(e.target.value.trim()); return; }
  if (e.target.tagName === "INPUT" && e.key === "Enter") {
    const code = document.getElementById("code"), name = document.getElementById("name");
    if (code) submit({ code: code.value.trim(), name: name ? name.value.trim() : "" });
    else if (name) submit({ name: name.value.trim() });
    return;
  }
  if (e.target.tagName === "INPUT") return;
  if (e.key === "Escape") {
    if (S.submitOpen) { S.submitOpen = false; watchRun(false); }
    else if (S.historyOpen) { S.historyOpen = false; S.historyData = null; }
    else if (S.modal) { S.modal = false; S.focus = null; }
    render();
  }
});
document.addEventListener("click", e => {
  const t = e.target.closest("[data-open],[data-close],[data-f],[data-send],[data-new],"
    + "[data-submit],[data-closesubmit],[data-history],[data-closehistory],"
    + "[data-toast],[data-sendcode],[data-sendname]");
  if (!t) return;
  if (t.dataset.open !== undefined) {
    const T = turns();
    if (!T.length) return;
    S.focus = t.dataset.open === "last" ? T.length - 1 : +t.dataset.open;
    S.modal = true; render(); return;
  }
  if (t.dataset.close) {
    // the backdrop closes; anything inside the window does not
    if (e.target.closest("button[data-close]") || !e.target.closest("[data-stop]")) {
      S.modal = false; S.focus = null; render();
    }
    return;
  }
  if (t.dataset.f) { S.filters[t.dataset.f] = !S.filters[t.dataset.f]; render(); return; }
  if (t.dataset.send) { say(S.draft.trim()); return; }
  if (t.dataset.new) { fresh(); return; }
  if (t.dataset.submit) { submit(); return; }
  if (t.dataset.history) { openHistory(); return; }
  if (t.dataset.closehistory) {
    if (e.target.closest("button[data-closehistory]") || !e.target.closest("[data-stop]")) {
      closeHistory();
    }
    return;
  }
  if (t.dataset.toast) { S.toast = null; render(); return; }
  if (t.dataset.closesubmit) {
    if (e.target.closest("button[data-closesubmit]") || !e.target.closest("[data-stop]")) {
      S.submitOpen = false; watchRun(false); render();
    }
    return;
  }
  if (t.dataset.sendcode) {
    const code = document.getElementById("code"), name = document.getElementById("name");
    submit({ code: code.value.trim(), name: name.value.trim() }); return;
  }
  if (t.dataset.sendname) {
    submit({ name: document.getElementById("name").value.trim() }); return;
  }
});

/* The one fetch nobody clicked: the page has to start somewhere. */
ask("/api/state").then(render);
