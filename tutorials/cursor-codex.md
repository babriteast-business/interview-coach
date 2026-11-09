---
title: Cursor & Codex
group: Agents & tools
order: 10
blurb: Setup, rules, safety, examples and interview Q&A
tagline: setup · rules · safety · examples · interview Q&A
about: Official docs checked 24 Oct 2026 · Windows PowerShell commands · every feature marked verified or (verify)
---

## The 30-second picture

> **Say This:** Cursor is an AI-first code editor (a VS Code fork) with an Agent, a CLI and cloud agents. Codex is OpenAI's coding agent that runs in a terminal CLI, a desktop app, an IDE extension and the cloud. Both read project instructions, edit files, run commands, and both are controlled by the same two ideas: what the agent may touch (sandbox) and when it must ask me (approvals).

<table><thead><tr><th></th><th>Cursor</th><th>Codex</th></tr></thead><tbody><tr><td><b>Main home</b></td><td>Desktop editor + <code>agent</code> CLI</td><td>Terminal CLI ( <code>codex</code> ), desktop app, IDE extension, cloud</td></tr><tr><td><b>Project</b><br><b>instructions</b></td><td><code>.cursor/rules/*.mdc</code> and <code>AGENTS.md</code></td><td><code>AGENTS.md</code> (and <code>AGENTS.override.md</code> )</td></tr><tr><td><b>Safety knobs</b></td><td>Run modes + sandbox +<br><code>permissions.json</code></td><td><code>sandbox_mode</code> + <code>approval_policy</code> in <code>config.toml</code></td></tr><tr><td><b>Tools plug-in</b></td><td><code>.cursor/mcp.json</code></td><td><code>[mcp_servers.*]</code> in <code>config.toml</code> , <code>codex mcp</code></td></tr><tr><td><b>Automation</b></td><td><code>agent -p &quot;...&quot;</code> , hooks, cloud agents</td><td><code>codex exec &quot;...&quot;</code> , <code>codex review</code> , <code>codex cloud</code></td></tr><tr><td><b>Sign-in</b></td><td>Cursor account</td><td>ChatGPT account (Plus/Pro/Business/Edu/Enterprise) or API key</td></tr><tr><td><b>Open source?</b></td><td>No (product)</td><td>CLI is Apache-2.0 on GitHub (openai/codex)</td></tr></tbody></table>

> **Tip:** The two tools are not rivals in an interview: say "I pick by surface. Cursor when I want to live in an editor with inline review; Codex when I want a terminal/CI agent with explicit sandbox and approval settings. The discipline is identical: instructions file, small tasks, review the diff, tests."

### Lab folder used in every example

```powershell
mkdir $HOME\agent-lab
cd $HOME\agent-lab
git init
git config user.name "Babrit"
git config user.email "iambabrit@gmail.com"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pytest
```

Make a tiny project the agents can improve:

```python
@'
def add(a, b):
    return a + b
def divide(a, b):
    return a / b
'@ | Set-Content calc.py
git add .; git commit -m "start"
```

> **Careful:** Always work in a Git repo. It is your undo button for both tools. Cursor checkpoints are local and separate from Git; Codex docs recommend Git checkpoints before and after each task.

## Cursor

### A1. Install on Windows

1. Download the Windows installer from **cursor.com**, run it, sign in with your Cursor account. (Desktop app; I did not run it, so follow the installer prompts.)
2. Open the folder: `cursor $HOME\agent-lab` if the shell command was added, else File → Open Folder.
3. Open the Agent panel with **Ctrl+I**.

### A2. Install the Cursor CLI (verified)

```
irm 'https://cursor.com/install?win32=true' | iex
agent --version
agent                      # interactive session in the current folder
agent update               # manual update (it also auto-updates)
```

macOS/Linux/WSL uses `curl https://cursor.com/install -fsS | bash`, then add `~/.local/bin` to PATH. First run asks you to log in. The install page did not document login steps, so follow the on-screen prompt.

### A3. The three modes

<table><thead><tr><th>Mode</th><th>What it does</th><th>Open it</th></tr></thead><tbody><tr><td><b>Agent</b></td><td>Reads, edits, runs shell, uses browser/MCP</td><td>default; CLI <code>agent &quot;prompt&quot;</code></td></tr><tr><td><b>Plan</b></td><td>Researches and writes a plan to approve before any edit</td><td>Shift+Tab, <code>/plan</code> , <code>--mode=plan</code></td></tr><tr><td><b>Ask</b></td><td>Read-only Q&amp;A about the code</td><td><code>/ask</code> , <code>--mode=ask</code></td></tr></tbody></table>

Useful keys: **Enter** queues a message, **Ctrl+Enter** sends now, `/side` or `/btw` opens a side chat, `/goal` sets a long-running objective, **Ctrl+K** searches past chats. Checkpoints let you roll the agent's edits back.

### A4. Example 1 - Plan then Agent

```bash
agent --mode=plan "Add input validation to calc.py: divide must raise ValueError on zero. Add pytest
tests."
# read the plan, then run it:
agent "Implement the plan. Then run pytest and show the result."
git diff
```

> **Say This:** I plan first on anything touching more than one file. The plan is cheap to correct; a wrong edit is not.

### A5. Rules - the most asked topic

<table><thead><tr><th>Type</th><th>Where</th><th>Notes</th></tr></thead><tbody><tr><td>Project Rules</td><td><code>.cursor/rules/*.mdc</code></td><td>version-controlled; plain <code>.md</code> in that folder is ignored</td></tr><tr><td>User Rules</td><td>Settings → Customize → Rules</td><td>apply to all my projects</td></tr><tr><td>Team Rules</td><td>dashboard</td><td>Team/Enterprise plans</td></tr><tr><td><code>AGENTS.md</code></td><td>root or subfolders</td><td>plain markdown, no frontmatter; nested ones combine, more specific wins</td></tr></tbody></table>

Precedence: Team → Project → User. All applicable rules are merged; earlier sources win conflicts.

**Frontmatter decides when a rule loads:**

<table><thead><tr><th>Frontmatter</th><th>Behaviour</th></tr></thead><tbody><tr><td><code>alwaysApply: true</code></td><td>in every chat</td></tr><tr><td><code>globs: &quot;**/*.py&quot;</code></td><td>auto-attached when a matching file is in context</td></tr><tr><td><code>description</code> only</td><td>Agent decides if relevant (&quot;Apply Intelligently&quot;)</td></tr><tr><td>none of these</td><td>only when I @-mention the rule</td></tr></tbody></table>

### A6. Example 2 - write three rules

```
mkdir .cursor\rules
@'
---
description: Python style for this repo
globs: "**/*.py"
alwaysApply: false
---
- Use type hints on every function.
- Raise ValueError for bad input, never return None silently.
- Tests live in tests/ and use pytest.
'@ | Set-Content .cursor\rules\python.mdc
@'
---
description: Always-on safety rules
alwaysApply: true
---
- Never edit files outside this repo.
- Run pytest before saying a task is done.
'@ | Set-Content .cursor\rules\always.mdc
@'
# Project notes
Run tests: pytest -q
Entry file: calc.py
'@ | Set-Content AGENTS.md
```

Test it: `agent --mode=ask "What rules apply to calc.py?"`

> **Tip:** Official guidance: keep rules under 500 lines, point to files instead of pasting them, add a rule only when the agent repeats the same mistake, and use a linter instead of copying a style guide.

### A7. Run modes, sandbox, permissions (interview gold)

Settings → Agents → Approvals & Execution:

<table><thead><tr><th>Mode</th><th>Behaviour</th></tr></thead><tbody><tr><td><b>Auto-review</b><br>(recommended default)</td><td>allowlisted calls run at once; other shell commands run in the sandbox when possible; those that cannot go to a classifier. <b>Not a security boundary.</b></td></tr><tr><td><b>Allowlist</b></td><td>only allowlisted commands run without asking</td></tr><tr><td><b>Run Everything</b></td><td>no prompts, no sandbox. Dangerous.</td></tr></tbody></table>

**Sandbox:** workspace is read/write; `.git/config`, `.git/hooks`, `.vscode` and `.cursorignore` are protected; network blocked by default (`sandbox.json` network modes: "sandbox.json Only", "sandbox.json + Defaults" which is the default, "Allow All"). macOS uses Seatbelt, Linux uses Landlock or Bubblewrap. The docs I read describe those two; check the sandbox page for what Windows uses (verify). **permissions.json** in `~/.cursor/` or `<project>/.cursor/` holds `allow_instructions` and `block_instructions` (plain-language rules for the classifier). **Cloud Agents** run on dedicated machines and never ask approval. A leading `&` in the CLI sends a task to one.

### A8. Example 3 - headless CLI (scripts and CI)

```
agent -p "Summarise calc.py in 3 bullets" --output-format text
agent ls                         # list sessions
agent --continue                 # continue the last one
agent -p "Review git diff for bugs" --model auto --sandbox enabled
```

Flags `-p`, `--model`, `--output-format`, `--continue`, `--sandbox` are from the CLI docs. Exact values for `--model` and `--sandbox` vary, so check `agent --help` (verify).

### A9. MCP - connect tools (verified)

```
mkdir .cursor
@'
{
  "mcpServers": {
    "local-tools": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/tools/server.py"],
      "env": { "API_KEY": "${env:API_KEY}" }
    },
    "remote-api": {
      "url": "https://api.example.com/mcp",
      "headers": { "Authorization": "Bearer ${env:MY_TOKEN}" }
    }
  }
}
'@ | Set-Content .cursor\mcp.json
```

Project file `.cursor/mcp.json`; global file `~/.cursor/mcp.json`. Use `${env:NAME}` so secrets never sit in the JSON. `envFile` works for stdio only. By default Cursor asks before each MCP tool call. Admins can set an MCP Allowlist on Team/Enterprise.

### A10. Hooks (verified)

Scripts that run at stages of the agent loop: formatters after edits, secret scans, blocking risky commands. File: `.cursor/hooks.json` (project) or `~/.cursor/hooks.json` (user).

```powershell
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [{ "command": ".cursor/hooks/block-git.ps1" }],
    "afterFileEdit": [{ "command": ".cursor/hooks/audit.ps1" }]
  }
}
```

Input: JSON on stdin (on Windows read it from `$input`). Output: JSON on stdout, e.g. `permission` = allow / deny / ask. Exit code 0 = use output; **2 = block**; other codes = hook failed and action proceeds unless `failClosed: true`.

I did not verify the exact `.ps1` invocation form on Windows, so test with a harmless script first (verify).

### A11. Cursor pros and cons

```diagram flow
plain: Best-in-class editor UX: inline diffs, checkpoints Plan mode and Ask mode reduce risky edits Rules + AGENTS.md give reusable context CLI, hooks and cloud agents cover automation Choose among several model providers | Pros
plain: Closed product tied to its subscription Auto-review is "not a security boundary" Rules can bloat context if overused Pricing and limits change; I did not verify current plans (verify) Editor lock-in vs plain terminal tools | Cons
```

## OpenAI Codex

### B1. Install on Windows (verified)

```powershell
# Option 1: official PowerShell installer
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
# Option 2: npm (needs Node)
npm install -g @openai/codex
codex --version
codex doctor        # diagnostic report: install, config, auth
```

Windows 11 is recommended; Windows 10 1809+ is best effort. `winget` should be available. Update: re-run the installer, or `codex update` if your release supports it. macOS/Linux: `curl -fsSL https://chatgpt.com/codex/install.sh | sh`; Homebrew: `brew install --cask codex`.

### B2. Sign in and first run

```bash
cd $HOME\agent-lab
codex                # choose "Sign in with ChatGPT"
codex login          # other methods: device auth, API key
codex logout
```

ChatGPT sign-in works with Plus, Pro, Business, Edu and Enterprise plans. An API key also works (usage billed to the API account).

### B3. Sandbox and approvals - the heart of Codex

<table><thead><tr><th>Setting</th><th>Values</th><th>Meaning</th></tr></thead><tbody><tr><td><code>sandbox_mode</code> / <code>--</code> <code>sandbox</code></td><td><code>read-only</code> , <code>workspace-write</code> , <code>danger-</code> <code>full-access</code></td><td>what files/commands the agent can touch</td></tr><tr><td><code>approval_policy</code> / <code>-a</code></td><td><code>on-request</code> , <code>never</code> , <code>granular</code></td><td>when it must ask me. <code>untrusted</code> is retired</td></tr></tbody></table>

**Defaults:** network off. In a version-controlled folder you get Auto (`workspace-write` + `on-request`); in a non-version-controlled folder, `read-only`. That is another reason to `git init` first. Protected paths under workspace-write: `.git`, `.agents`, `.codex`, `.aws`. In the session, type `/permissions` to see approvals, sandbox and writable roots. `--dangerously-bypass-approvals-and-sandbox` (`--yolo`) exists but the docs do not recommend it.

```bash
# safe read-only review (good for CI)
codex --sandbox read-only --ask-for-approval never "Review calc.py for bugs"
# normal day-to-day edit
codex --sandbox workspace-write --ask-for-approval on-request "Add tests for divide"
```

### B4. Windows sandbox

The native PowerShell sandbox is recommended; WSL is optional. Implementations are `mxc` (recommended on newer Windows 11 builds, `[features] prefer_mxc = true`), `elevated` and `unelevated` (`[windows] sandbox = "elevated"`). Diagnostics log: `CODEX_HOME/.sandbox/sandbox.log`.

### B5. config.toml - minimal file

Location: `~/.codex/config.toml` (on Windows `$HOME\.codex\config.toml`).

```powershell
New-Item -ItemType Directory -Force $HOME\.codex | Out-Null
@'
sandbox_mode = "workspace-write"
approval_policy = "on-request"
web_search = "cached"
[sandbox_workspace_write]
network_access = false
'@ | Set-Content $HOME\.codex\config.toml
```

> **Careful:** The keys `sandbox_mode`, `approval_policy`, `web_search` and `network_access` come from the approvals and security docs. The config basics page was not reachable for me, so check any other key against the Configuration Reference before relying on it (verify). Override per run with `codex -c key=value`.

### B6. AGENTS.md in Codex (verified)

1. **Global:** in `~/.codex`, first non-empty of `AGENTS.override.md` or `AGENTS.md`.
2. **Project:** from the repo root down to the current folder, one file per directory (`AGENTS.override.md`, then `AGENTS.md`, then fallback names).
3. **Merge:** root first, nearer files later so they override.
4. Combined size cap `project_doc_max_bytes` = 32 KiB by default.

```bash
@'
# Working agreements
- Run `pytest -q` before finishing.
- Keep functions small; add type hints.
- Never touch files outside this repo.
'@ | Set-Content AGENTS.md
codex --ask-for-approval never "Summarize the current instructions."
```

That last command is the official way to prove the file loaded. A nested `AGENTS.override.md` in a subfolder replaces the root file there.

> **Tip:** One `AGENTS.md` works for both Cursor and Codex. That is a strong interview point: write instructions once, reuse everywhere.

### B7. Example 1 - fix and test

```bash
codex "divide in calc.py crashes on zero. Raise ValueError and add pytest tests in
tests/test_calc.py. Run them."
git diff
pytest -q
```

### B8. Example 2 - non-interactive and review

```bash
codex exec "List every function in calc.py with a one-line summary"
codex review                       # non-interactive review (uncommitted, branch diff or commit)
codex resume                       # continue a past session
codex --search "What is new in pytest 8?"   # live web search for this run
```

`codex exec` is the scripting/CI entry point (stdout or JSONL). In the TUI the slash commands named in the docs include `/init`, `/plan`, `/review`, `/status`, `/mcp`, `/goal` and `/permissions`. The page did not describe each, so use `/init` and others only after reading their help in the app (verify).

### B9. Example 3 - add an MCP server (verified)

```bash
@'
[mcp_servers.my-tools]
command = "npx"
args = ["-y", "my-mcp-package"]
env_vars = ["MY_API_TOKEN"]
enabled_tools = ["search", "read"]
default_tools_approval_mode = "prompt"
'@ | Add-Content $HOME\.codex\config.toml
# HTTP server with OAuth
codex mcp add example --url https://mcp.example.com
codex mcp login example
```

`my-mcp-package` is a placeholder; put a real package or script. Remote servers use `url`, `bearer_token_env_var`, `http_headers`. Stdio uses `command`, `args`, `env`, `env_vars`, `cwd`. Approval modes for tools: `auto`, `prompt`, `writes`, `approve`. Allow list `enabled_tools`, deny list `disabled_tools`. Check connected servers with `/mcp`. Project-level `.codex/config.toml` works only for trusted projects.

### B10. Other CLI commands worth naming

<table><thead><tr><th>Command</th><th>Use</th></tr></thead><tbody><tr><td><code>codex cloud</code></td><td>submit/browse cloud tasks (experimental)</td></tr><tr><td><code>codex apply</code></td><td>apply a cloud task&#x27;s diff locally</td></tr><tr><td><code>codex fork</code></td><td>branch a past session into a new chat</td></tr><tr><td><code>codex execpolicy</code></td><td>test whether a command would be allowed (experimental)</td></tr><tr><td><code>codex sandbox</code></td><td>run a command inside Codex&#x27;s sandbox</td></tr><tr><td><code>codex completion</code></td><td>shell completion incl. PowerShell</td></tr><tr><td><code>codex features</code></td><td>list/toggle feature flags</td></tr></tbody></table>

### B11. Codex pros and cons

```diagram flow
plain: Open-source CLI (Apache-2.0) Explicit, scriptable sandbox + approval model Native Windows sandbox, no WSL needed Same config shared by CLI, app and IDE extension Included with ChatGPT plans; cloud tasks and review built in | Pros
plain: Terminal-first; less visual than an editor Docs moved (learn.chatgpt.com), some pages hard to find Many options; wrong sandbox/approval combo is easy Tied to OpenAI models and ChatGPT limits Plan limits and models change; I did not verify current ones (verify) | Cons
```

## Compare with the tools from earlier notes

<table><thead><tr><th>Tool</th><th>Best for</th><th>Control model</th><th>Weakness</th></tr></thead><tbody><tr><td><b>Cursor</b></td><td>editing code with inline review</td><td>run modes, sandbox, rules, hooks</td><td>closed, subscription</td></tr><tr><td><b>Codex</b></td><td>terminal/CI agent, review, cloud tasks</td><td>sandbox_mode +<br>approval_policy</td><td>terminal-first</td></tr><tr><td><b>Claude</b><br><b>Code</b></td><td>agentic coding in terminal with skills, hooks, subagents</td><td>permissions, CLAUDE.md</td><td>needs Claude<br>account/API</td></tr><tr><td><b>Antigravity</b></td><td>agent-first IDE</td><td>its own agent manager</td><td>newer, fewer mature habits</td></tr><tr><td><b>n8n</b></td><td>no-code workflow automation</td><td>nodes, credentials</td><td>not a coding agent</td></tr><tr><td><b>CrewAI</b></td><td>multi-agent Python apps</td><td>Crew / Flow</td><td>you write and host it</td></tr><tr><td><b>OpenClaw</b></td><td>personal always-on agent</td><td>channels, skills</td><td>high risk; lab only</td></tr></tbody></table>

### Concept map - same four ideas everywhere

<table><thead><tr><th>Idea</th><th>Cursor</th><th>Codex</th><th>Claude Code</th></tr></thead><tbody><tr><td>Instructions</td><td><code>.cursor/rules</code> , AGENTS.md</td><td>AGENTS.md</td><td>CLAUDE.md</td></tr><tr><td>Permissions</td><td>run modes, permissions.json</td><td>sandbox_mode, approval_policy</td><td>permission rules / modes</td></tr><tr><td>Tools (MCP)</td><td>.cursor/mcp.json</td><td>config.toml / codex mcp</td><td>.mcp.json / claude mcp</td></tr><tr><td>Headless</td><td>agent -p</td><td>codex exec</td><td>claude -p</td></tr></tbody></table>

> **Say This:** Whatever the tool, my workflow is: Git branch, instructions file, plan for big tasks, least-privilege permissions, run tests, review the diff, then merge. The tool changes; the discipline does not.

### C2. Five-day practice plan

<table><thead><tr><th>Day</th><th>Do</th></tr></thead><tbody><tr><td>1</td><td>Lab folder; install Cursor + CLI; Plan-then-Agent on calc.py (A4)</td></tr><tr><td>2</td><td>Write the three rules and AGENTS.md; prove they load (A6)</td></tr><tr><td>3</td><td>Install Codex; sign in; read-only review then workspace-write fix (B3, B7)</td></tr><tr><td>4</td><td>Add one MCP server to each tool; try a hook in Cursor (A9, A10, B9)</td></tr><tr><td>5</td><td><code>agent -p</code> and <code>codex exec</code> in a script; speak the Q&amp;A aloud</td></tr></tbody></table>

## Interview Q&A

**Q1. Cursor vs Codex, when do you pick which?** Cursor when I want editor-native review (inline diffs, checkpoints). Codex when I want a terminal or CI agent with explicit sandbox and approval flags. Both consume the same AGENTS.md.

**Q2. How do you keep an agent from doing damage?** Git repo first. Least privilege: Codex `read-only` or `workspace-write` with network off; Cursor Auto-review or Allowlist, never Run Everything. Block lists via permissions.json or hooks. Review every diff and run tests.

**Q3. Explain Cursor rule types.** Always (`alwaysApply`), Auto-attached (`globs`), Agent-requested (`description`), Manual (@-mention). Stored as `.mdc` in `.cursor/rules`. Order: Team, Project, User.

**Q4. Sandbox vs approvals?** Sandbox limits what the agent can do technically. Approvals decide when it must ask. Codex has them as two settings; Cursor combines them in run modes. Neither is a substitute for review.

**Q5. What is AGENTS.md and how is it resolved?** A plain markdown file of project instructions shared across tools. Codex merges global then root-to-current-folder files, nearer ones override, 32 KiB cap. Cursor supports it in root and subfolders with the most specific winning.

**Q6. What is MCP and how do you add it?** Model Context Protocol, a standard way to plug tools and data into agents. Cursor: `.cursor/mcp.json`. Codex: `[mcp_servers.name]` in `config.toml` or `codex mcp add`. Secrets via environment variables, tool calls need approval.

**Q7. How do you use these in CI?** `codex exec` or `codex review` with `--sandbox read-only --ask-for-approval never`; Cursor `agent -p` for headless prompts. Read-only plus no approvals means it can analyse but cannot change anything.

**Q8. What are Cursor hooks for?** Scripts around the agent loop: format after edits, scan secrets, deny risky shell commands. Exit code 2 blocks; `failClosed` makes failures block.

**Q9. Prompt injection risk?** Files, web pages or MCP outputs can carry instructions. Keep network off by default, limit MCP tools with allow lists, require approval for writes, and never feed untrusted content to a full-access agent.

<table><thead><tr><th>Verified from official docs on 24 Oct 2026</th><th>Not verified / do yourself</th></tr></thead><tbody><tr><td>Cursor rules, modes, run modes, sandbox, CLI install and flags, MCP, hooks<br>Codex install commands, sign-in, sandbox and approval values, defaults, Windows sandbox, AGENTS.md loading, MCP config, CLI command list</td><td>I ran none of these on Windows.<br>Cursor: desktop installer steps, login flow, pricing/plans, CLI flag values, Windows sandbox details, hook script form on PowerShell.<br>Codex: full config.toml key list, what each slash command does, models and plan limits.<br>Run <code>agent --help</code> , <code>codex --help</code> and the Configuration Reference to confirm before quoting a detail.</td></tr></tbody></table>

**Q10. How do you know the agent's work is right?**

Small tasks, tests it must run, my own read of the diff, and a second pass with `codex review` or a Plan-mode review. I treat it like a fast junior who needs checking.

**Q11. What do you do when the agent keeps repeating a mistake?**

Add one short rule or AGENTS.md line that names the mistake, point it to the right file, and rerun. Not a giant style guide; use a linter for style.

**Q12. Why Git checkpoints?**

Cursor checkpoints are local and separate from Git; Codex docs recommend commits before and after tasks. Git gives reviewable, revertible history.

Honesty page - what is verified and what is not

Sources: cursor.com/docs (agent, rules, run modes, CLI, MCP, hooks); learn.chatgpt.com/docs (Codex CLI, agent approvals & security, Windows sandbox, AGENTS.md, MCP, developer commands); github.com/openai/codex.
