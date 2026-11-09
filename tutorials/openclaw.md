---
title: OpenClaw
group: Agents & tools
order: 12
blurb: Setup, skills, safety and real examples
tagline: setup · skills · safety · real examples
about: Docs checked Oct 2026 · Not run by me: verify commands and paths on your machine. Practise in a safe lab.
---

## OpenClaw - from scratch to interview-ready

> **Careful:** OpenClaw is an always-on personal assistant that can use tools on your computer and talk to you through chat apps. That makes it powerful and risky. Practise on a spare machine, VM or WSL with **no personal accounts** connected at first. The docs themselves say prompt injection is a risk even if you are the only sender.

### O0. What it is (say this in 20 seconds)

> **Say This:** OpenClaw is a self-hosted personal AI assistant. A Gateway process connects chat channels (Telegram, WhatsApp, Slack, Discord and more) to an agent that has tools and skills, with its persona and memory kept as plain files in a workspace.

<table><thead><tr><th>Piece</th><th>Meaning</th></tr></thead><tbody><tr><td><b>Gateway</b></td><td>The long-running process; listens on port <b>18789</b>; runs as a background service once installed</td></tr><tr><td><b>Control UI /</b><br><b>dashboard</b></td><td>Browser UI opened with <code>openclaw dashboard</code> ; chat, settings, files</td></tr><tr><td><b>Channels</b></td><td>Telegram (fastest, only needs a bot token), WhatsApp, Slack, Discord, Teams, Signal and others</td></tr><tr><td><b>Workspace</b></td><td>Agent&#x27;s home: <code>~/.openclaw/workspace</code> . Separate from <code>~/.openclaw/</code> (config, credentials, sessions)</td></tr><tr><td><b>AGENTS.md</b></td><td>Operating instructions and memory-use guidance, loaded each session</td></tr><tr><td><b>SOUL.md</b></td><td>Persona, tone, boundaries, loaded each session</td></tr><tr><td><b>USER.md</b></td><td>Your preferences and active projects (4,000-character budget)</td></tr><tr><td><b>Skills</b></td><td>Folders with <code>SKILL.md</code> ; teach the agent how and when to use tools; ClawHub is the public registry</td></tr><tr><td><b>Pairing</b></td><td>Unknown senders get a code; their messages never reach the model until you approve</td></tr></tbody></table>

### O1. Setup on Windows

Requirement from the docs: **Node.js 24.16+ or 26.1+** (Node 26 recommended). Check with `node --version`; install from nodejs.org if older. You also need a model route: an existing Claude Code or Codex CLI login, or a provider API key.

```powershell
# Option 1: fastest path (runs the Gateway in this terminal until Ctrl+C)
npx openclaw@latest
#   choose "Quick start"
# Option 2: standard install (PowerShell)
iwr -useb https://openclaw.ai/install.ps1 | iex
#   the installer starts the onboarding wizard
# keep it running in the background (stop the foreground one with Ctrl+C first)
openclaw gateway install
openclaw gateway status       # should show it listening on 18789
openclaw dashboard            # opens the Control UI; send a test message
```

More settings later: `openclaw configure`. Step-by-step wizard: `openclaw onboard --classic`. Problems: `openclaw doctor` (readable findings) or `openclaw triage` (read-only diagnosis; docs say it leaves out secrets, tokens and raw chats from its prompt).

The docs also mention a native Windows Hub app and a WSL2 Gateway as supported paths. Native Windows runs the Gateway as a Scheduled Task (with a Startup-folder fallback).

### O2. Practise, step by step

1. **Chat in the dashboard.** Ask "what tools do you have?" and note the answer.
2. **Give it a persona.** Dashboard → Settings → Agents → Files, edit `SOUL.md` (or edit the file in the workspace):

```
# SOUL.md
You are my interview mentor. Be direct and specific. Say when an answer is vague.
No flattery. Ask one question at a time. Never claim you ran something you didn't.
```

3. **First skill: hello-world** (the docs' own example):

```powershell
# PowerShell
mkdir "$env:USERPROFILE\.openclaw\workspace\skills\hello-world"    # path assumed from ~; verify on
your machine
# SKILL.md inside that folder
---
name: hello-world
description: A simple skill that prints a greeting.
---
# Hello World
When the user asks for a greeting, use the `exec` tool to run:
echo "Hello from your custom skill!"
```

```bash
openclaw skills list                           # confirm it loaded
openclaw agent --message "give me a greeting"    # test from the CLI
# or in chat:  /skill hello-world
openclaw gateway restart                       # if it doesn't show up
```

Rules for skills: `name` required (lowercase, digits, hyphens), `description` required (one line, under 160 characters). Optional: `user-invocable`, `disable-model-invocation`.

4. **Skill that uses your own data: interview-drill.** Copy your question bank into the workspace, then make the skill:

```powershell
mkdir "$env:USERPROFILE\.openclaw\workspace\drill"
copy C:\Users\god\JobSprint\Coach\questions.json "$env:USERPROFILE\.openclaw\workspace\drill\"   #
adjust to where you unzipped it
# skills\interview-drill\SKILL.md
---
name: interview-drill
description: Drill me with one interview question at a time from my question bank and score my
answer.
---
# Interview drill
1. Read drill/questions.json from the workspace.
2. Pick one random question from the topic I name (or any topic).
3. Ask only that question and wait for my answer.
4. Then reply: score out of 10, points covered, points missed, one tip.
5. Never show the key points before I answer.
```

Say "start an interview drill on RAG". Skill precedence (highest first): workspace `skills/`, project `.agents/skills`, personal `~/.agents/skills`, managed skills, bundled skills. Same name = highest wins.

5. **Connect Telegram.** Create a bot with BotFather in Telegram to get a token, run `openclaw configure`, choose Telegram and paste it. Message your bot: you get a pairing code. Approve it with `openclaw pairing approve` (check `openclaw pairing --help` for the exact arguments).
6. **Audit yourself:** `openclaw security audit --deep` and `openclaw gateway status`. Fix the first findings: public binds without auth, open DMs or groups with tools enabled, exposed browser control.

### O3. Security model (the part that impresses)

**Pairing and allowlists** for DMs and groups. Don't open DMs to everyone with tools on. **Gateway exposure:** bind to loopback or reach it only through an authenticated private path (tailnet, SSH tunnel, trusted proxy). **Prompt injection:** web pages, emails, documents and attachments can carry instructions. Use a read-only or tool-disabled agent to summarise untrusted content; keep `web_search`, `web_fetch` and `browser` off for tool-enabled agents; use sandboxing and strict tool allowlists. **The workspace is not a sandbox.** Absolute paths can still reach the host unless sandboxing is on. **Skills and plugins are code you choose to trust.** ClawHub scan results help but are not a complete security boundary. Back up the workspace in a private Git repo; never commit secrets.

### OpenClaw: pros, cons, interview answers

<table><thead><tr><th>Pros</th><th>Cons / risks</th></tr></thead><tbody><tr><td>Self-hosted, always-on assistant reachable from chat apps; persona and memory as plain editable files; skills ecosystem; multi-agent routing; sensible pairing model</td><td>Broad host access = large attack surface; prompt injection; third- party skills are untrusted code; fast-moving project with recent Node requirements; costs per message; not a framework for building customer products</td></tr></tbody></table>

<table><thead><tr><th>Question</th><th>Crisp answer</th></tr></thead><tbody><tr><td>What did you learn from it?</td><td>The threat model of always-on agents: pairing, loopback binding, tool allowlists, sandboxing, treating skills as code, and prompt injection from every external input.</td></tr><tr><td>Skills vs AGENTS.md vs SOUL.md?</td><td>AGENTS.md = operating rules; SOUL.md = persona and boundaries; skills = loadable how-to for specific tools or tasks.</td></tr><tr><td>Would you deploy it for a client?</td><td>Not as-is for sensitive work. I&#x27;d isolate it, restrict tools, run the security audit and keep humans in the loop for irreversible actions.</td></tr></tbody></table>

### O4. How it works inside (so you can explain the machinery)

<table><thead><tr><th>Part</th><th>What to know</th></tr></thead><tbody><tr><td><b>Runtime</b></td><td>One built-in &quot;embedded&quot; runtime runs the agent loop, tool wiring and prompt assembly</td></tr><tr><td><b>Built-in</b><br><b>tools</b></td><td>Core tools: <code>read</code> , <code>exec</code> , <code>edit</code> , <code>write</code> and related system tools. The &quot;Tools&quot; section you write in <code>AGENTS.md</code> is <b>guidance only</b>; it does not decide which tools exist.</td></tr><tr><td><b>Bootstrap</b> <b>files</b></td><td>On the first turn of a session these are injected into Project Context: <code>AGENTS.md</code> , <code>SOUL.md</code> , <code>IDENTITY.md</code> , <code>USER.md</code> , <code>BOOTSTRAP.md</code> (first run only, deleted after use) and <code>MEMORY.md</code> (only if at the workspace root). Blank files are skipped; large files are truncated. Turn off with <code>agents.defaults.skipBootstrap: true</code> .</td></tr><tr><td><b>Sessions</b></td><td>Stored in SQLite under <code>~/.openclaw/agents/&lt;agentId&gt;/agent/</code> ; older JSONL transcripts under <code>.../sessions/</code></td></tr><tr><td><b>Sandbox</b></td><td>With <code>agents.defaults.sandbox</code> enabled, non-main sessions can use per-session workspaces</td></tr><tr><td><b>Setup /</b><br><b>repair</b></td><td><code>openclaw setup</code> creates config and workspace files; <code>openclaw doctor --fix</code> migrates legacy files into SQLite</td></tr></tbody></table>

### Context: what the model actually sees

Context = system prompt (rules, tools, skills list, time, injected workspace files) + conversation history + tool calls, results and attachments, all bounded by the model's window. **Context is not memory**: memory is on disk and reloaded later; context is only what is in the window right now.

<table><thead><tr><th>Command (in chat)</th><th>Shows</th></tr></thead><tbody><tr><td><code>/status</code></td><td>How full the window is, session settings</td></tr><tr><td><code>/context list</code></td><td>Injected content and rough sizes</td></tr><tr><td><code>/context detail</code></td><td>Breakdown by file, tool schema, skill, system prompt</td></tr><tr><td><code>/context map</code></td><td>Treemap image of what fills the session</td></tr><tr><td><code>/usage tokens</code></td><td>Per-reply token usage footer</td></tr><tr><td><code>/compact</code></td><td>Summarise older history to free space</td></tr></tbody></table>

> **Say This:** When the agent behaves oddly I check `/context detail` first. A bloated AGENTS.md or too many skills crowd out the conversation, which is the same lesson as keeping CLAUDE.md short.

### Skills: updated precedence (highest first)

`<workspace>/skills` → `<workspace>/.agents/skills` → `~/.agents/skills` → `~/.openclaw/skills` → bundled skills → `skills.load.extraDirs`. Pages differ slightly; `openclaw skills list` shows what really loaded.

### Multi-agent routing

Run **several isolated agents inside one Gateway**. Each has its own workspace (persona files), state directory `agentDir` (auth, models, config) and session store. A **binding** maps a channel account (a Slack workspace, a WhatsApp number) to one agent, so one Gateway can serve "personal" and "work" assistants separately. **Never reuse an** `agentDir` **across agents**: it causes auth and session collisions (direct warning from the docs). Skills can be limited per agent: `agents.defaults.skills` is the shared baseline; `agents.entries.*.skills` replaces it for one agent. A workspace is a default folder, not a sandbox, for every agent. Commands to add an agent and write bindings were in a truncated part of the docs; read the "Multi-agent routing" and "Agent bindings" pages before demoing this.

### O5. A safe lab setup (do this first)

1. Use **WSL2 or a VM** (or a spare laptop). Keep your real email, banking and work accounts out of it.
2. Keep the Gateway on **loopback**; do not port-forward 18789.
3. Create a **throwaway Telegram bot** and pair only your own account.
4. Give it only the model key it needs. Don't paste other secrets into chat.
5. Install skills you wrote yourself first. Read any third-party skill like code before enabling it.
6. Run `openclaw security audit --deep` after every change in exposure or tools.

### O6. Project: "Interview Mentor" agent (what to demo)

1. SOUL.md: direct mentor persona (O2 step 2).
2. Skill `interview-drill` reading your question bank (O2 step 4).
3. Add a second skill `answer-polish`:

```
# skills\answer-polish\SKILL.md
---
name: answer-polish
description: Tighten a spoken interview answer into a 60-second version with one concrete example.
---
When I paste an answer:
1. Keep my meaning; remove filler.
2. Structure: claim, one concrete example from my own work, result, trade-off.
3. Flag any claim I should be able to defend with evidence.
4. Never add experience I did not mention.
```

4. Pair Telegram so you can drill from your phone.
5. Screenshots: skills list, a drill with a score, `/context detail`, the security audit output.

> **Careful:** The last rule in `answer-polish` matters: an assistant that invents experience for you is a liability in an interview. Use it to clarify what you actually did.

### O7. Five-day OpenClaw plan

<table><thead><tr><th>Day</th><th>Do</th><th>Proof to keep</th></tr></thead><tbody><tr><td>1</td><td>Safe lab, install, onboarding, dashboard chat, <code>openclaw doctor</code></td><td>Gateway status + first chat</td></tr><tr><td>2</td><td>SOUL.md persona; hello-world skill; <code>openclaw skills list</code></td><td>Skills list screenshot</td></tr><tr><td>3</td><td>interview-drill and answer-polish skills</td><td>Sample drill transcript</td></tr><tr><td>4</td><td>Telegram pairing; test prompt injection with a harmless &quot;ignore your rules&quot; note in a file and see how it behaves</td><td>Written observations</td></tr><tr><td>5</td><td>Security audit, <code>/context detail</code> , mock interview on security</td><td>Audit output + notes</td></tr></tbody></table>

### More interview Q&A

<table><thead><tr><th>Question</th><th>Crisp answer</th></tr></thead><tbody><tr><td>Context vs memory?</td><td>Context is what is in the model window this turn; memory is stored on disk and reloaded. I inspect context with <code>/context detail</code> and shrink it with <code>/compact</code> or shorter files.</td></tr><tr><td>How does it support multiple personas?</td><td>Multi-agent routing: isolated agents, each with its own workspace, state and sessions, bound to channel accounts.</td></tr><tr><td>What controls which tools exist?</td><td>Runtime and config, not the AGENTS.md text; AGENTS.md is guidance. Restrict risky tools with config, allowlists and sandboxing.</td></tr></tbody></table>

Sources: docs.openclaw.ai (several pages truncated when fetched; verify on your version). Checked Oct 2026. Not run by me.
