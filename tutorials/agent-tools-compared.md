---
title: CrewAI & OpenClaw, and six tools compared
group: Agents & tools
order: 13
blurb: Claude Code, Claude API, n8n, Antigravity, CrewAI and OpenClaw side by side
tagline: setup · examples · and how all 6 tools compare
about: Docs checked Oct 2026, CrewAI code smoke-tested · Includes: master comparison of Claude Code, Claude API, n8n, Antigravity, CrewAI, OpenClaw + mentor review of all today's docs
---

## CrewAI

### C0. What it is (say this in 20 seconds)

> **Say This:** CrewAI is a Python framework for multi-agent systems. I define agents with a role, goal and backstory, give them tasks and tools, and a Crew runs them in a process. For deterministic control I wrap crews in Flows, which add state, routing and ordinary Python.

<table><thead><tr><th>Concept</th><th>What it is (key attributes)</th></tr></thead><tbody><tr><td><b>Agent</b></td><td><code>role</code> , <code>goal</code> , <code>backstory</code> , <code>llm</code> , <code>tools</code> , <code>max_iter</code> (default 20), <code>max_rpm</code> , <code>allow_delegation</code> (default False), <code>reasoning</code> (plan before acting)</td></tr><tr><td><b>Task</b></td><td><code>description</code> , <code>expected_output</code> , <code>agent</code> , <code>context</code> (earlier tasks feeding this one), <code>output_pydantic</code> , <code>output_file</code> , <code>guardrail</code> , <code>async_execution</code> , <code>human_input</code></td></tr><tr><td><b>Crew</b></td><td>agents + tasks + <code>process</code> (sequential default, or hierarchical with a manager: <code>manager_llm</code> required), <code>memory</code> , <code>planning</code> , <code>max_rpm</code> , <code>verbose</code></td></tr><tr><td><b>Run</b></td><td><code>kickoff(inputs={...})</code> , <code>kickoff_for_each</code> , async variants. Returns <code>CrewOutput</code> : <code>raw</code> , <code>pydantic</code> , <code>json_dict</code> , <code>tasks_output</code> , <code>token_usage</code></td></tr><tr><td><b>Tools</b></td><td>Instances in <code>tools=[...]</code> (e.g. <code>SerperDevTool</code> from <code>crewai_tools</code> ) or LangChain tools</td></tr><tr><td><b>Flow</b></td><td>Python class with <code>@start</code> , <code>@listen</code> , <code>@router</code> , Pydantic state in <code>self.state</code> ; can call crews</td></tr><tr><td><b>Memory /</b><br><b>Knowledge</b></td><td>Short-term, long-term, entity memory; <code>knowledge/</code> folder for reference files</td></tr></tbody></table>

> **Tip:** Crew = agents collaborating on judgment-heavy work. Flow = the deterministic skeleton around it. Strong answer: "I use a Flow for control and put a Crew only where reasoning is needed."

### C1. Setup on Windows

Needs **Python 3.10 to 3.13** (the docs say `>=3.10 and <3.14`). Check with `python --version`.

```powershell
# 1. install uv (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# open a NEW PowerShell, then:
uv tool install crewai
uv tool list                  # confirm crewai is listed
crewai --version
```

PATH warning? run `uv tool update-shell`, then reopen PowerShell. Build error mentioning `chroma-hnswlib` / `C1083`? Install **Visual Studio Build Tools** with the "Desktop development with C++" workload. Upgrade the CLI: `uv tool install crewai --upgrade` (does not upgrade the project's own environment).

> **Careful:** The newest docs describe a JSON-first project layout (`crew.jsonc`, `agents/*.jsonc`). I teach the **classic YAML + Python** layout (`--classic`) because it is the one you will meet in most tutorials and interviews. I scaffolded it in a sandbox, so the file listings below are real.

### C2. Scaffold a crew and read every file

```bash
crewai create crew --classic jobscout
# It asks you to pick an LLM provider (a number) and a model. Pick any; we edit .env next.
cd jobscout
dir
```

What gets generated (verified):

```
jobscout/
  .env                        MODEL=... and your API key go here
  pyproject.toml              project + script entry points (run_crew, train, replay, test)
  AGENTS.md CLAUDE.md GEMINI.md CURSOR.md    rule files so coding agents understand the project
  knowledge/user_preference.txt              sample knowledge file
  src/jobscout/
    config/agents.yaml        who the agents are
    config/tasks.yaml         what each does
    crew.py                   wires agents + tasks into a Crew
    main.py                   run(), train(), replay(), test()
    tools/custom_tool.py      template for your own tool
```

> **Say This:** The scaffold even writes AGENTS.md, CLAUDE.md and GEMINI.md, so Claude Code and Antigravity pick up project rules automatically. That's the same context-file idea from my other playbooks.

### agents.yaml (generated, trimmed)

```yaml
researcher:
  role: >
    {topic} Senior Data Researcher
  goal: >
    Uncover cutting-edge developments in {topic}
  backstory: >
    You're a seasoned researcher ...
reporting_analyst:
  role: >
    {topic} Reporting Analyst
  goal: >
    Create detailed reports based on {topic} data analysis and research findings
  backstory: >
    You're a meticulous analyst ...
```

### tasks.yaml (generated, trimmed)

```yaml
research_task:
  description: >
    Conduct a thorough research about {topic}. The current year is {current_year}.
  expected_output: >
    A list with 10 bullet points of the most relevant information about {topic}
  agent: researcher
reporting_task:
  description: >
    Review the context you got and expand each topic into a full section for a report.
  expected_output: >
    A full report in markdown without ``` fences
  agent: reporting_analyst
```

`{topic}` and `{current_year}` are filled from `inputs` in `main.py`. A task whose output feeds the next one is passed automatically in a sequential process; use `context:` to feed specific earlier tasks.

### crew.py (generated, trimmed) - the part interviewers ask about

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
@CrewBase
class Jobscout():
    @agent
    def researcher(self) -> Agent:
        return Agent(config=self.agents_config['researcher'], verbose=True)
    @agent
    def reporting_analyst(self) -> Agent:
        return Agent(config=self.agents_config['reporting_analyst'], verbose=True)
    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config['research_task'])
    @task
    def reporting_task(self) -> Task:
        return Task(config=self.tasks_config['reporting_task'], output_file='report.md')
    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks,
                    process=Process.sequential, verbose=True)
```

**How it works:** `@CrewBase` loads the YAML; `@agent` and `@task` methods register themselves in order; `self.agents` / `self.tasks` are the collected lists. `main.py` calls `Jobscout().crew().kickoff(inputs=inputs)`.

### C3. Point it at a free NVIDIA model and run

1. Create a key at `build.nvidia.com` (free tier, check limits and terms there).
2. Edit `.env` (replace the generated `MODEL` line):

```
MODEL=nvidia_nim/meta/llama-3.1-70b-instruct
NVIDIA_API_KEY=nvapi-your-key
```

3. Install the LiteLLM extra. **This is required**: in my sandbox test, a `nvidia_nim/` model failed with "LiteLLM fallback package is not installed" until I added it.

```bash
uv add "crewai[litellm]"
crewai install
crewai run
```

Always use **provider-prefixed model names** (`openai/gpt-4o`, `anthropic/...`, `ollama/llama3`, `nvidia_nim/...`). A bare model name is treated as wrong. Model IDs change; check the catalog for the exact name. If one fails, try another from build.nvidia.com. Local alternative: install Ollama, `ollama pull llama3`, then `LLM(model="ollama/llama3", base_url="http://localhost:11434")`. Anthropic needs `max_tokens` set and `uv add "crewai[anthropic]"`. Output lands in `report.md`. Run with `verbose=True` to watch agents think, delegate and call tools.

> **Tip:** Change the input topic in `main.py` to "remote GenAI job market in India" and read `report.md`. Note which claims you must verify yourself: agents can sound sure and be wrong.

### Example 1 - single-file crew, no CLI (easy to explain live)

```python
# crew_demo.py   (pip install crewai litellm)
import os
from crewai import Agent, Task, Crew, Process, LLM
llm = LLM(model="nvidia_nim/meta/llama-3.1-70b-instruct")   # needs NVIDIA_API_KEY in env
researcher = Agent(role="Researcher", goal="Find key facts about {topic}",
                   backstory="Careful analyst who never invents facts.",
                   llm=llm, max_iter=5, allow_delegation=False)
writer = Agent(role="Writer", goal="Write a clear 5-bullet brief",
               backstory="Plain-English technical writer.", llm=llm)
t1 = Task(description="Research {topic}.", expected_output="8 raw bullets", agent=researcher)
t2 = Task(description="Turn the research into a 5-bullet brief.",
          expected_output="5 bullets", agent=writer, context=[t1], output_file="brief.md")
crew = Crew(agents=[researcher, writer], tasks=[t1, t2],
            process=Process.sequential, verbose=True)
print(crew.kickoff(inputs={"topic": "agentic AI evaluation"}))
```

```powershell
# PowerShell
$env:NVIDIA_API_KEY = "nvapi-your-key"
python crew_demo.py
```

### Example 2 - structured output + guardrail (shows production thinking)

```python
from pydantic import BaseModel
class Brief(BaseModel):
    title: str
    points: list[str]
def check(result):                       # guardrail: returns (ok, value_or_error)
    return (True, result) if result.raw else (False, "Empty output, try again")
t2 = Task(description="Summarise as JSON with title and points.",
          expected_output="JSON", agent=writer, context=[t1],
          output_pydantic=Brief, guardrail=check)
# after kickoff: out = crew.kickoff(...); out.pydantic.title, out.token_usage
```

I constructed this task (with `context`, `output_pydantic`, `guardrail`, `output_file`) in a sandbox and it validated. The guardrail contract (`(bool, value)` tuple) is from general knowledge; confirm against the docs for your installed version.

### Example 3 - hierarchical process (a manager delegates)

```
crew = Crew(agents=[researcher, writer], tasks=[t1, t2],
            process=Process.hierarchical, manager_llm=llm, verbose=True)
```

A manager agent plans, delegates and validates. It costs more tokens and is less predictable than sequential. Use it only when task routing truly varies.

### Example 4 - Flow with a router (tested; works)

```python
# flow_demo.py
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start, router
class S(BaseModel):
    n: int = 0
class Demo(Flow[S]):
    @start()
    def begin(self):
        self.state.n = 5
    @router(begin)
    def decide(self):
        return "big" if self.state.n > 3 else "small"
    @listen("big")
    def handle_big(self):
        print("big path", self.state.n)
    @listen("small")
    def handle_small(self):
        print("small path")
Demo().kickoff()
```

> **Careful:** Gotcha I hit: naming the handler the same as the route label (`def big` listening to `"big"`) fails with an "infinite loop" validation error. Name handlers differently from route strings. Real use: `@start` reads input, `@router` classifies it, `@listen("complaint")` calls a support Crew, `@listen("sales")` calls a sales Crew. Scaffold with `crewai create flow <name>`; add a crew with `crewai flow add-crew <name>`; visualise with `crewai flow plot`.

### CrewAI: pros, cons, interview answers

<table><thead><tr><th>Pros</th><th>Cons / risks</th></tr></thead><tbody><tr><td>Fast to prototype role-based multi-agent work; readable YAML; CLI scaffolding; many tools and LLM providers; Flows give deterministic control, state and routing</td><td>Agent loops burn tokens and are non-deterministic; hierarchical manager can mis-delegate; APIs and project layout change quickly (classic vs JSON-first); debugging needs verbose logs and tracing; needs guardrails and evals</td></tr></tbody></table>

<table><thead><tr><th>Question</th><th>Crisp answer</th></tr></thead><tbody><tr><td>Sequential vs<br>hierarchical?</td><td>Sequential runs tasks in order, passing outputs. Hierarchical adds a manager ( <code>manager_llm</code> required) that delegates and validates; more flexible, more cost and variance.</td></tr><tr><td>Crew vs Flow?</td><td>Crew = collaborating agents for judgment work. Flow = event-driven Python with state and routing; it can call crews. Use Flows for control, crews for reasoning.</td></tr><tr><td>How do you stop<br>runaway agents?</td><td><code>max_iter</code> , <code>max_rpm</code> , narrow tools, <code>allow_delegation=False</code> , guardrails on tasks, structured output, tracing.</td></tr><tr><td>How do tasks share data?</td><td>Sequential passes output along; <code>context=[...]</code> selects specific earlier tasks; Flow state shares data across steps.</td></tr><tr><td>Why CrewAI vs n8n?</td><td>CrewAI is code-first agent reasoning inside a Python service. n8n is visual orchestration of triggers, apps and APIs. I often call a CrewAI service from n8n.</td></tr></tbody></table>

## OpenClaw

> **Careful:** OpenClaw is an always-on personal assistant that can use tools on your computer and talk to you through chat apps. That makes it powerful and risky. Practise on a spare machine, VM or WSL with **no personal accounts** connected at first. The docs themselves say prompt injection is a risk even if you are the only sender.

### D0. What it is (say this in 20 seconds)

> **Say This:** OpenClaw is a self-hosted personal AI assistant. A Gateway process connects chat channels (Telegram, WhatsApp, Slack, Discord and more) to an agent that has tools and skills, with its persona and memory kept as plain files in a workspace.

<table><thead><tr><th>Piece</th><th>Meaning</th></tr></thead><tbody><tr><td><b>Gateway</b></td><td>The long-running process; listens on port <b>18789</b>; runs as a background service once installed</td></tr><tr><td><b>Control UI /</b><br><b>dashboard</b></td><td>Browser UI opened with <code>openclaw dashboard</code> ; chat, settings, files</td></tr><tr><td><b>Channels</b></td><td>Telegram (fastest, only needs a bot token), WhatsApp, Slack, Discord, Teams, Signal and others</td></tr><tr><td><b>Workspace</b></td><td>Agent&#x27;s home: <code>~/.openclaw/workspace</code> . Separate from <code>~/.openclaw/</code> (config, credentials, sessions)</td></tr><tr><td><b>AGENTS.md</b></td><td>Operating instructions and memory-use guidance, loaded each session</td></tr><tr><td><b>SOUL.md</b></td><td>Persona, tone, boundaries, loaded each session</td></tr><tr><td><b>USER.md</b></td><td>Your preferences and active projects (4,000-character budget)</td></tr><tr><td><b>Skills</b></td><td>Folders with <code>SKILL.md</code> ; teach the agent how and when to use tools; ClawHub is the public registry</td></tr><tr><td><b>Pairing</b></td><td>Unknown senders get a code; their messages never reach the model until you approve</td></tr></tbody></table>

### D1. Setup on Windows

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

### D2. Practise, step by step

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

### D3. Security model (the part that impresses)

**Pairing and allowlists** for DMs and groups. Don't open DMs to everyone with tools on. **Gateway exposure:** bind to loopback or reach it only through an authenticated private path (tailnet, SSH tunnel, trusted proxy). **Prompt injection:** web pages, emails, documents and attachments can carry instructions. Use a read-only or tool-disabled agent to summarise untrusted content; keep `web_search`, `web_fetch` and `browser` off for tool-enabled agents; use sandboxing and strict tool allowlists. **The workspace is not a sandbox.** Absolute paths can still reach the host unless sandboxing is on. **Skills and plugins are code you choose to trust.** ClawHub scan results help but are not a complete security boundary. Back up the workspace in a private Git repo; never commit secrets.

### OpenClaw: pros, cons, interview answers

<table><thead><tr><th>Pros</th><th>Cons / risks</th></tr></thead><tbody><tr><td>Self-hosted, always-on assistant reachable from chat apps; persona and memory as plain editable files; skills ecosystem; multi-agent routing; sensible pairing model</td><td>Broad host access = large attack surface; prompt injection; third- party skills are untrusted code; fast-moving project with recent Node requirements; costs per message; not a framework for building customer products</td></tr></tbody></table>

<table><thead><tr><th>Question</th><th>Crisp answer</th></tr></thead><tbody><tr><td>What did you learn from it?</td><td>The threat model of always-on agents: pairing, loopback binding, tool allowlists, sandboxing, treating skills as code, and prompt injection from every external input.</td></tr><tr><td>Skills vs AGENTS.md vs SOUL.md?</td><td>AGENTS.md = operating rules; SOUL.md = persona and boundaries; skills = loadable how-to for specific tools or tasks.</td></tr><tr><td>Would you deploy it for a client?</td><td>Not as-is for sensitive work. I&#x27;d isolate it, restrict tools, run the security audit and keep humans in the loop for irreversible actions.</td></tr></tbody></table>

## All six tools side by side

### E1. One-line identity (so you never mix them up)

<table><thead><tr><th>Tool</th><th>What it is</th><th>Who drives it</th></tr></thead><tbody><tr><td><b>Claude</b><br><b>Code</b></td><td>Agentic coding assistant in your terminal/IDE</td><td>You, interactively, on a repo</td></tr><tr><td><b>Claude API</b></td><td>Model access (tools, caching, structured output) for your own apps</td><td>Your code</td></tr><tr><td><b>n8n</b></td><td>Visual workflow automation with triggers, many app integrations and AI nodes</td><td>Events and schedules</td></tr><tr><td><b>Antigravity</b></td><td>Google&#x27;s agent-first IDE/app with artifacts and a browser agent</td><td>You, delegating tasks to agents</td></tr><tr><td><b>CrewAI</b></td><td>Python framework for multi-agent crews and flows</td><td>Your Python service</td></tr><tr><td><b>OpenClaw</b></td><td>Self-hosted always-on personal assistant over chat apps</td><td>You, by chatting</td></tr></tbody></table>

### E2. Same ideas, different names (concept map)

<table><thead><tr><th>Idea</th><th>Claude Code</th><th>Antigravity</th><th>CrewAI</th><th>OpenClaw</th><th>n8n</th></tr></thead><tbody><tr><td>Standing<br>context</td><td>CLAUDE.md</td><td>AGENTS.md,<br>GEMINI.md, rules</td><td>role/goal/backstory, AGENTS.md in scaffold</td><td>AGENTS.md,<br>SOUL.md</td><td>AI Agent<br>system<br>message</td></tr><tr><td>Reusable<br>know-how</td><td>Skills</td><td>Skills, Workflows</td><td>Tasks, Flows</td><td>Skills</td><td>Sub-workflows</td></tr><tr><td>Tools</td><td>Built-in + MCP</td><td>Terminal, browser, MCP</td><td>crewai_tools, custom</td><td>exec, browser, plugins</td><td>Nodes, tools, MCP</td></tr><tr><td>Isolation</td><td>Subagents</td><td>Parallel agents</td><td>Multiple agents</td><td>Multi-agent<br>routing</td><td>Sub-workflows</td></tr><tr><td>Guardrails</td><td>Permissions, hooks</td><td>Security preset, review policy</td><td>Guardrails, max_iter</td><td>Pairing, sandbox, allowlists</td><td>Error workflow, approvals</td></tr><tr><td>Memory</td><td>CLAUDE.md, auto memory</td><td>Rules,<br>conversations</td><td>Crew memory, knowledge</td><td>Workspace files</td><td>Memory node (per session)</td></tr></tbody></table>

### E3. Pros and cons in one table

<table><thead><tr><th>Tool</th><th>Best for</th><th>Watch out for</th></tr></thead><tbody><tr><td>Claude<br>Code</td><td>Repo-level coding with tests, hooks, reusable skills</td><td>Needs paid plan or API key; rules are advice unless enforced by hooks</td></tr><tr><td>Claude API</td><td>Embedding Claude in products: tool use, caching, JSON output</td><td>You build the loop, guardrails, evals and cost control</td></tr><tr><td>n8n</td><td>Event-driven glue between apps, schedules, human- visible flows</td><td>Complex logic gets messy on canvas; public webhooks need auth; licence terms</td></tr><tr><td>Antigravity</td><td>Delegating whole coding tasks with reviewable artifacts and browser testing</td><td>Fast-changing product and quotas; auto-execution risk</td></tr><tr><td>CrewAI</td><td>Multi-agent reasoning pipelines in Python; Flows for control</td><td>Token cost, variance, API churn</td></tr><tr><td>OpenClaw</td><td>Personal always-on assistant from your phone</td><td>Big attack surface; prompt injection; unvetted skills</td></tr></tbody></table>

### E4. Which would you pick? (practice these)

<table><thead><tr><th>Scenario</th><th>Pick, and why</th></tr></thead><tbody><tr><td>Email arrives, extract fields, update CRM, alert Slack</td><td><b>n8n</b>: trigger plus integrations, with an AI node for extraction</td></tr><tr><td>Research then write reports with different specialist roles</td><td><b>CrewAI</b> crew, wrapped in a Flow if branching is needed</td></tr><tr><td>Add a feature and tests to an existing repo</td><td><b>Claude Code</b> or <b>Antigravity</b>, with rules and tests as the check</td></tr><tr><td>Customer-facing chatbot with tool calls and tight cost</td><td><b>Claude API</b> directly, with caching and validation</td></tr><tr><td>Personal assistant I message from Telegram</td><td><b>OpenClaw</b>, isolated and locked down</td></tr></tbody></table>

> **Say This:** They stack. Antigravity or Claude Code builds the service; CrewAI holds the reasoning logic; n8n triggers it from the real world and alerts on failure; the Claude API powers the model calls; OpenClaw is my personal front door. Every layer gets guardrails, logging and a human approval step for irreversible actions.

### E5. Mentor review of everything prepared today (be honest with yourself)

<table><thead><tr><th>Area</th><th>What is solid</th><th>What to verify / my limits</th></tr></thead><tbody><tr><td>Claude playbook</td><td>Install, CLAUDE.md, skills, subagents, hooks, MCP details came from current Claude Code docs; API tool-use and caching patterns from the API docs</td><td>Permissions JSON is a sketch; hook scripts need <code>jq</code> and Git Bash on Windows; check model IDs on the day; I could not run Claude Code here</td></tr><tr><td>n8n</td><td>Docker run, test vs production webhook, publish/draft, error workflow, AI Agent settings from official docs</td><td>Items marked &quot;(verify)&quot; (background flags, retry labels, NVIDIA base URL); I did not run Docker; npm route is deprecated, so use Docker</td></tr><tr><td>Antigravity</td><td>Setup, slash commands, artifacts, rules locations and modes, skills, limits from official pages</td><td>Product and menu labels change; workflows folder path was not in the docs I could read (use the Customizations panel); MCP JSON shape unverified</td></tr><tr><td>CrewAI</td><td>Install and concepts from docs; I installed crewai 1.15.30, scaffolded a classic crew, built agents/tasks/crew and ran a Flow successfully</td><td>I could not call a live LLM (no key). Real runs may need model ID changes; NVIDIA models need <code>crewai[litellm]</code></td></tr><tr><td>OpenClaw</td><td>Requirements, install, gateway, workspace files, skills, security model from official docs</td><td>Some doc pages were truncated; Windows path forms and <code>pairing approve</code> arguments need checking; version churn is high</td></tr><tr><td>Job-sprint<br>scripts and<br>practice coach</td><td>Python logic and web routes were tested; offline grading works</td><td>PowerShell scripts were not run (no PowerShell here); NVIDIA and Claude grading paths and the browser UI were not tested live</td></tr></tbody></table>

> **Careful:** Biggest interview risk is not a wrong flag. It is claiming experience you haven't earned. Run each hands-on section once, keep a screenshot or repo for each, and prepare one honest "what broke and how I fixed it" story per tool.

<table><tbody><tr><td>E6. Seven-day practice plan for these two tools (plus recap)</td></tr><tr><td><b>Day</b></td><td><b>Do</b></td></tr><tr><td>1</td><td>CrewAI: install, scaffold <code>--classic</code> , read all files, run with NVIDIA key</td></tr><tr><td>2</td><td>CrewAI: Examples 1 and 2; then the Flow with a router</td></tr><tr><td>3</td><td>CrewAI: hierarchical run; compare token usage and quality with sequential</td></tr><tr><td>4</td><td>OpenClaw: install on a spare environment, dashboard, SOUL.md, hello-world skill</td></tr><tr><td>5</td><td>OpenClaw: interview-drill skill, Telegram pairing, security audit</td></tr><tr><td>6</td><td>Integrate: n8n webhook calls a small Python service that runs your crew; error workflow alerts</td></tr><tr><td>7</td><td>Mock interview: explain all six tools aloud using E1 to E4 without notes</td></tr></tbody></table>

30-second pitch for each (memorise the shape: what, why, risk) **Claude Code:** "I run it with a short CLAUDE.md, skills for repeated workflows, subagents for noisy work and hooks for guardrails, and I verify with tests."

**n8n:** "Self-hosted orchestration with webhooks, schedules and agents, with error workflows and publish discipline."

**Antigravity:** "I plan first, review artifacts, restrict permissions and verify in the browser agent." **CrewAI:** "Flows for control, crews for reasoning, with guardrails, iteration caps and structured output." **OpenClaw:** "A way to study always-on agent security: pairing, loopback, allowlists, sandboxing, skills as untrusted code."

Sources: CrewAI docs (installation, crews, tasks, agents, LLMs, flows) at docs.crewai.com; OpenClaw docs (getting started, security and access control, agent workspace, skills, creating skills) at docs.openclaw.ai. CrewAI code was installed and smoke-tested in a sandbox with crewai 1.15.30. Checked Oct 2026; versions and flags change, so verify before relying on exact syntax.
