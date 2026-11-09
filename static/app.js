// Interview Coach front end (vanilla JS) - "hot seat" studio UI
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const state = { iv: null, turn: null, timer: null, t0: 0, problem: null, thread: null, meta: null };
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

async function api(path, opts = {}) {
  const r = await fetch(path, {
    method: opts.method || (opts.body ? "POST" : "GET"),
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (r.status === 401 && !path.startsWith("/api/auth")) { showLogin(); throw new Error("Your session ended. Log in again."); }
  const isText = (r.headers.get("content-type") || "").startsWith("text/plain");
  const data = isText ? await r.text() : await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `Something went wrong (${r.status}). Try again.`);
  return data;
}
function toast(msg, ms = 4000) { const t = $("#toast"); t.textContent = msg; t.classList.remove("hidden"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), ms); }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function md(s) {
  if (window.marked && window.DOMPurify) return DOMPurify.sanitize(marked.parse(String(s || "")));
  // small built-in fallback: headings, bullets, bold, italics, inline code, code blocks
  const blocks = String(s || "").split(/```/);
  return blocks.map((b, i) => {
    if (i % 2) return `<pre>${esc(b.replace(/^\w*\n/, ""))}</pre>`;
    let html = "", inList = false;
    for (const raw of b.split("\n")) {
      const line = esc(raw).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\s)\*(\S.+?)\*/g, "$1<i>$2</i>").replace(/`(.+?)`/g, "<code>$1</code>");
      const li = line.match(/^\s*(?:[-*]|\d+[.)])\s+(.*)/);
      const h = line.match(/^(#{1,4})\s+(.*)/);
      if (li) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${li[1]}</li>`; continue; }
      if (inList) { html += "</ul>"; inList = false; }
      if (h) html += `<h3>${h[2]}</h3>`; else if (line.trim()) html += `<p>${line}</p>`;
    }
    return html + (inList ? "</ul>" : "");
  }).join("");
}
const level = (n) => (n >= 7 ? "hi" : n >= 5 ? "mid" : "lo");
function busy(btn, on, label) { if (!btn) return; if (on) { btn._t = btn.innerHTML; btn.disabled = true; btn.innerHTML = `${label || "Working"}<span class="dots"></span>`; } else { btn.disabled = false; btn.innerHTML = btn._t; } }
function download(name, text) { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type: "text/markdown" })); a.download = name; a.click(); }
// the teaching block: what was wrong, the candidate's own answer fixed, and a real explanation
function corrections(fb, original, inHistory = false) {
  const ms = (fb.mistakes || []).filter((m) => m && (m.said || m.correct));
  return `
    ${ms.length ? `<div class="fixes"><h3>What you got wrong</h3>${ms.map((m) => `<div class="fix">
      <div class="fix-said"><span>You said</span>${esc(m.said)}</div>
      <div class="fix-right"><span>Actually</span>${esc(m.correct)}</div></div>`).join("")}</div>` : ""}
    <details class="orig"${inHistory ? " open" : ""}><summary>Your original answer</summary><div class="your-answer">${esc(original || "")}</div></details>
    ${fb.corrected_answer ? `<div class="corrected"><h3>Your answer, corrected</h3>
      <div class="prompter-text">${esc(fb.corrected_answer)}</div>
      ${inHistory ? "" : `<div class="answer-actions" style="margin-bottom:0"><button class="btn ghost small" id="fb-read-fix">Listen to it</button></div>`}</div>` : ""}
    ${fb.explanation ? `<div class="explain"><h3>Understand it properly</h3><div class="md">${md(fb.explanation)}</div></div>` : ""}`;
}
const list = (a, empty = "") => (a && a.length ? `<ul>${a.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : empty);

// the one orchestrated moment: score dial fills while the number counts up
function dial(score, max = 10) {
  return `<div class="dial"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="dial-track"/>
    <circle cx="60" cy="60" r="52" class="dial-fill v-${level(score)}" pathLength="100" data-to="${(score / max) * 100}"/></svg>
    <div class="dial-num v-${level(score)}"><div><b data-count="${score}">${reduceMotion ? score : 0}</b><span>/${max}</span></div></div></div>`;
}
function playDial(root) {
  const fill = root.querySelector(".dial-fill"), num = root.querySelector("[data-count]");
  if (!fill) return;
  const to = +fill.dataset.to, target = +num.dataset.count;
  requestAnimationFrame(() => requestAnimationFrame(() => (fill.style.strokeDasharray = `${to} 100`)));
  if (reduceMotion) { num.textContent = target; return; }
  const t0 = performance.now(), dur = 1000, dec = String(target).includes(".");
  const step = (t) => { const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    num.textContent = dec ? (target * e).toFixed(1) : Math.round(target * e); if (p < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

// ---------------- auth ----------------
async function boot() {
  const s = await api("/api/auth/status");
  if (s.logged_in) showShell(s.username); else showLogin(s.can_register);
}
function setTab(mode) {
  $("#login-form").dataset.mode = mode;
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === mode));
  $("#login-btn").textContent = mode === "register" ? "Create account" : "Log in";
  $("#lg-pass2-wrap").classList.toggle("hidden", mode !== "register");
  $("#lg-pass").autocomplete = mode === "register" ? "new-password" : "current-password";
  $("#register-hint").textContent = mode === "register" ? "New accounts wait for the admin's approval before the first login." : "";
  $("#login-err").textContent = ""; $("#login-ok").textContent = "";
}
function showLogin(canRegister) {
  $("#shell").classList.add("hidden"); $("#view-login").classList.remove("hidden");
  if (canRegister !== undefined) $("#tab-register").classList.toggle("hidden", !canRegister);
  setTab("login");
}
$$(".tab").forEach((t) => (t.onclick = () => setTab(t.dataset.tab)));
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault(); $("#login-err").textContent = ""; $("#login-ok").textContent = "";
  const mode = e.target.dataset.mode, btn = $("#login-btn");
  const body = { username: $("#lg-user").value.trim(), password: $("#lg-pass").value };
  busy(btn, true, mode === "register" ? "Creating" : "Logging in");
  try {
    if (mode === "register") {
      if (body.password !== $("#lg-pass2").value) throw new Error("The two passwords don't match.");
      const r = await api("/api/auth/register", { body });
      busy(btn, false); setTab("login"); $("#login-ok").textContent = r.message; $("#lg-pass").value = "";
    } else {
      await api("/api/auth/login", { body });
      busy(btn, false); showShell(body.username);
    }
  } catch (err) { busy(btn, false); $("#login-err").textContent = err.message; }
});
$("#logout").onclick = async () => { await api("/api/auth/logout", { method: "POST" }); location.reload(); };

async function showShell(name) {
  $("#view-login").classList.add("hidden"); $("#shell").classList.remove("hidden");
  $("#who").textContent = `Signed in as ${name}`;
  $("#dash-name").textContent = `, ${name.split(/[._-]/)[0].replace(/^./, (c) => c.toUpperCase())}`;
  await refreshMeta();
  buildChips();
  go("dashboard");
}
async function refreshMeta() {
  const m = (state.meta = await api("/api/meta"));
  $("#model-status").textContent = m.mock ? "Demo mode: AI replies are fake" : m.key_set ? "AI panel connected" : "No OpenRouter key set";
  $("#usage-status").textContent = m.ai_limit === null ? "Admin, no AI limit" : `AI calls today: ${m.ai_used_today} of ${m.ai_limit}`;
  $("#nav-admin").classList.toggle("hidden", m.role !== "admin");
  $("#pw-card").classList.toggle("hidden", m.role === "admin");
  $("#p-locked").classList.toggle("hidden", m.trusted);
  $("#p-run").disabled = !m.trusted;
  const cur = $("#s-cat").value;
  $("#s-cat").innerHTML = `<option value="mixed">All topics, a realistic mix</option>` +
    Object.entries(m.categories).map(([c, n]) => `<option value="${esc(c)}">${esc(c)} (${n} questions)</option>`).join("");
  if (cur) $("#s-cat").value = cur;
  $("#bank-info").textContent = `${m.total_questions} questions in the bank${m.bank_updated ? `, last refreshed ${m.bank_updated}` : ""}.`;
}

// ---------------- navigation ----------------
function go(view) {
  if (view !== "room") clearInterval(state.timer), $("#r-onair").classList.remove("live");
  $$(".view").forEach((v) => v.classList.add("hidden"));
  $(`#view-${view}`).classList.remove("hidden");
  $$(".desk nav a").forEach((a) => a.classList.toggle("active", a.dataset.view === view || (["room", "report"].includes(view) && a.dataset.view === "setup")));
  if (view !== "reader") closeReader();
  $$(".desk nav a").forEach((a) => { if (view === "reader" && a.dataset.view === "tutorials") a.classList.add("active"); });
  ({ dashboard: loadDashboard, coding: loadProblems, coach: loadThreads, history: loadHistory, profile: loadProfile, admin: loadAdmin, tutorials: loadTutorials }[view] || (() => {}))();
  window.scrollTo(0, 0);
}
$$(".desk nav a").forEach((a) => (a.onclick = (e) => { e.preventDefault(); go(a.dataset.view); }));
$$("[data-view-link]").forEach((b) => (b.onclick = () => go(b.dataset.viewLink)));

// ---------------- home ----------------
async function loadDashboard() {
  api("/api/tutorials").then((d) => ($("#tut-count").textContent = d.tutorials.length || "")).catch(() => {});
  const s = await api("/api/stats");
  $("#st-answered").textContent = s.answered || 0;
  $("#st-avg").textContent = s.average ?? "–";
  $("#st-7d").textContent = s.avg_7d ?? "–";
  $("#st-best").textContent = s.best ?? "–";
  $("#st-code").textContent = `${s.coding_solved} of ${s.coding_total}`;
  $("#streak-n").textContent = s.streak;
  $("#streak-chip").classList.toggle("hot", s.streak >= 3);
  const pct = Math.min(100, (s.today / s.daily_goal) * 100);
  $("#goal-n").textContent = `${s.today}/${s.daily_goal}`;
  requestAnimationFrame(() => ($("#goal-fill").style.strokeDasharray = `${pct} 100`));
  $("#goal-fill").style.stroke = s.today >= s.daily_goal ? "var(--mint)" : "var(--gold)";
  $("#dash-sub").textContent = s.today >= s.daily_goal ? `Today's goal is done. ${s.streak} day streak and counting.`
    : s.streak ? `You're on a ${s.streak} day streak. ${s.daily_goal - s.today} more answers keeps it alive today.`
    : "Five good answers a day keeps your interview reflexes sharp.";
  if (s.by_category.length) {
    $("#cat-bars").innerHTML = s.by_category.map((c) => {
      const on = Math.round(c.avg);
      return `<div class="meter" title="${esc(c.category)}: ${c.avg} average over ${c.n} answers">
        <span class="meter-name">${esc(c.category)}</span>
        <span class="meter-segs">${Array.from({ length: 10 }, (_, i) => `<i class="${i < on ? `on ${level(c.avg)}` : ""}"></i>`).join("")}</span>
        <span class="meter-val">${c.avg}</span><span class="meter-n">${c.n} answer${c.n === 1 ? "" : "s"}</span></div>`;
    }).join("");
  }
}
$$("[data-quick]").forEach((b) => (b.onclick = () => {
  const [track, cat, count] = b.dataset.quick.split("|");
  $("#s-track").value = track; $("#s-cat").value = cat; $("#s-count").value = count; $("#s-diff").value = "mixed";
  startInterview(b);
}));

// ---------------- interview room ----------------
$("#start-btn").onclick = () => startInterview($("#start-btn"));
async function startInterview(btn) {
  busy(btn, true, "Seating the panel");
  try {
    const r = await api("/api/interview/start", { body: {
      track: $("#s-track").value, category: $("#s-cat").value, difficulty: $("#s-diff").value,
      count: +$("#s-count").value || 8, source: $("#s-src").value } });
    state.iv = { id: r.interview_id, total: r.total };
    go("room"); showQuestion(r, 1, r.total);
  } catch (e) { toast(e.message); } finally { busy(btn, false); }
}
function showQuestion(q, index, total) {
  state.turn = q.turn_id;
  $("#r-cat").textContent = q.live ? `${q.category}, freshly written` : q.category;
  $("#r-progress").textContent = `Question ${index} of ${total}`;
  $("#r-follow").classList.toggle("hidden", !q.is_followup);
  $("#r-question").textContent = q.question;
  $("#r-answer").value = ""; $("#r-answer-box").classList.remove("hidden");
  $("#r-feedback").classList.add("hidden"); $("#r-feedback").innerHTML = "";
  startTimer();
  if ($("#s-voice").checked) speak(q.question);
  window.scrollTo(0, 0);
  $("#r-answer").focus({ preventScroll: true });
}
function startTimer() {
  clearInterval(state.timer); state.t0 = Date.now(); $("#r-onair").classList.add("live");
  const tick = () => {
    const s = Math.floor((Date.now() - state.t0) / 1000);
    $("#r-timer").textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    $("#r-timer").classList.toggle("late", s > 180);
  };
  tick(); state.timer = setInterval(tick, 1000);
}
function stopTimer() { clearInterval(state.timer); $("#r-onair").classList.remove("live"); }
function speak(text) {
  if (!("speechSynthesis" in window)) return toast("This browser can't read aloud. Try Chrome or Edge.");
  speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(text); u.rate = 1; speechSynthesis.speak(u);
}
$("#r-speak").onclick = () => speak($("#r-question").textContent);

let rec = null;
$("#r-mic").onclick = () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return toast("Voice answers need Chrome or Edge.");
  if (rec) { rec.stop(); return; }
  rec = new SR(); rec.lang = "en-IN"; rec.continuous = true; rec.interimResults = true;
  const base = $("#r-answer").value ? $("#r-answer").value + " " : "";
  rec.onresult = (e) => { let t = ""; for (const r of e.results) t += r[0].transcript; $("#r-answer").value = base + t; };
  rec.onend = () => { rec = null; $("#r-mic").classList.remove("on"); $("#r-mic-label").textContent = "Speak"; $("#r-mic-status").textContent = ""; };
  rec.start(); $("#r-mic").classList.add("on"); $("#r-mic-label").textContent = "Stop"; $("#r-mic-status").textContent = "Listening. Speak naturally.";
};

$("#r-submit").onclick = async () => {
  const btn = $("#r-submit");
  if (rec) rec.stop();
  busy(btn, true, "The panel is grading");
  try {
    const r = await api(`/api/interview/${state.iv.id}/answer`, { body: { turn_id: state.turn, answer: $("#r-answer").value } });
    stopTimer(); renderFeedback(r.feedback);
  } catch (e) { toast(e.message, 7000); } finally { busy(btn, false); }
};
$("#r-skip").onclick = () => nextQuestion(false, state.turn);

function renderFeedback(fb) {
  $("#r-answer-box").classList.add("hidden");
  const box = $("#r-feedback");
  box.innerHTML = `
    <div class="verdict">${dial(fb.score)}
      <div><h2>${esc(fb.verdict || "")}</h2>${fb.delivery_tips ? `<p>${esc(fb.delivery_tips)}</p>` : ""}</div></div>
    <div class="fb-cols">
      <div class="landed"><h3>What landed</h3>${list(fb.strengths, `<p class="empty">Nothing yet. Look at the model answer.</p>`)}</div>
      <div class="missed"><h3>What the panel missed</h3>${list(fb.gaps, `<p class="empty">No gaps. Nicely done.</p>`)}</div>
    </div>
    ${corrections(fb, $("#r-answer").value)}
    <div class="prompter"><h3>How a senior candidate would say it</h3>
      <div class="prompter-text">${esc(fb.model_answer || "")}</div>
      <div class="answer-actions" style="margin-bottom:0"><button class="btn ghost small" id="fb-read">Listen to it</button></div></div>
    ${fb.key_points && fb.key_points.length ? `<div class="checklist"><h3>A strong answer covers</h3>${list(fb.key_points)}</div>` : ""}
    ${fb.follow_up ? `<div class="incoming"><h3>The panel follows up</h3><p>${esc(fb.follow_up)}</p></div>` : ""}
    <div class="answer-actions">
      ${fb.follow_up ? `<button class="btn gold" id="fb-follow">Answer the follow-up</button>` : ""}
      <button class="btn ${fb.follow_up ? "" : "gold"}" id="fb-next">Next question</button>
      <button class="btn ghost" id="fb-retry">Try this one again</button>
      <span class="spacer"></span><button class="btn ghost" id="fb-end">End and see my debrief</button>
    </div>
    <p class="fine">Graded by ${esc(fb.model_used || "the AI panel")}</p>`;
  box.classList.remove("hidden");
  playDial(box);
  $("#fb-read").onclick = () => speak(fb.model_answer || "");
  if ($("#fb-read-fix")) $("#fb-read-fix").onclick = () => speak(fb.corrected_answer || "");
  if ($("#fb-follow")) $("#fb-follow").onclick = () => nextQuestion(true);
  $("#fb-next").onclick = () => nextQuestion(false);
  $("#fb-retry").onclick = () => { box.classList.add("hidden"); $("#r-answer-box").classList.remove("hidden"); startTimer(); $("#r-answer").focus(); };
  $("#fb-end").onclick = () => finishInterview();
  box.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  refreshMeta().catch(() => {});
}

async function nextQuestion(followup, skipId) {
  try {
    const r = await api(`/api/interview/${state.iv.id}/next`, { body: { followup, skip_turn_id: skipId || null } });
    if (r.done) return finishInterview();
    showQuestion(r, Math.max(1, r.index), r.total);
  } catch (e) { toast(e.message); }
}

async function finishInterview() {
  stopTimer(); go("report");
  $("#view-report").innerHTML = `<h1 class="display sm">Debrief</h1><p class="lede">The panel is writing up your debrief<span class="dots"></span></p>`;
  try {
    const r = await api(`/api/interview/${state.iv.id}/finish`, { method: "POST" });
    renderReport(r, state.iv.id);
  } catch (e) { $("#view-report").innerHTML = `<h1 class="display sm">Debrief</h1><p class="err">${esc(e.message)}</p>`; }
}
function renderReport(r, iid) {
  const v = $("#view-report");
  v.innerHTML = `
    <h1 class="display sm">Debrief</h1>
    <div class="verdict" style="margin-top:22px">${dial(r.average)}
      <div><h2>${esc(r.ready_for || "")}</h2><p>${r.answered} answer${r.answered === 1 ? "" : "s"} graded. ${esc(r.overall || "")}</p></div></div>
    <div class="fb-cols">
      <div class="missed"><h3>Fix these first</h3>${list(r.top_fixes)}</div>
      <div class="landed"><h3>Your next 48 hours</h3>${list(r.study_plan)}</div>
    </div>
    <div class="panel" style="max-width:900px">
      ${(r.turns || []).map((t) => `<div class="report-q"><div>${t.is_followup ? "↳ " : ""}${esc(t.question)}<div class="cat">${esc(t.category)}</div></div>
        <div class="report-score v-${level(t.score)}">${t.score}</div></div>`).join("")}
    </div>
    <div class="answer-actions"><button class="btn gold" id="rep-again">Start another interview</button>
      <button class="btn ghost" id="rep-export">Download questions and model answers</button></div>`;
  playDial(v);
  $("#rep-again").onclick = () => go("setup");
  $("#rep-export").onclick = async () => download(`interview-${iid}.md`, await api(`/api/interview/${iid}/export`));
}

// ---------------- coding ----------------
async function loadProblems() {
  const ps = await api("/api/coding/problems");
  $("#p-list").innerHTML = ps.map((p) => `<button class="p-item ${p.solved ? "solved" : ""} ${state.problem?.id === p.id ? "active" : ""}" data-id="${p.id}">
    <b>${esc(p.title)}</b><span>${p.kind === "sql" ? "SQL" : "Python"}, ${p.difficulty}</span></button>`).join("");
  $$(".p-item").forEach((el) => (el.onclick = () => openProblem(el.dataset.id)));
}
async function openProblem(id) {
  const p = await api(`/api/coding/problems/${id}`);
  state.problem = p;
  $$(".p-item").forEach((el) => el.classList.toggle("active", el.dataset.id === id));
  $("#p-empty").classList.add("hidden"); $("#p-body").classList.remove("hidden");
  $("#p-title").textContent = p.title; $("#p-diff").textContent = p.difficulty; $("#p-topic").textContent = p.topic;
  $("#p-tests").textContent = `${p.test_count} hidden tests`;
  const samples = p.kind === "sql" ? "" : `<p class="fine">Example calls:</p><pre>${p.sample_tests.map((t) => `${esc(t.expr)}\n  ⇒ ${esc(JSON.stringify(t.expected))}`).join("\n")}</pre>`;
  $("#p-prompt").innerHTML = md(p.prompt) + samples;
  $("#p-code").value = lsGet(`code-${id}`) || p.starter; $("#p-result").innerHTML = "";
}
function lsGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function lsSet(k, v) { try { localStorage.setItem(k, v); } catch {} }
$("#p-code").addEventListener("keydown", (e) => {
  if (e.key === "Tab" && !e.shiftKey) { e.preventDefault(); const t = e.target, s = t.selectionStart; t.value = t.value.slice(0, s) + "    " + t.value.slice(t.selectionEnd); t.selectionStart = t.selectionEnd = s + 4; }
});
$("#p-code").addEventListener("input", () => state.problem && lsSet(`code-${state.problem.id}`, $("#p-code").value));
$("#p-reset").onclick = () => { $("#p-code").value = state.problem.starter; lsSet(`code-${state.problem.id}`, ""); };
$("#p-run").onclick = async () => {
  const btn = $("#p-run"); busy(btn, true, "Running tests");
  try {
    const r = await api(`/api/coding/problems/${state.problem.id}/run`, { body: { code: $("#p-code").value } });
    const all = r.passed === r.total && r.total > 0;
    const show = (x) => esc(typeof x === "string" ? x : JSON.stringify(x));
    $("#p-result").innerHTML = `<div class="res-head ${all ? "pass" : "fail"}">${all ? "All tests pass" : `${r.passed} of ${r.total} tests pass`}</div>
      ${r.error ? `<div class="res fail">${esc(r.error)}</div>` : ""}
      <div class="results">${(r.results || []).map((t) => `<div class="res ${t.ok ? "ok" : "fail"}">${t.ok ? "✓" : "✗"} ${esc(t.name)}${t.ok ? "" : t.error ? `\n  ${esc(t.error)}` : `\n  expected ${show(t.expected)}\n  got      ${show(t.got)}`}</div>`).join("")}</div>
      ${r.stdout ? `<p class="fine">Printed output</p><pre>${esc(r.stdout)}</pre>` : ""}
      ${all ? `<p class="sub" style="margin-top:14px">Now say it out loud: your approach, the time and space complexity, and the edge cases. Then ask for a review.</p>` : ""}`;
    if (all) loadProblems();
  } catch (e) { toast(e.message); } finally { busy(btn, false); $("#p-run").disabled = !state.meta.trusted; }
};
$("#p-review").onclick = async () => {
  const btn = $("#p-review"); busy(btn, true, "Reviewing");
  try {
    const r = await api(`/api/coding/problems/${state.problem.id}/review`, { body: { code: $("#p-code").value } });
    $("#p-result").insertAdjacentHTML("beforeend", `<div class="review msg assistant">${md(r.review)}</div>`);
  } catch (e) { toast(e.message, 7000); } finally { busy(btn, false); }
};
$("#p-solution").onclick = async () => {
  if (!confirm("Have a real go first. Show the reference solution anyway?")) return;
  const r = await api(`/api/coding/problems/${state.problem.id}/solution`);
  $("#p-result").insertAdjacentHTML("beforeend", `<p class="fine" style="margin-top:16px">Reference solution</p><pre>${esc(r.solution)}</pre>`);
};

// ---------------- coach ----------------
const CHIPS = [
  ["Introduce yourself", "30, 90 and 120 second versions", "Write my 'Tell me about yourself' introduction in three versions: 30 seconds, 90 seconds and 2 minutes, for a remote {track} role. Make it confident and impact-focused, built only from my profile. Mark anything you need from me as [FILL]."],
  ["Projects to showcase", "Five builds hiring managers love", "Curate 5 portfolio projects that would most impress hiring managers for remote {track} roles right now (agents, MCP, RAG, evals, MLOps). For each: the business problem, architecture, stack, what to measure, a 1-week build plan, and why interviewers find it impressive. Prioritise ones I can build fastest with my skills."],
  ["Script one of my projects", "Pitch, story, challenges, cross-questions", "Write my interview showcase script for this project.\nProject name: \nProblem it solved: \nWho used it: \nStack: \nMy role: \nHardest problem I faced: \nResult / numbers: \n\nGive me: a 60-second pitch, the full STAR story, architecture explanation, 3 challenges and how I solved them, what I'd do differently, and the 10 cross-questions an interviewer will ask with strong answers.", true],
  ["Grill me on a project", "The 12 hardest cross-questions", "Take the project I describe next and act as a tough interviewer: list the 12 hardest cross-questions you'd ask to test whether I really built it, with what a strong answer must contain. Project: ", true],
  ["Explain a concept", "Simple, engineer, then architect level", "Explain this concept in 3 levels (simple analogy, working engineer, senior/architect with trade-offs), then give me a 60-second interview answer I can say out loud: ", true],
  ["Plan for my weak topics", "Seven days, built from my scores", "__WEAK__"],
  ["Negotiate salary", "Word-for-word scripts", "Give me word-for-word scripts for salary negotiation for a remote {track} role: answering 'expected CTC', responding to a low offer, asking for a joining bonus, and negotiating two offers against each other. Include how to research the market range."],
  ["Questions to ask them", "Ten that show senior thinking", "Give me 10 smart questions to ask the interviewer at the end of a {track} interview that show senior thinking, grouped by who I'm talking to (recruiter, hiring manager, tech lead)."],
];
function buildChips() {
  const host = $("#c-chips"); if (!host) return;
  host.innerHTML = CHIPS.map((c, i) => `<button class="chip" data-i="${i}"><b>${esc(c[0])}</b><span>${esc(c[1])}</span></button>`).join("");
  $$("#c-chips .chip").forEach((b) => (b.onclick = async () => {
    const [, , text, edit] = CHIPS[b.dataset.i];
    const track = $("#c-track").selectedOptions[0].text;
    if (text === "__WEAK__") {
      const s = await api("/api/stats");
      const weak = s.by_category.filter((c) => c.avg < 7).map((c) => `${c.category} (${c.avg}/10)`);
      $("#c-input").value = weak.length
        ? `My weakest interview topics right now are: ${weak.join(", ")}. Build me a 7-day study and practice plan to get each to 8+/10, with daily tasks, the key concepts to master, and 3 practice questions per topic.`
        : `I haven't done enough mock interviews yet. Give me a 7-day plan covering the most-asked ${track} topics, with daily tasks and practice questions.`;
      return sendCoach();
    }
    $("#c-input").value = text.replaceAll("{track}", track);
    if (edit) { $("#c-input").focus(); toast("Fill in the details, then press Send."); } else sendCoach();
  }));
}
async function loadThreads() {
  const ts = await api("/api/coach/threads");
  $("#c-threads").innerHTML = ts.map((t) => `<div class="thread ${state.thread === t.id ? "active" : ""}" data-id="${t.id}"><span title="${esc(t.title)}">${esc(t.title)}</span><button data-del="${t.id}" title="Delete chat" aria-label="Delete chat">✕</button></div>`).join("") || `<p class="fine">Your chats appear here.</p>`;
  $$(".thread").forEach((el) => (el.onclick = (e) => { if (e.target.dataset.del) return; openThread(+el.dataset.id); }));
  $$("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!confirm("Delete this chat?")) return;
    await api(`/api/coach/threads/${b.dataset.del}`, { method: "DELETE" });
    if (state.thread === +b.dataset.del) newChat(); else loadThreads();
  }));
}
function newChat() {
  state.thread = null;
  $("#c-messages").innerHTML = `<div class="starter"><h3>What should we work on?</h3><div class="chips" id="c-chips"></div></div>`;
  buildChips(); loadThreads();
}
$("#c-new").onclick = newChat;
async function openThread(id) {
  const d = await api(`/api/coach/threads/${id}`);
  state.thread = id;
  $("#c-messages").innerHTML = "";
  d.messages.forEach((m) => addMsg(m.role, m.content));
  loadThreads();
}
function addMsg(role, content) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  if (role === "assistant") {
    el.innerHTML = `<button class="btn ghost small copy">Copy</button>` + md(content);
    el.querySelector(".copy").onclick = () => { navigator.clipboard.writeText(content); toast("Copied"); };
  } else el.textContent = content;
  $("#c-messages").appendChild(el);
  $("#c-messages").scrollTop = $("#c-messages").scrollHeight;
  return el;
}
$("#c-form").addEventListener("submit", (e) => { e.preventDefault(); sendCoach(); });
$("#c-input").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) sendCoach(); });
async function sendCoach() {
  const text = $("#c-input").value.trim(); if (!text) return;
  const starter = $("#c-messages .starter"); if (starter) starter.remove();
  addMsg("user", text); $("#c-input").value = "";
  const wait = document.createElement("div"); wait.className = "msg assistant"; wait.innerHTML = `<span class="fine">Writing<span class="dots"></span></span>`;
  $("#c-messages").appendChild(wait);
  const btn = $("#c-send"); busy(btn, true, "");
  try {
    const r = await api("/api/coach/send", { body: { thread_id: state.thread, message: text, track: $("#c-track").value } });
    wait.remove(); addMsg("assistant", r.reply);
    if (!state.thread) { state.thread = r.thread_id; loadThreads(); }
    refreshMeta().catch(() => {});
  } catch (e) { wait.innerHTML = `<span class="err">${esc(e.message)}</span>`; } finally { busy(btn, false); }
}
$("#c-export").onclick = async () => {
  if (!state.thread) return toast("Open a chat first.");
  download(`coach-${state.thread}.md`, await api(`/api/coach/threads/${state.thread}/export`));
};

// ---------------- history ----------------
async function loadHistory() {
  const rows = await api("/api/interview/history");
  $("#h-detail").innerHTML = "";
  $("#h-table").innerHTML = `<tr><th>Date</th><th>Role</th><th>Topic</th><th>Answered</th><th>Average</th></tr>` +
    (rows.map((r) => `<tr class="click" data-id="${r.id}"><td>${new Date(r.created * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</td>
      <td>${r.track === "architect" ? "AI Architect" : "AI Engineer"}</td><td>${r.category === "mixed" ? "All topics" : esc(r.category)}</td>
      <td>${r.answered} of ${r.total}</td><td><b class="v-${level(r.avg || 0)}">${r.avg ? (+r.avg).toFixed(1) : "–"}</b></td></tr>`).join("") ||
     `<tr><td colspan="5" class="empty">No interviews yet. Your first one shows up here.</td></tr>`);
  $$("#h-table tr.click").forEach((tr) => (tr.onclick = () => showTranscript(+tr.dataset.id)));
}
async function showTranscript(id) {
  const d = await api(`/api/interview/${id}/transcript`);
  $("#h-detail").innerHTML = `<div class="answer-actions" style="margin-top:28px"><h2 style="margin:0">Interview ${id}</h2><span class="spacer"></span>
    <button class="btn ghost small" id="h-export">Download</button>
    ${d.interview.finished ? "" : `<button class="btn gold small" id="h-resume">Resume</button>`}</div>` +
    d.turns.map((t) => `<div class="t-card"><div class="p-meta"><span class="tag dim">${esc(t.category)}</span>${t.is_followup ? `<span class="tag coral">Follow-up</span>` : ""}<span class="spacer"></span><b class="report-score v-${level(t.score || 0)}">${t.score ?? "–"}</b></div>
      <p class="q">${esc(t.question)}</p>
      ${t.feedback.model_answer || t.feedback.corrected_answer ? `<details><summary>Corrections, explanation and model answer</summary><div style="margin-top:14px">${corrections(t.feedback, t.answer, true)}
        ${t.feedback.model_answer ? `<div class="prompter"><h3>How a senior candidate would say it</h3><div class="prompter-text">${esc(t.feedback.model_answer)}</div></div>` : ""}${list(t.feedback.gaps)}</div></details>`
        : `<div class="your-answer">${esc(t.answer || "Not answered")}</div>`}</div>`).join("");
  $("#h-export").onclick = async () => download(`interview-${id}.md`, await api(`/api/interview/${id}/export`));
  if ($("#h-resume")) $("#h-resume").onclick = () => {
    state.iv = { id, total: d.interview.total };
    const open = d.turns.find((t) => !t.answered);
    go("room");
    if (open) showQuestion({ turn_id: open.id, question: open.question, category: open.category, is_followup: !!open.is_followup }, d.turns.filter((t) => !t.is_followup).length, d.interview.total);
    else nextQuestion(false);
  };
  $("#h-detail").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
}

// ---------------- profile ----------------
async function loadProfile() { $("#pf-text").value = (await api("/api/profile")).text; $("#pf-status").textContent = ""; }
$("#pf-save").onclick = async () => {
  await api("/api/profile", { method: "PUT", body: { text: $("#pf-text").value } });
  $("#pf-status").textContent = "Profile saved. The panel and coach use it from your next question.";
};
$("#pw-save").onclick = async () => {
  try {
    await api("/api/auth/password", { body: { old: $("#pw-old").value, new: $("#pw-new").value } });
    $("#pw-status").textContent = "Password changed."; $("#pw-old").value = $("#pw-new").value = "";
  } catch (e) { $("#pw-status").textContent = e.message; }
};

// ---------------- admin ----------------
async function loadAdmin() {
  const [d, b] = await Promise.all([api("/api/admin/users"), api("/api/admin/refresh")]);
  showBank(b);
  $("#ad-reg").checked = d.registration_open; $("#ad-limit").value = d.ai_daily_limit;
  const btn = (id, action, label, cls = "") => `<button class="btn small ${cls}" data-uid="${id}" data-act="${action}">${label}</button>`;
  $("#ad-users").innerHTML = `<tr><th>User</th><th>Status</th><th>Joined</th><th>Answers</th><th>AI today</th><th></th></tr>` +
    d.users.map((u) => `<tr><td><b>${esc(u.username)}</b>${u.role === "admin" ? ` <span class="tag">you</span>` : ""}${u.trusted && u.role !== "admin" ? ` <span class="tag dim">trusted</span>` : ""}</td>
      <td><span class="badge b-${u.status}">${u.status}</span></td>
      <td class="fine">${new Date(u.created * 1000).toLocaleDateString()}</td><td>${u.answers}</td><td>${u.ai_today || 0}</td>
      <td>${u.role === "admin" ? "" : [
        u.status === "pending" ? btn(u.id, "approve", "Approve", "gold") : "",
        u.status === "active" ? btn(u.id, "disable", "Disable") : "",
        u.status === "disabled" ? btn(u.id, "enable", "Enable") : "",
        u.trusted ? btn(u.id, "untrust", "Remove trust") : btn(u.id, "trust", "Trust for code"),
        btn(u.id, "delete", "Delete", "ghost")].join("")}</td></tr>`).join("");
  $$("[data-act]").forEach((el) => (el.onclick = async () => {
    if (el.dataset.act === "delete" && !confirm("Delete this user and all their data? This can't be undone.")) return;
    try { await api(`/api/admin/users/${el.dataset.uid}`, { body: { action: el.dataset.act } }); loadAdmin(); } catch (e) { toast(e.message); }
  }));
}
function showBank(b) {
  $("#ad-bank").textContent = `${b.total} questions, ${b.trending} marked trending. ${b.last ? `Last refreshed ${b.last}.` : "Not refreshed on this server yet."}`;
  const running = b.status === "running";
  $("#ad-refresh").disabled = running;
  $("#ad-refresh").textContent = running ? "Refreshing…" : "Refresh from internet";
  $("#ad-refresh-status").textContent = running ? "Fetching lists and asking the AI. This takes a minute or two." : b.status.startsWith("done") ? `Last run: ${b.status.slice(6)}.` : b.status.startsWith("failed") ? `Last run failed: ${b.status.slice(8)}` : "";
  if (running) setTimeout(async () => { if (!$("#view-admin").classList.contains("hidden")) { showBank(await api("/api/admin/refresh")); refreshMeta(); } }, 5000);
}
$("#ad-refresh").onclick = async () => {
  await api("/api/admin/refresh", { body: { trending: +$("#ad-trend").value || 0 } });
  showBank(await api("/api/admin/refresh"));
};
$("#ad-import").onclick = async () => {
  const f = $("#ad-file").files[0];
  if (!f) return toast("Choose a file first.");
  const btn = $("#ad-import"); busy(btn, true, "Importing");
  try {
    const fd = new FormData(); fd.append("file", f);
    const r = await fetch("/api/admin/import", { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || `Import failed (${r.status}).`);
    $("#ad-import-status").textContent = `Found ${d.found} questions, added ${d.added} new. ` +
      Object.entries(d.categories).map(([c, n]) => `${c} ${n}`).join(", ") + ".";
    $("#ad-file").value = "";
    showBank(await api("/api/admin/refresh")); refreshMeta();
  } catch (e) { $("#ad-import-status").textContent = e.message; } finally { busy(btn, false); }
};
$("#ad-save").onclick = async () => {
  await api("/api/admin/settings", { body: { registration_open: $("#ad-reg").checked, ai_daily_limit: +$("#ad-limit").value || 0 } });
  toast("Settings saved");
};

boot().catch((e) => toast(e.message));

// ---------------- tutorials ----------------
const tut = { list: [], groups: [], filter: "All", cur: null, heads: [], page: 0, saveT: null, pending: null };
const pad2 = (n) => String(n).padStart(2, "0");
const tutPct = (t) => (t.done ? 100 : t.sections ? Math.round((t.max_page / t.sections) * 100) : 0);
const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");
function tutStatus(t) {
  if (t.done) return `<span class="done">Done</span>`;
  if (t.page) return `<span class="reading">Part ${t.page} of ${t.sections}</span>`;
  return `<span>Not started</span>`;
}

async function loadTutorials() {
  $("#tut-add-toggle").classList.toggle("hidden", state.meta?.role !== "admin");
  try {
    await tut.pending; tut.pending = null;
    const d = await api("/api/tutorials");
    tut.list = d.tutorials; tut.groups = d.groups;
  } catch (e) { $("#tut-grid").innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
  $("#ta-group").innerHTML = tut.groups.map((g) => `<option>${esc(g)}</option>`).join("");
  renderTutorials();
}
function renderTutorials() {
  const L = tut.list;
  if (!L.length) {
    $("#tut-filters").innerHTML = ""; $("#tut-continue").innerHTML = "";
    $("#tut-grid").innerHTML = `<p class="empty">No tutorials yet. ${state.meta?.role === "admin" ? "Use Add tutorial to upload your first one." : "Your admin hasn't added any."}</p>`;
    return;
  }
  const last = L.filter((t) => t.page && !t.done).sort((a, b) => b.updated - a.updated)[0];
  $("#tut-continue").innerHTML = last ? `<div class="tut-continue">
      <div><small>Pick up where you left off</small><h2>${esc(last.title)}</h2>
        <p>Part ${last.page} of ${last.sections}${last.section ? ` · ${esc(last.section)}` : ""}</p>
        <div class="tut-bar"><i style="width:${tutPct(last)}%"></i></div></div>
      <div><button class="btn gold" data-open="${esc(last.id)}">Resume</button></div></div>` : "";
  const counts = {};
  L.forEach((t) => (counts[t.group] = (counts[t.group] || 0) + 1));
  const groups = ["All", ...tut.groups.filter((g) => counts[g])];
  if (!groups.includes(tut.filter)) tut.filter = "All";
  $("#tut-filters").innerHTML = groups.map((g) => `<button class="tut-chip${g === tut.filter ? " active" : ""}" role="tab" aria-selected="${g === tut.filter}" data-group="${esc(g)}">
    ${esc(g)}<span>${g === "All" ? L.length : counts[g]}</span></button>`).join("");
  const shown = tut.filter === "All" ? L : L.filter((t) => t.group === tut.filter);
  $("#tut-grid").innerHTML = shown.map((t) => `<button class="tut-tile" data-open="${esc(t.id)}">
      <span class="tut-top"><span>${esc(t.group)}</span><span>${t.minutes} min read</span></span>
      <span class="tut-title">${esc(t.title)}</span>
      ${t.blurb ? `<p class="tut-blurb">${esc(t.blurb)}</p>` : ""}
      <ol class="tut-outline">${t.outline.map((s, i) => `<li><b>${pad2(i + 1)}</b><span>${esc(s)}</span></li>`).join("")}
        ${t.sections > t.outline.length ? `<li class="more">+${t.sections - t.outline.length} more parts</li>` : ""}</ol>
      <span class="tut-foot"><span>${t.sections} parts</span>${tutStatus(t)}</span>
      <span class="tut-bar" aria-hidden="true"><i class="${t.done ? "done" : ""}" style="width:${tutPct(t)}%"></i></span></button>`).join("");
}
$("#tut-filters").addEventListener("click", (e) => { const b = e.target.closest("[data-group]"); if (b) { tut.filter = b.dataset.group; renderTutorials(); } });
$("#view-tutorials").addEventListener("click", (e) => { const b = e.target.closest("[data-open]"); if (b) openTutorial(b.dataset.open); });
$("#tut-add-toggle").onclick = () => $("#tut-add").classList.toggle("hidden");
$("#tut-add").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = $("#ta-file").files[0]; if (!f) return;
  const fd = new FormData();
  fd.append("file", f); fd.append("title", $("#ta-title").value); fd.append("group", $("#ta-group").value); fd.append("blurb", $("#ta-blurb").value);
  busy($("#ta-save"), true, "Turning it into a lesson"); $("#ta-status").textContent = "";
  try {
    const r = await fetch("/api/admin/tutorials", { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || `Upload failed (${r.status})`);
    $("#ta-status").textContent = `Added: ${d.sections} parts, about ${Math.max(1, Math.round(d.words / 200))} min read.`;
    e.target.reset(); await loadTutorials();
  } catch (err) { $("#ta-status").textContent = err.message; }
  busy($("#ta-save"), false);
});

// ---- lesson rendering ----
const CALLOUT_KIND = { "say this": "say", "teach it back": "say", "interview": "say", "my take": "say", "say": "say",
  tip: "tip", expected: "tip", remember: "tip", "key idea": "key", "real output": "tip", why: "tip", check: "tip",
  careful: "warn", warning: "warn", important: "warn",
  practice: "task", task: "task", "try it": "task", "your turn": "task", note: "note" };
function diagramHtml(kind, body) {
  const items = body.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
    const m = l.match(/^(\w+):\s*(.*)$/); const tone = m ? m[1] : "plain"; const rest = m ? m[2] : l;
    const [title, ...det] = rest.split(" | ");
    return { tone, title, det: det.join(" | ") };
  });
  const boxes = items.filter((n) => n.tone !== "note"), notes = items.filter((n) => n.tone === "note");
  const node = (n) => `<div class="dg-node t-${esc(n.tone)}"><b>${esc(n.title)}</b>${n.det ? `<span>${esc(n.det)}</span>` : ""}</div>`;
  const inner = kind === "flow" ? boxes.map(node).join(`<span class="dg-arrow" aria-hidden="true">→</span>`) : boxes.map(node).join("");
  const cls = kind === "flow" || kind === "steps" ? "dg-flow" : "dg-grid";
  const ann = notes.length ? `<ul class="dg-notes">${notes.map((n) => `<li>${esc(n.title)}${n.det ? ` — ${esc(n.det)}` : ""}</li>`).join("")}</ul>` : "";
  return `<figure class="dg"><div class="${cls}">${inner}</div>${ann}</figure>`;
}
function slug(s, used) {
  let b = "p-" + (s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "part"), k = b, i = 2;
  while (used.has(k)) k = `${b}-${i++}`;
  used.add(k); return k;
}
function renderLesson(text) {
  // our diagram blocks become HTML before Markdown runs
  const src = text.replace(/```diagram (\w+)\n([\s\S]*?)```/g, (_, k, body) => "\n" + diagramHtml(k, body) + "\n");
  const html = window.marked ? DOMPurify.sanitize(marked.parse(src)) : md(src);
  const box = document.createElement("div");
  box.className = "lesson-body";
  box.innerHTML = html;
  // callouts: a quote that starts with a bold label
  box.querySelectorAll("blockquote").forEach((q) => {
    const first = q.querySelector("p > strong:first-child");
    const m = first && first.textContent.match(/^([^:]{2,24}):?$/);
    const label = m ? m[1].trim() : "";
    const key = label.toLowerCase().replace(/\s*\[.*?\]\s*/g, "").trim();
    const kind = CALLOUT_KIND[key] || (label && label === label.toUpperCase() ? "note" : null);
    const div = document.createElement("div");
    div.className = `callout ${kind || "note"}`;
    if (kind) {
      first.remove();
      const lab = document.createElement("span");
      lab.className = "callout-label"; lab.textContent = cap(label.toLowerCase());
      div.appendChild(lab);
      const p = q.querySelector("p"); if (p) p.innerHTML = p.innerHTML.replace(/^\s+/, "");
    }
    while (q.firstChild) div.appendChild(q.firstChild);
    q.replaceWith(div);
  });
  // code blocks get a header with the language and a copy button
  box.querySelectorAll("pre > code").forEach((c) => {
    const pre = c.parentElement, lang = ([...c.classList].find((x) => x.startsWith("language-")) || "").replace("language-", "");
    const wrap = document.createElement("div");
    wrap.className = "code-block";
    wrap.innerHTML = `<div class="code-head"><span>${esc({ bash: "Terminal", powershell: "PowerShell", python: "Python", json: "JSON", yaml: "YAML" }[lang] || lang || "Code")}</span><button class="code-copy" type="button">Copy</button></div>`;
    pre.replaceWith(wrap); wrap.appendChild(pre);
  });
  box.querySelectorAll("table").forEach((tb) => { const w = document.createElement("div"); w.className = "table-wrap"; tb.replaceWith(w); w.appendChild(tb); });
  box.querySelectorAll("a[href^='http']").forEach((a) => { a.target = "_blank"; a.rel = "noopener"; });
  // sections: ## headings, or ### when the lesson has only one or two ##
  const used = new Set();
  box.querySelectorAll("h2,h3").forEach((h) => (h.id = slug(h.textContent, used)));
  const h2 = [...box.querySelectorAll("h2")], h3 = [...box.querySelectorAll("h3")];
  const heads = h2.length >= 3 ? h2 : h3.length > h2.length ? h3 : h2;
  heads.forEach((h, i) => {
    h.classList.add("sec"); h.dataset.n = pad2(i + 1);
    // the counter numbers parts, so drop the notes' own "1." / "A3." prefixes
    const first = h.firstChild;
    if (first && first.nodeType === 3) first.textContent = first.textContent.replace(/^\s*[A-Z]?\d{1,2}[.)]\s+/, "");
  });
  return { box, heads };
}
$("#rd-article").addEventListener("click", (e) => {
  const b = e.target.closest(".code-copy");
  if (!b) return;
  const code = b.closest(".code-block").querySelector("code").innerText;
  navigator.clipboard?.writeText(code).then(() => { b.textContent = "Copied"; b.classList.add("ok"); setTimeout(() => { b.textContent = "Copy"; b.classList.remove("ok"); }, 1400); });
});

async function openTutorial(id) {
  closeReader();
  go("reader");
  const art = $("#rd-article");
  art.innerHTML = `<p class="empty">Opening the lesson<span class="dots"></span></p>`;
  $("#rd-toc").innerHTML = ""; $("#rd-where").textContent = "";
  try {
    const t = await api(`/api/tutorials/${encodeURIComponent(id)}`);
    tut.cur = t; tut.page = 0;
    $("#rd-crumb-group").textContent = t.group; $("#rd-crumb-title").textContent = t.title;
    const { box, heads } = renderLesson(t.content);
    tut.heads = heads;
    const toc = heads.map((h, i) => `<a href="#${h.id}" data-i="${i + 1}"><b>${pad2(i + 1)}</b><span>${esc(h.textContent)}</span></a>`).join("");
    art.innerHTML = `<header class="lesson-hero">
        <div class="lesson-eyebrow">${esc(t.group)}</div>
        <h1>${esc(t.title)}</h1>
        ${t.tagline ? `<p class="lesson-tagline">${esc(cap(t.tagline))}</p>` : t.blurb ? `<p class="lesson-tagline">${esc(t.blurb)}</p>` : ""}
        <div class="lesson-meta"><span>${t.minutes} min read</span><span>${heads.length} parts</span>${t.done ? "<span>Done</span>" : ""}</div>
        ${t.about ? `<p class="lesson-about">${esc(t.about)}</p>` : ""}
        ${heads.length ? `<details class="toc-mobile"><summary>In this lesson</summary>${toc}</details>` : ""}
      </header>`;
    art.appendChild(box);
    art.insertAdjacentHTML("beforeend", `<footer class="lesson-end">
        <div class="end-card"><small>Finished reading?</small><h3>Explain it out loud next</h3>
          <button class="btn small" id="rd-done">Mark as done</button></div>
        ${t.next ? `<button class="end-card" id="rd-next" data-id="${esc(t.next.id)}"><small>Next lesson · ${esc(t.next.group)}</small><h3>${esc(t.next.title)}</h3></button>`
          : `<button class="end-card" id="rd-next-all"><small>That was the last one</small><h3>Back to all tutorials</h3></button>`}
      </footer>
      ${state.meta?.role === "admin" ? `<div class="rd-admin"><button class="btn ghost small" id="rd-remove">Remove this tutorial</button></div>` : ""}`);
    $("#rd-toc").innerHTML = heads.length ? `<h3>In this lesson</h3>${toc}` : "";
    setDone(t.done);
    $("#rd-done").onclick = () => { const d = !tut.cur?.done; saveProgress(d); if (d) toast("Marked as done. Now explain it in a mock interview.", 3500); };
    $("#rd-next") && ($("#rd-next").onclick = (e) => openTutorial(e.currentTarget.dataset.id));
    $("#rd-next-all") && ($("#rd-next-all").onclick = () => go("tutorials"));
    $("#rd-remove") && ($("#rd-remove").onclick = removeTutorial);
    if (t.page > 1 && heads[t.page - 1]) {
      heads[t.page - 1].scrollIntoView({ block: "start" });
      toast(`Back at part ${t.page}: ${heads[t.page - 1].textContent}`, 2600);
    } else window.scrollTo(0, 0);
    trackLesson();
  } catch (e) {
    art.innerHTML = `<div class="rd-error"><p>Couldn't open this lesson. ${esc(e.message || "")}</p><button class="btn" id="rd-retry">Try again</button></div>`;
    $("#rd-retry").onclick = () => openTutorial(id);
  }
}
function trackLesson() {
  if (!tut.cur) return;
  const heads = tut.heads, line = window.innerHeight * 0.3;
  let cur = 0;
  for (let i = 0; i < heads.length; i++) { if (heads[i].getBoundingClientRect().top <= line) cur = i + 1; else break; }
  const doc = document.documentElement, max = doc.scrollHeight - window.innerHeight;
  const pct = max > 0 ? Math.min(100, (window.scrollY / max) * 100) : 100;
  $("#rd-progress").style.width = `${pct}%`;
  $("#rd-where").textContent = heads.length ? (cur ? `Part ${cur} of ${heads.length}` : `${heads.length} parts`) : "";
  $$("#rd-toc a").forEach((a) => a.classList.toggle("active", +a.dataset.i === cur));
  if (cur && cur !== tut.page) {
    tut.page = cur;
    clearTimeout(tut.saveT);
    tut.saveT = setTimeout(() => saveProgress(), 1200);
  }
}
async function saveProgress(done) {
  const t = tut.cur; if (!t) return;
  try {
    const r = await api(`/api/tutorials/${encodeURIComponent(t.id)}/progress`, { method: "PUT", body: { page: Math.max(1, tut.page), ...(done === undefined ? {} : { done }) } });
    t.done = r.done; if (tut.cur === t) setDone(r.done);
  } catch (e) { /* progress is a convenience; reading carries on */ }
}
function setDone(d) { const b = $("#rd-done"); if (!b) return; b.classList.toggle("is-done", d); b.textContent = d ? "Done ✓" : "Mark as done"; }
let lessonRaf = 0;
window.addEventListener("scroll", () => {
  if ($("#view-reader").classList.contains("hidden") || lessonRaf) return;
  lessonRaf = requestAnimationFrame(() => { lessonRaf = 0; trackLesson(); });
}, { passive: true });
document.addEventListener("click", (e) => {
  const a = e.target.closest("#rd-toc a, .toc-mobile a");
  if (!a) return;
  e.preventDefault();
  document.getElementById(a.getAttribute("href").slice(1))?.scrollIntoView({ block: "start", behavior: reduceMotion ? "auto" : "smooth" });
  a.closest("details")?.removeAttribute("open");
});
$("#rd-back").onclick = () => go("tutorials");
async function removeTutorial() {
  if (!tut.cur) return;
  const b = $("#rd-remove");
  if (b.dataset.armed !== "1") { b.dataset.armed = "1"; b.textContent = "Click again to remove it for everyone"; setTimeout(() => { b.dataset.armed = ""; b.textContent = "Remove this tutorial"; }, 4000); return; }
  await api(`/api/admin/tutorials/${encodeURIComponent(tut.cur.id)}`, { method: "DELETE" });
  tut.cur = null; toast("Tutorial removed"); go("tutorials");
}
function closeReader() {
  if (!tut.cur) return;
  clearTimeout(tut.saveT);
  if (tut.page) tut.pending = saveProgress();
  tut.cur = null; tut.heads = [];
}
