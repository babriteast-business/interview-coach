// Interview Coach front end (vanilla JS)
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const state = { iv: null, turn: null, timer: null, t0: 0, problem: null, thread: null, meta: null, lastFeedback: null };

async function api(path, opts = {}) {
  const r = await fetch(path, {
    method: opts.method || (opts.body ? "POST" : "GET"),
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (r.status === 401 && !path.startsWith("/api/auth")) { showLogin(); throw new Error("Please log in"); }
  const isText = (r.headers.get("content-type") || "").startsWith("text/plain");
  const data = isText ? await r.text() : await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `Error ${r.status}`);
  return data;
}
function toast(msg, ms = 4000) { const t = $("#toast"); t.textContent = msg; t.classList.remove("hidden"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), ms); }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function md(s) {
  if (window.marked && window.DOMPurify) return DOMPurify.sanitize(marked.parse(String(s || "")));
  return `<div style="white-space:pre-wrap">${esc(s)}</div>`;
}
function scoreClass(n) { return n >= 7 ? "s-good" : n >= 5 ? "s-mid" : "s-bad"; }
function barColor(n) { return n >= 7 ? "var(--good)" : n >= 5 ? "var(--warn)" : "var(--bad)"; }
function busy(btn, on, label) { if (!btn) return; if (on) { btn._t = btn.textContent; btn.disabled = true; btn.innerHTML = `${label || "Working"}<span class="dots"></span>`; } else { btn.disabled = false; btn.textContent = btn._t; } }
function download(name, text) { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type: "text/markdown" })); a.download = name; a.click(); }

// ---------------- auth ----------------
async function boot() {
  const s = await api("/api/auth/status");
  if (s.logged_in) { showShell(s.username); } else { showLogin(s.can_register); }
}
function setTab(mode) {
  $("#login-form").dataset.mode = mode;
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === mode));
  $("#login-btn").textContent = mode === "register" ? "Create account" : "Log in";
  $("#lg-pass2-wrap").classList.toggle("hidden", mode !== "register");
  $("#lg-pass").autocomplete = mode === "register" ? "new-password" : "current-password";
  $("#register-hint").textContent = mode === "register" ? "New accounts need the admin's approval before first login." : "";
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
  const mode = e.target.dataset.mode;
  const body = { username: $("#lg-user").value.trim(), password: $("#lg-pass").value };
  try {
    if (mode === "register") {
      if (body.password !== $("#lg-pass2").value) throw new Error("Passwords don't match");
      const r = await api("/api/auth/register", { body });
      setTab("login"); $("#login-ok").textContent = r.message; $("#lg-pass").value = "";
    } else {
      await api("/api/auth/login", { body });
      showShell(body.username);
    }
  } catch (err) { $("#login-err").textContent = err.message; }
});
$("#logout").onclick = async () => { await api("/api/auth/logout", { method: "POST" }); location.reload(); };

async function showShell(name) {
  $("#view-login").classList.add("hidden"); $("#shell").classList.remove("hidden");
  $("#who").textContent = `Signed in as ${name}`; $("#dash-name").textContent = `, ${name}`;
  state.meta = await api("/api/meta");
  const m = state.meta;
  $("#model-status").textContent = m.mock ? "Offline demo mode (MOCK_LLM=1)" : m.key_set ? "AI: OpenRouter free models" : "⚠ No OpenRouter API key set";
  $("#usage-status").textContent = m.ai_limit === null ? "Admin · unlimited AI" : `AI calls today: ${m.ai_used_today}/${m.ai_limit}`;
  $("#nav-admin").classList.toggle("hidden", m.role !== "admin");
  $("#pw-card").classList.toggle("hidden", m.role === "admin");
  $("#p-locked").classList.toggle("hidden", m.trusted);
  $("#p-run").disabled = !m.trusted;
  $("#s-cat").innerHTML = `<option value="mixed">All topics (realistic mix)</option>` +
    Object.entries(m.categories).map(([c, n]) => `<option value="${esc(c)}">${esc(c)} (${n})</option>`).join("");
  $("#bank-info").textContent = `${m.total_questions} questions in your bank${m.bank_updated ? " · refreshed " + m.bank_updated : ""}.`;
  buildChips();
  go("dashboard");
}

// ---------------- navigation ----------------
function go(view) {
  $$(".view").forEach((v) => v.classList.add("hidden"));
  $(`#view-${view}`).classList.remove("hidden");
  $$(".sidebar nav a").forEach((a) => a.classList.toggle("active", a.dataset.view === view || (view === "room" && a.dataset.view === "setup")));
  if (view === "dashboard") loadDashboard();
  if (view === "coding") loadProblems();
  if (view === "coach") loadThreads();
  if (view === "history") loadHistory();
  if (view === "profile") loadProfile();
  if (view === "admin") loadAdmin();
  window.scrollTo(0, 0);
}
$$(".sidebar nav a").forEach((a) => (a.onclick = () => go(a.dataset.view)));

// ---------------- dashboard ----------------
async function loadDashboard() {
  const s = await api("/api/stats");
  $("#st-answered").textContent = s.answered || 0;
  $("#st-avg").textContent = s.average ?? "–";
  $("#st-7d").textContent = s.avg_7d ?? "–";
  $("#st-code").textContent = `${s.coding_solved}/${s.coding_total}`;
  if (s.by_category.length) {
    $("#cat-bars").innerHTML = s.by_category.map((c) => `
      <div class="bar-row"><span>${esc(c.category)}</span>
      <div class="bar"><span style="width:${c.avg * 10}%;background:${barColor(c.avg)}"></span></div>
      <span class="muted">${c.avg} · ${c.n}</span></div>`).join("") +
      `<p class="muted small">Weakest topics are on top. Drill them until every bar is green (7+).</p>`;
  }
}
$$("[data-quick]").forEach((b) => (b.onclick = () => {
  const [track, cat, count] = b.dataset.quick.split("|");
  $("#s-track").value = track; $("#s-cat").value = cat; $("#s-count").value = count; $("#s-diff").value = "mixed";
  startInterview();
}));

// ---------------- interview ----------------
$("#start-btn").onclick = () => startInterview();
async function startInterview() {
  const btn = $("#start-btn"); busy(btn, true, "Preparing panel");
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
  $("#r-cat").textContent = q.category + (q.live ? " · fresh" : "");
  $("#r-progress").textContent = `Question ${index} of ${total}`;
  $("#r-follow").classList.toggle("hidden", !q.is_followup);
  $("#r-question").textContent = q.question;
  $("#r-answer").value = ""; $("#r-answer-box").classList.remove("hidden");
  $("#r-feedback").classList.add("hidden"); $("#r-feedback").innerHTML = "";
  startTimer();
  if ($("#s-voice").checked) speak(q.question);
  $("#r-answer").focus();
}
function startTimer() {
  clearInterval(state.timer); state.t0 = Date.now();
  state.timer = setInterval(() => {
    const s = Math.floor((Date.now() - state.t0) / 1000);
    $("#r-timer").textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    $("#r-timer").style.color = s > 180 ? "var(--bad)" : "";
  }, 1000);
}
function speak(text) {
  if (!("speechSynthesis" in window)) return toast("Your browser cannot read aloud.");
  speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(text); u.rate = 1; speechSynthesis.speak(u);
}
$("#r-speak").onclick = () => speak($("#r-question").textContent);

// speech-to-text answer (Chrome / Edge)
let rec = null;
$("#r-mic").onclick = () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return toast("Voice input needs Chrome or Edge.");
  if (rec) { rec.stop(); return; }
  rec = new SR(); rec.lang = "en-IN"; rec.continuous = true; rec.interimResults = true;
  const base = $("#r-answer").value ? $("#r-answer").value + " " : "";
  rec.onresult = (e) => { let t = ""; for (const r of e.results) t += r[0].transcript; $("#r-answer").value = base + t; };
  rec.onend = () => { rec = null; $("#r-mic").textContent = "🎤 Speak answer"; $("#r-mic-status").textContent = ""; };
  rec.start(); $("#r-mic").textContent = "■ Stop"; $("#r-mic-status").textContent = "Listening… speak naturally";
};

$("#r-submit").onclick = async () => {
  const btn = $("#r-submit");
  if (rec) rec.stop();
  busy(btn, true, "Panel is grading");
  try {
    const r = await api(`/api/interview/${state.iv.id}/answer`, { body: { turn_id: state.turn, answer: $("#r-answer").value } });
    clearInterval(state.timer); renderFeedback(r.feedback);
  } catch (e) { toast(e.message, 7000); } finally { busy(btn, false); }
};
$("#r-skip").onclick = () => nextQuestion(false, state.turn);

function renderFeedback(fb) {
  state.lastFeedback = fb;
  $("#r-answer-box").classList.add("hidden");
  const list = (a) => (a && a.length ? `<ul>${a.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p class="muted">–</p>`);
  $("#r-feedback").innerHTML = `
    <div class="card fb">
      <div class="score-head"><div class="score ${scoreClass(fb.score)}">${fb.score}</div>
        <div><h2 style="margin:0">${esc(fb.verdict || "")}</h2><div class="muted small">${esc(fb.delivery_tips || "")}</div></div></div>
      <div class="grid2"><div><h4>What landed</h4>${list(fb.strengths)}</div><div><h4>Gaps the panel noticed</h4>${list(fb.gaps)}</div></div>
      <div><h4>Your answer</h4><div class="muted" style="white-space:pre-wrap">${esc($("#r-answer").value)}</div></div>
      <div><h4>How a senior candidate would answer</h4><div class="model-ans">${esc(fb.model_answer || "")}
        </div><button class="btn ghost small" id="fb-read" style="margin-top:6px">🔊 Hear it</button></div>
      ${fb.key_points && fb.key_points.length ? `<div><h4>Checklist for this question</h4>${list(fb.key_points)}</div>` : ""}
      ${fb.follow_up ? `<div class="followup-box"><h4 style="color:var(--warn)">Interviewer's cross-question</h4><div>${esc(fb.follow_up)}</div></div>` : ""}
      <div class="row">
        ${fb.follow_up ? `<button class="btn primary" id="fb-follow">Answer the cross-question</button>` : ""}
        <button class="btn ${fb.follow_up ? "" : "primary"}" id="fb-next">Next question →</button>
        <button class="btn" id="fb-retry">Retry this question</button>
        <span class="spacer"></span><button class="btn ghost" id="fb-end">End &amp; get report</button>
      </div>
      <div class="muted small">Graded by ${esc(fb.model_used || "")}</div>
    </div>`;
  $("#r-feedback").classList.remove("hidden");
  $("#fb-read").onclick = () => speak(fb.model_answer || "");
  if ($("#fb-follow")) $("#fb-follow").onclick = () => nextQuestion(true);
  $("#fb-next").onclick = () => nextQuestion(false);
  $("#fb-retry").onclick = () => { $("#r-feedback").classList.add("hidden"); $("#r-answer-box").classList.remove("hidden"); startTimer(); $("#r-answer").focus(); };
  $("#fb-end").onclick = () => finishInterview();
  $("#r-feedback").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function nextQuestion(followup, skipId) {
  try {
    const r = await api(`/api/interview/${state.iv.id}/next`, { body: { followup, skip_turn_id: skipId || null } });
    if (r.done) return finishInterview();
    showQuestion(r, Math.max(1, r.index), r.total);
  } catch (e) { toast(e.message); }
}

async function finishInterview() {
  clearInterval(state.timer); go("report");
  $("#view-report").innerHTML = `<h1>Debrief</h1><p class="muted">The panel is writing your debrief<span class="dots"></span></p>`;
  try {
    const r = await api(`/api/interview/${state.iv.id}/finish`, { method: "POST" });
    renderReport(r, state.iv.id);
  } catch (e) { $("#view-report").innerHTML = `<h1>Debrief</h1><p class="err">${esc(e.message)}</p>`; }
}
function renderReport(r, iid) {
  const list = (a) => (a && a.length ? `<ul>${a.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "");
  $("#view-report").innerHTML = `
    <h1>Debrief</h1>
    <div class="card fb">
      <div class="score-head"><div class="score ${scoreClass(r.average)}">${r.average}</div>
        <div><h2 style="margin:0">${esc(r.ready_for || "")}</h2><div class="muted">${r.answered} answers graded</div></div></div>
      <p>${esc(r.overall || "")}</p>
      <div class="grid2"><div><h4>Fix these first</h4>${list(r.top_fixes)}</div><div><h4>Next 48 hours</h4>${list(r.study_plan)}</div></div>
      <table class="table">${(r.turns || []).map((t) => `<tr><td>${t.is_followup ? "↳ " : ""}${esc(t.question)}</td><td class="muted">${esc(t.category)}</td><td><b>${t.score}</b>/10</td></tr>`).join("")}</table>
      <div class="row"><button class="btn primary" id="rep-again">New interview</button>
        <button class="btn" id="rep-export">⬇ Export Q&amp;A with model answers (.md)</button></div>
    </div>`;
  $("#rep-again").onclick = () => go("setup");
  $("#rep-export").onclick = async () => download(`interview-${iid}.md`, await api(`/api/interview/${iid}/export`));
}

// ---------------- coding ----------------
async function loadProblems() {
  const ps = await api("/api/coding/problems");
  $("#p-list").innerHTML = ps.map((p) => `<div class="p-item ${p.solved ? "solved" : ""} ${state.problem?.id === p.id ? "active" : ""}" data-id="${p.id}">
    ${esc(p.title)}<span class="small muted">${p.kind.toUpperCase()} · ${p.difficulty} · ${esc(p.topic)}</span></div>`).join("");
  $$(".p-item").forEach((el) => (el.onclick = () => openProblem(el.dataset.id)));
}
async function openProblem(id) {
  const p = await api(`/api/coding/problems/${id}`);
  state.problem = p;
  $$(".p-item").forEach((el) => el.classList.toggle("active", el.dataset.id === id));
  $("#p-empty").classList.add("hidden"); $("#p-body").classList.remove("hidden");
  $("#p-title").textContent = p.title; $("#p-diff").textContent = p.difficulty; $("#p-topic").textContent = p.topic;
  $("#p-tests").textContent = `${p.test_count} tests`;
  const samples = p.kind === "sql" ? "" : `<p class="small muted">Example tests:</p><pre>${p.sample_tests.map((t) => `${esc(t.expr)}  →  ${esc(JSON.stringify(t.expected))}`).join("\n")}</pre>`;
  $("#p-prompt").innerHTML = md(p.prompt) + samples;
  const saved = localStorageGet(`code-${id}`);
  $("#p-code").value = saved || p.starter; $("#p-result").innerHTML = "";
}
function localStorageGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function localStorageSet(k, v) { try { localStorage.setItem(k, v); } catch {} }
$("#p-code").addEventListener("keydown", (e) => {
  if (e.key === "Tab") { e.preventDefault(); const t = e.target, s = t.selectionStart; t.value = t.value.slice(0, s) + "    " + t.value.slice(t.selectionEnd); t.selectionStart = t.selectionEnd = s + 4; }
});
$("#p-code").addEventListener("input", () => state.problem && localStorageSet(`code-${state.problem.id}`, $("#p-code").value));
$("#p-reset").onclick = () => { $("#p-code").value = state.problem.starter; localStorageSet(`code-${state.problem.id}`, ""); };
$("#p-run").onclick = async () => {
  const btn = $("#p-run"); busy(btn, true, "Running");
  try {
    const r = await api(`/api/coding/problems/${state.problem.id}/run`, { body: { code: $("#p-code").value } });
    const all = r.passed === r.total && r.total > 0;
    $("#p-result").innerHTML = `<h3 style="margin-top:14px;color:${all ? "var(--good)" : "var(--bad)"}">${all ? "✓ All tests passed" : `${r.passed}/${r.total} tests passed`}</h3>
      ${r.error ? `<div class="res fail">${esc(r.error)}</div>` : ""}
      <div class="results">${(r.results || []).map((t) => `<div class="res ${t.ok ? "ok" : "fail"}">${t.ok ? "✓" : "✗"} ${esc(t.name)}${t.ok ? "" : t.error ? `\n   ${esc(t.error)}` : `\n   expected ${esc(typeof t.expected === "string" ? t.expected : JSON.stringify(t.expected))}\n   got      ${esc(typeof t.got === "string" ? t.got : JSON.stringify(t.got))}`}</div>`).join("")}</div>
      ${r.stdout ? `<p class="small muted">Printed output:</p><pre>${esc(r.stdout)}</pre>` : ""}
      ${all ? `<p class="muted small">Now say out loud: approach, time complexity, space complexity, edge cases. Then hit “AI review”.</p>` : ""}`;
    if (all) loadProblems();
  } catch (e) { toast(e.message); } finally { busy(btn, false); }
};
$("#p-review").onclick = async () => {
  const btn = $("#p-review"); busy(btn, true, "Reviewing");
  try {
    const r = await api(`/api/coding/problems/${state.problem.id}/review`, { body: { code: $("#p-code").value } });
    $("#p-result").insertAdjacentHTML("beforeend", `<div class="card md" style="margin-top:14px">${md(r.review)}</div>`);
  } catch (e) { toast(e.message, 7000); } finally { busy(btn, false); }
};
$("#p-solution").onclick = async () => {
  if (!confirm("Try it yourself first? Show the reference solution anyway?")) return;
  const r = await api(`/api/coding/problems/${state.problem.id}/solution`);
  $("#p-result").insertAdjacentHTML("beforeend", `<p class="small muted" style="margin-top:14px">Reference solution:</p><pre>${esc(r.solution)}</pre>`);
};

// ---------------- coach ----------------
const CHIPS = [
  ["Intro scripts", "Write my 'Tell me about yourself' introduction in three versions: 30 seconds, 90 seconds and 2 minutes, for a remote {track} role. Make it confident and impact-focused, built only from my profile. Mark anything you need from me as [FILL]."],
  ["Curate showcase projects", "Curate 5 portfolio projects that would most impress hiring managers for remote {track} roles right now (agents, MCP, RAG, evals, MLOps). For each: the business problem, architecture, stack, what to measure, a 1-week build plan, and why interviewers find it impressive. Prioritise ones I can build fastest with my skills."],
  ["Project script (fill in)", "Write my interview showcase script for this project.\nProject name: \nProblem it solved: \nWho used it: \nStack: \nMy role: \nHardest problem I faced: \nResult / numbers: \n\nGive me: a 60-second pitch, the full STAR story, architecture explanation, 3 challenges and how I solved them, what I'd do differently, and the 10 cross-questions an interviewer will ask with strong answers.", true],
  ["Cross-questions drill", "Take the project I describe next and act as a tough interviewer: list the 12 hardest cross-questions you'd ask to test whether I really built it, with what a strong answer must contain. Project: ", true],
  ["Explain a concept", "Explain this concept in 3 levels (simple analogy, working engineer, senior/architect with trade-offs), then give me a 60-second interview answer I can say out loud: ", true],
  ["Weak-topic plan", "__WEAK__"],
  ["Salary negotiation", "Give me word-for-word scripts for salary negotiation for a remote {track} role: answering 'expected CTC', responding to a low offer, asking for a joining bonus, and negotiating two offers against each other. Include how to research the market range."],
  ["Questions to ask them", "Give me 10 smart questions to ask the interviewer at the end of an AI Engineer interview that show senior thinking, grouped by who I'm talking to (recruiter, hiring manager, tech lead)."],
];
function buildChips() {
  $("#c-chips").innerHTML = CHIPS.map((c, i) => `<button class="chip" data-i="${i}">${esc(c[0])}</button>`).join("");
  $$("#c-chips .chip").forEach((b) => (b.onclick = async () => {
    const [, text, edit] = CHIPS[b.dataset.i];
    const track = $("#c-track").selectedOptions[0].text;
    if (text === "__WEAK__") {
      const s = await api("/api/stats");
      const weak = s.by_category.filter((c) => c.avg < 7).map((c) => `${c.category} (${c.avg}/10)`);
      $("#c-input").value = weak.length
        ? `My weakest interview topics right now are: ${weak.join(", ")}. Build me a 7-day study and practice plan to get each to 8+/10, with daily tasks, the key concepts to master, and 3 practice questions per topic.`
        : `I haven't done enough mock interviews yet. Give me a 7-day plan covering the most-asked {track} topics, with daily tasks and practice questions.`.replace("{track}", track);
      return sendCoach();
    }
    $("#c-input").value = text.replaceAll("{track}", track);
    if (edit) { $("#c-input").focus(); toast("Fill in the details, then Send."); } else sendCoach();
  }));
}
async function loadThreads() {
  const ts = await api("/api/coach/threads");
  $("#c-threads").innerHTML = ts.map((t) => `<div class="thread ${state.thread === t.id ? "active" : ""}" data-id="${t.id}"><span title="${esc(t.title)}">${esc(t.title)}</span><button data-del="${t.id}" title="Delete">✕</button></div>`).join("") || `<p class="muted small">No chats yet.</p>`;
  $$(".thread").forEach((el) => (el.onclick = (e) => { if (e.target.dataset.del) return; openThread(+el.dataset.id); }));
  $$("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!confirm("Delete this chat?")) return;
    await api(`/api/coach/threads/${b.dataset.del}`, { method: "DELETE" });
    if (state.thread === +b.dataset.del) newChat(); loadThreads();
  }));
}
function newChat() {
  state.thread = null;
  $("#c-messages").innerHTML = `<div class="starter"><p class="muted">Ask anything. Or tap a starter:</p><div class="chips" id="c-chips"></div></div>`;
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
  const wait = addMsg("assistant", "Thinking…"); const btn = $("#c-send"); busy(btn, true, "…");
  try {
    const r = await api("/api/coach/send", { body: { thread_id: state.thread, message: text, track: $("#c-track").value } });
    wait.remove(); addMsg("assistant", r.reply);
    if (!state.thread) { state.thread = r.thread_id; loadThreads(); }
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
  $("#h-table").innerHTML = `<tr><th>Date</th><th>Track</th><th>Topic</th><th>Answered</th><th>Avg</th></tr>` +
    (rows.map((r) => `<tr class="click" data-id="${r.id}"><td>${new Date(r.created * 1000).toLocaleString()}</td><td>${r.track}</td><td>${esc(r.category)}</td><td>${r.answered}/${r.total}</td><td><b>${r.avg ? r.avg.toFixed(1) : "–"}</b></td></tr>`).join("") ||
     `<tr><td colspan="5" class="muted">No interviews yet.</td></tr>`);
  $$("#h-table tr.click").forEach((tr) => (tr.onclick = () => showTranscript(+tr.dataset.id)));
}
async function showTranscript(id) {
  const d = await api(`/api/interview/${id}/transcript`);
  $("#h-detail").innerHTML = `<div class="row"><h2 style="margin:0">Interview #${id}</h2><span class="spacer"></span>
    <button class="btn" id="h-export">⬇ Export .md</button>
    ${d.interview.finished ? "" : `<button class="btn primary" id="h-resume">Resume</button>`}</div>` +
    d.turns.map((t, i) => `<div class="card" style="margin-bottom:10px"><div class="row" style="margin:0"><span class="pill">${esc(t.category)}</span>${t.is_followup ? `<span class="pill warn">Follow-up</span>` : ""}<span class="spacer"></span><b>${t.score ?? "–"}/10</b></div>
      <p><b>Q${i + 1}. ${esc(t.question)}</b></p><p class="muted" style="white-space:pre-wrap">${esc(t.answer || "(not answered)")}</p>
      ${t.feedback.model_answer ? `<details><summary>Model answer &amp; gaps</summary><div class="model-ans">${esc(t.feedback.model_answer)}</div><ul>${(t.feedback.gaps || []).map((g) => `<li>${esc(g)}</li>`).join("")}</ul></details>` : ""}</div>`).join("");
  $("#h-export").onclick = async () => download(`interview-${id}.md`, await api(`/api/interview/${id}/export`));
  if ($("#h-resume")) $("#h-resume").onclick = () => {
    state.iv = { id, total: d.interview.total };
    const open = d.turns.find((t) => !t.answered);
    go("room");
    if (open) showQuestion({ turn_id: open.id, question: open.question, category: open.category, is_followup: !!open.is_followup }, d.turns.filter((t) => !t.is_followup).length, d.interview.total);
    else nextQuestion(false);
  };
  $("#h-detail").scrollIntoView({ behavior: "smooth" });
}

// ---------------- profile ----------------
async function loadProfile() { $("#pf-text").value = (await api("/api/profile")).text; $("#pf-status").textContent = ""; }
$("#pf-save").onclick = async () => {
  await api("/api/profile", { method: "PUT", body: { text: $("#pf-text").value } });
  $("#pf-status").textContent = "Saved. The interviewer and coach will use this from your next message.";
};

$("#pw-save").onclick = async () => {
  try {
    await api("/api/auth/password", { body: { old: $("#pw-old").value, new: $("#pw-new").value } });
    $("#pw-status").textContent = "Password changed."; $("#pw-old").value = $("#pw-new").value = "";
  } catch (e) { $("#pw-status").textContent = e.message; }
};

// ---------------- admin ----------------
async function loadAdmin() {
  const d = await api("/api/admin/users");
  $("#ad-reg").checked = d.registration_open; $("#ad-limit").value = d.ai_daily_limit;
  const btn = (id, action, label, cls = "") => `<button class="btn small ${cls}" data-uid="${id}" data-act="${action}">${label}</button>`;
  $("#ad-users").innerHTML = `<tr><th>User</th><th>Status</th><th>Joined</th><th>Answers</th><th>AI today</th><th>Actions</th></tr>` +
    d.users.map((u) => `<tr><td><b>${esc(u.username)}</b>${u.role === "admin" ? ` <span class="pill">admin</span>` : ""}${u.trusted && u.role !== "admin" ? ` <span class="pill ghost">trusted</span>` : ""}</td>
      <td><span class="badge b-${u.status}">${u.status}</span></td>
      <td class="muted small">${new Date(u.created * 1000).toLocaleDateString()}</td><td>${u.answers}</td><td>${u.ai_today || 0}</td>
      <td>${u.role === "admin" ? `<span class="muted small">you</span>` : [
        u.status === "pending" ? btn(u.id, "approve", "Approve", "primary") : "",
        u.status === "active" ? btn(u.id, "disable", "Disable") : "",
        u.status === "disabled" ? btn(u.id, "enable", "Enable") : "",
        u.trusted ? btn(u.id, "untrust", "Untrust") : btn(u.id, "trust", "Trust for code"),
        btn(u.id, "delete", "Delete", "ghost")].join("")}</td></tr>`).join("");
  $$("[data-act]").forEach((b) => (b.onclick = async () => {
    if (b.dataset.act === "delete" && !confirm("Delete this user and all their data? This cannot be undone.")) return;
    try { await api(`/api/admin/users/${b.dataset.uid}`, { body: { action: b.dataset.act } }); loadAdmin(); } catch (e) { toast(e.message); }
  }));
}
$("#ad-save").onclick = async () => {
  await api("/api/admin/settings", { body: { registration_open: $("#ad-reg").checked, ai_daily_limit: +$("#ad-limit").value || 0 } });
  toast("Settings saved");
};

boot().catch((e) => toast(e.message));
