---
title: CrewAI
group: Agents & tools
order: 11
blurb: Setup, agents, flows and real examples
tagline: setup · agents · flows · real examples
about: Docs checked and code smoke-tested, Oct 2026 · Anything marked (verify) is from general knowledge. Re-check commands before the interview.
---

## CrewAI - from scratch to interview-ready

### C0. What it is (say this in 20 seconds)

> **Say This:** CrewAI is a Python framework for multi-agent systems. I define agents with a role, goal and backstory, give them tasks and tools, and a Crew runs them in a process. For deterministic control I wrap crews in Flows, which add state, routing and ordinary Python.

<table><thead><tr><th>Concept</th><th>What it is (key attributes)</th></tr></thead><tbody><tr><td><b>Agent</b></td><td><code>role</code> , <code>goal</code> , <code>backstory</code> , <code>llm</code> , <code>tools</code> , <code>max_iter</code> (default 20), <code>max_rpm</code> , <code>allow_delegation</code> (default False), <code>max_execution_time</code> , <code>planning_config</code> (plan before acting; replaces the deprecated <code>reasoning</code> )</td></tr><tr><td><b>Task</b></td><td><code>description</code> , <code>expected_output</code> , <code>agent</code> , <code>context</code> (earlier tasks feeding this one), <code>output_pydantic</code> , <code>output_file</code> , <code>guardrail</code> , <code>async_execution</code> , <code>human_input</code></td></tr><tr><td><b>Crew</b></td><td>agents + tasks + <code>process</code> (sequential default, or hierarchical with a manager: <code>manager_llm</code> required), <code>memory</code> , <code>planning</code> , <code>max_rpm</code> , <code>verbose</code></td></tr><tr><td><b>Run</b></td><td><code>kickoff(inputs={...})</code> , <code>kickoff_for_each</code> , async variants. Returns <code>CrewOutput</code> : <code>raw</code> , <code>pydantic</code> , <code>json_dict</code> , <code>tasks_output</code> , <code>token_usage</code></td></tr><tr><td><b>Tools</b></td><td>Instances in <code>tools=[...]</code> (e.g. <code>SerperDevTool</code> from <code>crewai_tools</code> ) or LangChain tools</td></tr><tr><td><b>Flow</b></td><td>Python class with <code>@start</code> , <code>@listen</code> , <code>@router</code> , Pydantic state in <code>self.state</code> ; can call crews</td></tr><tr><td><b>Memory /</b><br><b>Knowledge</b></td><td>Short-term, long-term, entity memory; <code>knowledge/</code> folder for reference files</td></tr></tbody></table>

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
# crew_demo.py   (uv add crewai litellm   - or pip install crewai litellm for a quick test)
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

> **Careful:** Gotcha I hit: naming the handler the same as the route label (`def big` listening to `"big"`) fails with an "infinite loop" validation error. Name handlers differently from route strings.

Real use: `@start` reads input, `@router` classifies it, `@listen("complaint")` calls a support Crew, `@listen("sales")` calls a sales Crew. Scaffold with `crewai create flow <name>`; add a crew with `crewai flow add-crew <name>`; visualise with `crewai flow plot`.

### CrewAI: pros, cons, interview answers

<table><thead><tr><th>Pros</th><th>Cons / risks</th></tr></thead><tbody><tr><td>Fast to prototype role-based multi-agent work; readable YAML; CLI scaffolding; many tools and LLM providers; Flows give deterministic control, state and routing</td><td>Agent loops burn tokens and are non-deterministic; hierarchical manager can mis-delegate; APIs and project layout change quickly (classic vs JSON-first); debugging needs verbose logs and tracing; needs guardrails and evals</td></tr></tbody></table>

<table><thead><tr><th>Question</th><th>Crisp answer</th></tr></thead><tbody><tr><td>Sequential vs<br>hierarchical?</td><td>Sequential runs tasks in order, passing outputs. Hierarchical adds a manager ( <code>manager_llm</code> required) that delegates and validates; more flexible, more cost and variance.</td></tr><tr><td>Crew vs Flow?</td><td>Crew = collaborating agents for judgment work. Flow = event-driven Python with state and routing; it can call crews. Use Flows for control, crews for reasoning.</td></tr><tr><td>How do you stop<br>runaway agents?</td><td><code>max_iter</code> , <code>max_rpm</code> , narrow tools, <code>allow_delegation=False</code> , guardrails on tasks, structured output, tracing.</td></tr><tr><td>How do tasks share data?</td><td>Sequential passes output along; <code>context=[...]</code> selects specific earlier tasks; Flow state shares data across steps.</td></tr><tr><td>Why CrewAI vs n8n?</td><td>CrewAI is code-first agent reasoning inside a Python service. n8n is visual orchestration of triggers, apps and APIs. I often call a CrewAI service from n8n.</td></tr></tbody></table>

### C4. Your own tools (tested)

Two ways. Class form (I ran this in a sandbox; `run()` returned the word count):

```python
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
class TextIn(BaseModel):
    text: str = Field(..., description="Text to count words in")
class WordCounter(BaseTool):
    name: str = "word_counter"
    description: str = "Counts the words in a piece of text."
    args_schema: type[BaseModel] = TextIn
    def _run(self, text: str) -> str:
        return str(len(text.split()))
agent = Agent(role="Editor", goal="...", backstory="...", llm=llm, tools=[WordCounter()])
```

Decorator form (from the scaffold's own guidance): `from crewai.tools import tool` then `@tool("Word counter")` on a function; the **docstring becomes the description**. Scaffold a template with `crewai create tool <name>`.

> **Say This:** The agent only knows a tool through its name, description and argument schema, so I write those like an API contract. A vague description means wrong tool choices.

### C5. Mini project: JobFit (Flow + crews + code) - build this one

Input: a job description in `jd.txt`. Output: a match score and 4 honest resume bullets. Design rule from the scaffold's guidance: **agents judge, code computes**. The model extracts requirements into a Pydantic object; plain Python calculates the score; a second agent writes bullets using only skills you really have.

`from pydantic import BaseModel from crewai import Agent, Task, Crew, Process, LLM from crewai.flow.flow import Flow, start, listen`

`llm = LLM(model="nvidia_nim/meta/llama-3.1-70b-instruct") # needs NVIDIA_API_KEY MY_SKILLS = {"python", "fastapi", "rag", "llm", "agents", "docker", "sql"}`

`class Reqs(BaseModel): must_have: list[str] nice_to_have: list[str]`

`class State(BaseModel): jd: str = "" must_have: list[str] = [] score: int = 0 bullets: str = ""`

`extractor = Agent(role="JD Analyst", goal="Extract skill requirements from a job description", backstory="Reads job posts precisely and never invents requirements.", llm=llm, max_iter=5) writer = Agent(role="Resume Coach", goal="Write honest, tailored resume bullets", backstory="Only uses skills the candidate really has.", llm=llm, max_iter=5)`

`class JobFit(Flow[State]): @start() def extract(self): t = Task(description="Extract requirements from this job description:\n{jd}", expected_output="JSON with must_have and nice_to_have skill lists", agent=extractor, output_pydantic=Reqs) out = Crew(agents=[extractor], tasks=[t], process=Process.sequential).kickoff( inputs={"jd": self.state.jd}) self.state.must_have = [s.lower() for s in out.pydantic.must_have]`

`@listen(extract) def score(self): # code computes, agents only judge hits = [s for s in self.state.must_have if any(k in s for k in MY_SKILLS)] self.state.score = round(100 * len(hits) / max(1, len(self.state.must_have))) print("Match score:", self.state.score)`

`@listen(score) def bullets(self): t = Task(description="Write 4 honest resume bullets for a role needing: {needs}. " "The candidate's real skills: {mine}. Never claim other skills.", expected_output="4 bullets", agent=writer) out = Crew(agents=[writer], tasks=[t], process=Process.sequential).kickoff(`

```
            inputs={"needs": ", ".join(self.state.must_have), "mine": ", ".join(sorted(MY_SKILLS))})
        self.state.bullets = out.raw
        return out.raw
if __name__ == "__main__":
    print(JobFit().kickoff(inputs={"jd": open("jd.txt").read()}))
```

```powershell
# PowerShell
$env:NVIDIA_API_KEY = "nvapi-your-key"
notepad jd.txt          # paste a real job post, save
python jobfit.py
```

I validated this flow (class definition, state, wiring) and ran the scoring step in a sandbox: with requirements `python, kubernetes, rag pipelines` it printed a score of 67. The two LLM steps I could not run (no key). Edit `MY_SKILLS` to what is true for you. The prompt forbids claiming other skills; check the bullets anyway. Extend: add a `@router` that sends a score under 50 to "skip" and over 50 to "apply".

> **Say This:** The score is deterministic Python, so I can unit-test it and explain it. The model only does language work: extraction and wording. That's how I keep agents auditable.

### C6. Memory, knowledge, single agents

**Knowledge:** `knowledge_sources=[StringKnowledgeSource(content=...), PDFKnowledgeSource(file_paths=[...])]` on an agent or crew (the scaffold also creates a `knowledge/` folder). **Memory in a Flow:** `self.remember("text")` and `self.recall("query")`. Inside a flow don't use `Crew(memory=True)`; share memory with `Crew(memory=self.memory.slice(scopes=[...], read_only=True))`. Memory is rooted at the flow class name, so renaming the class starts fresh. **Persist state:** `@persist` (from `crewai.flow`) saves state per run; resume with `kickoff(inputs= {"id": ...})` or seed with `kickoff(restore_from_state_id=...)`. **One agent, no crew needed:** `Agent(...).kickoff("question", response_format=MyModel)` returns `.raw` and `.pydantic`. **Reliability knobs:** `max_iter`, `max_execution_time`, `max_rpm`, `tool_failure_policy="raise"` (a failed tool becomes an error), `Crew(cache=True)` for tool-result caching, `respect_context_window` (on by default; summarises history near the limit). **Deprecated, don't use:** `reasoning` (use `planning_config`), `multimodal`, `allow_code_execution` (use a sandbox tool), `function_calling_llm`.

### C7. CLI cheat-sheet

<table><thead><tr><th>Command</th><th>Use</th></tr></thead><tbody><tr><td><code>crewai create crew|flow|tool|skill</code> <code>&lt;name&gt;</code></td><td>Scaffold (add <code>--classic</code> for the YAML + crew.py crew)</td></tr><tr><td><code>crewai install</code> / <code>crewai run</code></td><td>Sync dependencies / run the project</td></tr><tr><td><code>crewai flow plot</code></td><td>HTML diagram of a flow</td></tr><tr><td><code>crewai log-tasks-outputs</code> , <code>crewai replay</code> <code>-t &lt;task_id&gt;</code></td><td>Inspect task outputs; rerun from one task</td></tr><tr><td><code>crewai reset-memories -m</code> ( <code>-kn</code> knowledge)</td><td>Clear memory / knowledge</td></tr><tr><td><code>crewai traces enable|status</code></td><td>Tracing (also <code>CREWAI_TRACING_ENABLED=true</code> in <code>.env</code> )</td></tr><tr><td><code>crewai test</code> , <code>crewai train</code></td><td>Legacy per the scaffold&#x27;s own guidance</td></tr><tr><td><code>crewai login</code> , <code>crewai deploy ...</code></td><td>Optional CrewAI AMP platform (deploy, traces); not needed to learn the framework</td></tr></tbody></table>

Use `uv` for packages (`uv add <pkg>`), keep secrets in `.env` and never commit it.

### C8. Seven-day CrewAI plan

<table><thead><tr><th>Day</th><th>Do</th><th>Proof to keep</th></tr></thead><tbody><tr><td>1</td><td>Install, scaffold <code>--classic</code> , run with NVIDIA key</td><td>Screenshot of <code>report.md</code></td></tr><tr><td>2</td><td>Example 1 and 2 (structured output, guardrail)</td><td>Repo + output JSON</td></tr><tr><td>3</td><td>Own tool (C4); give it to an agent</td><td>Verbose log showing the tool call</td></tr><tr><td>4</td><td>Hierarchical vs sequential on the same task; compare <code>token_usage</code></td><td>Small comparison table</td></tr><tr><td>5</td><td>Flow with router (Example 4)</td><td><code>crewai flow plot</code> diagram</td></tr><tr><td>6</td><td>Build JobFit (C5) and run it on 3 real job posts</td><td>3 scores + bullets</td></tr><tr><td>7</td><td>Mock interview: explain Agent, Task, Crew, Flow, guardrails and failure modes aloud</td><td>Your own one-page notes</td></tr></tbody></table>

> **Careful:** Be ready for: "What went wrong?" Honest examples: the LiteLLM extra missing for NVIDIA models, a handler named like its route label, an agent inventing a requirement that your code then scored. Real stories beat polished claims.

Sources: docs.crewai.com (installation, crews, tasks, agents, LLMs, flows) and the guidance file CrewAI generates in every scaffolded project (AGENTS.md). Code smoke-tested with crewai 1.15.30 in a sandbox, without live LLM calls. Checked Oct 2026.
