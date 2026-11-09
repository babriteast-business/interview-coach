---
title: LLMOps with LangSmith
group: RAG & evals
order: 5
blurb: Trace it, test it, ship it, watch it, fix it
tagline: trace it, test it, ship it, watch it, fix it
about: RAG bot + tool-using agent, the full real-world flow comes with a lab you can run offline today and connect to LangSmith when ready
---

## How to use this tutorial

**Your approach is right, and for LLMOps it matters even more:** you cannot learn operations by reading. You must see a trace, break something, and watch a dashboard react. Five tweaks:

1. **Learn the lifecycle, not the buttons.** Build → Trace → Evaluate → Deploy → Monitor → Improve. LangSmith is only where each step gets recorded. Tools change; the loop does not.
2. **Tracing first.** Datasets, evals and monitoring are all built on traces. If you understand "a run and its child runs", the rest is easy.
3. **Connect it to your Evals notes.** Offline evals become datasets + experiments. Online monitoring is the same scorers on live traces. Same ideas, new home.
4. **One story, two apps.** A RAG support bot and a tool-using agent travel through every level, so you see one complete real-world journey, not 12 disconnected features.
5. **Practice twice:** offline first (instant, no account), then live in LangSmith. Then **teach it back** in your own words (a TEACH IT BACK box ends every level).

> **Tip:** **Cycle for every level (30-40 min):** read → run the lab command → do the PRACTICE box → close the page and explain it aloud from blank.

### Setup (5 min, PowerShell)

```powershell
cd C:\Users\god
Expand-Archive LLMOps_LangSmith_Practice_Lab.zip -DestinationPath llmops
cd llmops\lab
pip install langsmith
python run_all.py        # offline, no account, no API key
```

> **Careful:** **What is tested, honestly.** PART A (offline) was run end to end by me: it uses the **real** `langsmith` SDK (`@traceable`, `evaluate`) with a local stand-in for the server. PART B (live scripts in `live/`) was only syntax-checked; my build environment cannot reach LangSmith. UI click-paths and pricing below come from general knowledge and secondary articles, because LangSmith's own docs were not reachable from here. **Verify UI labels and prices on the live site.** Sample data in the lab is invented.

## The big picture

**LLMOps = running LLM apps reliably in production.** Like DevOps, but for systems whose output is non-deterministic, costs money per token, can fail silently (a fluent wrong answer), and (for agents) can take real actions.

LangSmith records steps TRACE, EVALUATE, MONITOR, IMPROVE (blue)

```diagram steps
plain: BUILD
blue: TRACE
blue: EVALUATE
plain: DEPLOY
blue: MONITOR
green: IMPROVE
```

every production failure becomes a new test case

<table><thead><tr><th>Stage</th><th>Question it answers</th><th>LangSmith feature [verify names in UI]</th></tr></thead><tbody><tr><td><b>Build</b></td><td>what prompt/model/retriever?</td><td>Playground, Prompt Hub (versioned prompts)</td></tr><tr><td><b>Trace</b></td><td>what exactly happened in this request?</td><td>Tracing: projects, traces, runs</td></tr><tr><td><b>Evaluate</b></td><td>is v2 better than v1, before users see it?</td><td>Datasets, <code>evaluate()</code> , experiments + comparison view</td></tr><tr><td><b>Deploy</b></td><td>how do we ship safely?</td><td>CI gate on experiments; LangSmith also has agent deployment [optional, verify]</td></tr><tr><td><b>Monitor</b></td><td>is production healthy right now?</td><td>Dashboards, online evaluators, alerts/automations</td></tr><tr><td><b>Improve</b></td><td>what do we fix, what test do we add?</td><td>Feedback, annotation queues, &quot;add trace to dataset&quot;</td></tr></tbody></table>

### Vocabulary (memorise this table)

<table><thead><tr><th>Word</th><th>Meaning</th></tr></thead><tbody><tr><td><b>Project</b></td><td>a folder of traces (for example <code>gravrel-support-dev</code> , <code>gravrel-support-prod</code> )</td></tr><tr><td><b>Trace</b></td><td>everything that happened for ONE request (a tree)</td></tr><tr><td><b>Run (span)</b></td><td>one step in that tree: LLM call, retriever, tool, chain...</td></tr><tr><td><b>Run type</b></td><td><code>llm, retriever, tool, chain, prompt, embedding, parser</code></td></tr><tr><td><b>Tags / metadata</b></td><td>labels you attach (version, user, env) so you can filter and compare later</td></tr><tr><td><b>Feedback</b></td><td>a score attached to a run (thumbs, judge score, human label)</td></tr><tr><td><b>Dataset / Example</b></td><td>your golden test set / one test case (inputs + reference outputs)</td></tr><tr><td><b>Experiment</b></td><td>one run of your app over a whole dataset, with scores</td></tr><tr><td><b>Evaluator</b></td><td>function that scores a run (code or LLM judge)</td></tr><tr><td><b>Online evaluator</b></td><td>an evaluator that scores a sample of live traces</td></tr><tr><td><b>Annotation queue</b></td><td>a to-do list of runs for humans to label</td></tr></tbody></table>

> **Teach It Back:** Say the six lifecycle stages from memory and one LangSmith feature for each. Then: why is "Improve" an arrow back to "Build"?

## The two case studies (used in every level)

```diagram flow
plain: Customer asks "How long are Pro backups kept?". Flow: retrieve top docs → build_prompt → generate (LLM). Failure modes: wrong doc, made-up fact, refused when it should answer, answered when it should refuse. | Case A: RAG support bot
plain: Customer asks "Refund me, I paid 3 days ago". Agent loops over tools: get_account , refund , escalate , create_vm . Policy: refund only if paid ≤7 days, used <10 hours, amount ≤ plan price. Failure modes: skipped check, wrong args, flaky behaviour, unsafe refund. | Case B: Support agent
```

Sample company "Gravrel" and its policies are **invented practice data**. The apps are in `apps.py`. The LLM and tools are deterministic stand-ins; all the LangSmith parts (`@traceable`, run types, tags, usage tokens) are exactly what you would use with real models.

> **Say This:** The same lab code also answers the "real world" question: swap `generate()` for a real model call and `Tools` for real APIs, leave every decorator alone, and your production app is instrumented.

## Level 1 - Tracing: seeing inside the app

### The 5-line setup (live)

```powershell
$env:LANGSMITH_TRACING = "true"
$env:LANGSMITH_API_KEY = "lsv2_..."          # smith.langchain.com -> Settings -> API keys
$env:LANGSMITH_PROJECT = "gravrel-support-dev"
pip install -U langsmith
python live/live_01_trace.py
```

### The code idea: one decorator per step

```python
from langsmith import traceable
@traceable(run_type="retriever", name="retrieve")
def retrieve(question, k): ...
@traceable(run_type="llm", name="generate")
def generate(prompt): ...            # return usage_metadata for token counts
@traceable(run_type="chain", name="rag_answer")
def rag_answer(inputs, version="v2"):
    docs = retrieve(inputs["question"], 3)     # child run
    return generate(build_prompt(...))         # child run
```

Calling `rag_answer()` creates a **trace**: a parent run with children. Nesting happens automatically because the functions call each other.

### What the lab shows (real SDK, offline)

```bash
python trace_demo.py
chain     rag_answer      33 ms
   retriever retrieve         4 ms
   prompt    build_prompt     0 ms
   llm       generate        28 ms  157 tok          <- slowest child, most tokens
(unanswerable "Do you offer GPU instances?")
chain     rag_answer       5 ms
   retriever retrieve         4 ms                   <- refused early, no LLM call
chain     support_agent    9 ms
   tool      get_account      3 ms
   tool      refund           4 ms
```

### How to READ a trace (3 debugging habits)

<table><thead><tr><th>Symptom</th><th>Look at first</th></tr></thead><tbody><tr><td>wrong answer</td><td>retriever output: did the right doc come back? (retrieval vs generation)</td></tr><tr><td>slow</td><td>the widest child run (usually the LLM call)</td></tr><tr><td>expensive</td><td>token counts per LLM run, and prompt size growth</td></tr><tr><td>agent did something odd</td><td>the sequence of tool runs under the parent (the trajectory)</td></tr></tbody></table>

### Tags, metadata, projects: decide before you ship

**Tags** = short labels to filter (`v2`, `rag`). **Metadata** = key/values (`version`, `env`, `user_id`). Always log **version**: it is what lets you find a regression later. **Separate projects** for dev / staging / prod. **Privacy:** the SDK can hide inputs and outputs (`LANGSMITH_HIDE_INPUTS=true`, `LANGSMITH_HIDE_OUTPUTS=true`). Redact personal data before logging. \[verified in SDK\] **Cost control:** `LANGSMITH_TRACING_SAMPLING_RATE` (0 to 1) traces only a share of requests. \[verified in SDK\]

> **Practice:** **Lab 1 (20 min):** run `python trace_demo.py`. (1) Draw the tree on paper. (2) Add a new traced step `@traceable(run_type="parser", name="clean_answer")` that strips spaces from the answer, call it inside `rag_answer`, re-run and find it in the tree. (3) Change `metadata` in `trace_demo.py` to include `"env": "dev"` and confirm it prints. Then live: run steps 00 and 01 and click your first real trace.

> **Teach It Back:** Explain to a non-technical teammate: "What is a trace and why can't I debug an LLM app with print statements?" Use the customer-asked-about-backups example.

## Level 2 - Prompts and iteration (Build)

**Playground:** open any LLM run from a trace, tweak the prompt or model, re-run. Fast way to test a fix on a real failing input. **Prompt Hub / prompt versions:** store prompts outside code with a commit history and tags (for example `staging`, `prod`). The SDK has `client.pull_prompt()` and `client.push_prompt()` \[verified\]. Benefit: change a prompt without redeploying code, and roll back by pointing the tag to an earlier commit. **Golden rule:** a prompt change is a release. It goes through the same dataset experiment and gate as code (Level 3).

<table><thead><tr><th>Mistake</th><th>Better habit</th></tr></thead><tbody><tr><td>editing the prod prompt in the UI &quot;just to try&quot;</td><td>new version, test on dataset, then move the <code>prod</code> tag</td></tr><tr><td>no version recorded in traces</td><td>log <code>version</code> in metadata so regressions point to a version</td></tr></tbody></table>

> **Teach It Back:** A teammate wants to tweak the prod prompt directly. Give three reasons and the safe alternative.

## Level 3 - Datasets and experiments (Evaluate) — Case A

**Idea:** dataset = your golden questions. Experiment = run an app version over the whole dataset and score it. Two experiments on the same dataset can be compared side by side.

```python
from langsmith import evaluate
evaluate(rag_target("v2"),            # function: inputs dict -> outputs dict
         data="gravrel-rag-golden",   # dataset name (or a list of examples offline)
         evaluators=[recall, faithfulness, correctness, refusal_ok],
         experiment_prefix="rag-v2")
```

An **evaluator** is a function `(run, example) -> {"key": ..., "score": ...}`. Code evaluators first; LLM- judge evaluators for the fuzzy parts (see Evals notes, Level 2: calibrate your judge!). Offline:

`upload_results=False` keeps everything local. \[verified in the SDK I installed\]

### Lab results (python exp_rag.py)

<table><thead><tr><th>version</th><th>recall</th><th>faithfulness</th><th>correctness</th><th>refusal_ok</th></tr></thead><tbody><tr><td>v1 (k=1, old prompt)</td><td>0.81</td><td>1.00</td><td>0.88</td><td>1.00</td></tr><tr><td>v2 (k=3, refuse if weak)</td><td>1.00</td><td>1.00</td><td>1.00</td><td>1.00</td></tr><tr><td>v3-bug (adds &quot;free GPU&quot; claim)</td><td>1.00</td><td><b>0.76</b></td><td>1.00</td><td>1.00</td></tr></tbody></table>

**Flipped cases v1 → v2:** q7 (refund question), q11 and q12 (needed two documents). Averages hide which questions changed, so always read the flips.

> **Say This:** Regression gate in the lab: candidate v3-bug vs baseline v2. Result: **FAIL, block release**: faithfulness 1.00 → 0.76. A gate is real only if it can fail.

### Where datasets come from

1. Your hand-written golden cases (start with 30-50).
2. **Production traces** that failed (Level 5): select a trace → add it to a dataset.
3. Cases from annotation queues after human review.

### CI gate in PowerShell

```bash
python exp_rag.py
if ($LASTEXITCODE -ne 0) { Write-Host "BLOCK RELEASE"; exit 1 }
```

> **Practice:** **Lab 2 (30 min):** (1) run `python exp_rag.py` and explain each row. (2) Add 3 new golden cases in `golden_rag.json` (one needs 2 documents, one unanswerable) and re-run. (3) Write a new evaluator `concise` that scores 1 when the answer has at most 3 sentences; add it to `RAG_EVALUATORS` in `evaluators.py`. (4) Live: run `live/live_02_dataset_experiment.py`, then in the LangSmith UI open the dataset, tick two experiments and press Compare.

> **Teach It Back:** Explain the difference between a **trace**, a **dataset** and an **experiment** using the support bot, in under one minute.

## Level 4 - Agents in LangSmith — Case B

**What a trace of an agent looks like:** one parent run `support_agent`, one child run per tool call, in order. That ordered list of tool runs **is the trajectory**. Each tool is decorated with `@traceable(run_type="tool")`, so arguments and results are recorded.

```
chain  support_agent
   tool  get_account  {user_id: "u2"}  -> {plan: "pro", usage_hours: 4, paid_days_ago: 3}
   tool  refund       {user_id: "u2", amount: 1999}
```

### Evaluate by WORLD STATE, not words

<table><thead><tr><th>Evaluator</th><th>Checks</th></tr></thead><tbody><tr><td><code>outcome</code></td><td>final state right? (VM created / refund recorded or escalated / correct answer)</td></tr><tr><td><code>safety</code></td><td>no refund that breaks policy (hard gate, zero tolerance)</td></tr><tr><td><code>path_efficiency</code></td><td>ideal steps / actual steps</td></tr><tr><td>(+ reliability)</td><td><code>num_repetitions=5</code> runs every task 5 times: pass@5 vs pass^5</td></tr></tbody></table>

### Lab results (python exp_agent.py, k=5)

<table><thead><tr><th>agent</th><th>outcome</th><th>safe</th><th>path</th><th>pass@5</th><th>pass^5</th></tr></thead><tbody><tr><td>good</td><td>1.00</td><td>1.00</td><td>1.00</td><td>1.00</td><td>1.00</td></tr><tr><td>sloppy</td><td>0.67</td><td><b>0.67</b></td><td>0.92</td><td>0.67</td><td>0.67</td></tr><tr><td>flaky (35% wrong)</td><td>0.83</td><td>1.00</td><td>0.93</td><td><b>1.00</b></td><td><b>0.67</b></td></tr></tbody></table>

**Read it:** sloppy skips `get_account` and refunds ineligible users: the trace shows only `refund`, no account check. flaky can do everything at least once (pass@5 = 1.00) but not every time (pass^5 = 0.67). If one try works 80% of the time, five in a row work only 0.8 5 ≈ 33%.

> **Careful:** Real agents also get multi-turn conversations. LangSmith can group traces into threads via a metadata key such as a thread/session/conversation id \[name not verified here; check the docs\]. Always log one so you can replay a whole customer conversation.

> **Practice:** **Lab 3 (30 min):** (1) run `python exp_agent.py`. (2) In `trace_demo.py` find the sloppy agent's tree and say what is missing. (3) Add task t7 to `golden_agent.json`: "Refund u2 Rs 5000" (kind `refund_big`, should\_refund false). Predict each agent's outcome first, then run. (4) Make `sloppy` pass the gate by checking the account first.

> **Teach It Back:** Why can an agent have a 100% "task success" in a demo and still be unsafe to launch? Use pass^k and the safety evaluator.

## Level 5 - Production: monitor and improve

### What to watch (the five signals)

<table><thead><tr><th>Signal</th><th>Why</th><th>Alert example</th></tr></thead><tbody><tr><td>Latency (p50 / p95)</td><td>users leave when slow</td><td>p95 &gt; 1.35 s</td></tr><tr><td>Error rate</td><td>tool or model failures</td><td>&gt; 3%</td></tr><tr><td>Tokens and cost</td><td>bills surprise you</td><td>&gt; 1.3× 7-day baseline</td></tr><tr><td>User feedback</td><td>real-world quality</td><td>thumbs-down &gt; 20%</td></tr><tr><td>Online eval score</td><td>quality on live traffic</td><td>faithfulness &lt; 85%</td></tr></tbody></table>

**Online evaluators:** you configure a rule on a project: "on N% of new traces, run this evaluator". Sample rate matters: judging every request is expensive; judging 10-25% gives a stable estimate. \[In the UI this lives under your project's automations/rules; verify labels.\]

### The incident replay (python prod_monitor.py, SIMULATED data)

<table><thead><tr><th>metric</th><th>days 1-8 (v2)</th><th>days 9-14 (v3-bug)</th></tr></thead><tbody><tr><td>p95 latency</td><td>about 1.1-1.2 s</td><td>about 1.4 s</td></tr><tr><td>error rate</td><td>0-2%</td><td>4-8%</td></tr><tr><td>cost / day</td><td>about $0.07</td><td>about $0.11 (+55%)</td></tr><tr><td>thumbs-down</td><td>0-12%</td><td>25-43%</td></tr><tr><td>online faithfulness</td><td>92-100%</td><td>48-71%</td></tr></tbody></table>

**What you do, step by step (this is the real-world flow):**

1. **Alert fires** (day 9): five alerts at once, so it is a release problem, not noise.
2. **Filter by metadata** `version`: all bad traces are `v3-bug`.
3. **Open a bad trace:** the answer has the "free GPU" sentence not present in the retrieved context: generation bug, retrieval fine.
4. **Roll back** to v2 (move the `prod` prompt tag / redeploy).
5. **Capture:** send the flagged traces to a dataset (lab: `new_golden_candidates.json`) and label them.
6. **Fix and re-test** through the Level 3 experiment and gate, then ship v4.

> **Say This:** The flywheel: **fail in production → becomes a dataset example → guards every future release.**

### Humans in the loop

**Annotation queues**: send uncertain or flagged runs to reviewers, collect labels, use them to (a) create golden cases, (b) calibrate your LLM judge (kappa, from the Evals notes).

### Plans and cost (secondary source, verify on the pricing page)

One article dated 23 Sep 2026 lists: Developer (free): 1 seat, 5,000 base traces/month, 14-day retention. Plus: $39 per seat/month, 10,000 base traces shared, extra traces billed per 1,000, with an extended-retention option. I did not confirm these on LangSmith's own pricing page. **Practical rule:** on the free tier, use **sampling** and a separate dev project so practice does not eat your quota.

> **Practice:** **Lab 4 (30 min):** (1) run `python prod_monitor.py`. (2) Change the alert thresholds so that a healthy day triggers a **false alarm**; explain why small samples and a noisy judge cause that. (3) Open `new_golden_candidates.json`, write the correct answer for 3 items. (4) Live: attach feedback with `live/live_03_feedback_and_query.py` and find the trace in the UI.

> **Teach It Back:** Tell the incident story in 60 seconds: first signal, how you found the cause, what you rolled back, what you added so it cannot happen again.

## The complete flow, one page (real-world version)

<table><thead><tr><th>Step</th><th>RAG bot (Case A)</th><th>Agent (Case B)</th></tr></thead><tbody><tr><td>1 Instrument</td><td>@traceable on retrieve, build_prompt, generate; tags + version</td><td>@traceable on the agent loop and every tool; thread id</td></tr><tr><td>2 Inspect</td><td>retriever output right? tokens?</td><td>trajectory right? args right?</td></tr><tr><td>3 Dataset</td><td>30-50 questions, incl. unanswerable</td><td>10-20 tasks with end-state checks and a forbidden action</td></tr><tr><td>4<br>Experiment</td><td>recall, faithfulness, correctness, refusal</td><td>outcome, safety, path, pass^k</td></tr><tr><td>5 Gate</td><td>faithfulness ≥ 0.95 and no drop vs baseline</td><td>safety = 100%, pass^k ≥ 0.95</td></tr><tr><td>6 Ship</td><td>tag the prompt/version <code>prod</code></td><td>same, behind a feature flag</td></tr><tr><td>7 Monitor</td><td>latency, cost, thumbs, online faithfulness</td><td>error rate, tool failure, escalations, cost per task</td></tr><tr><td>8 Improve</td><td>bad traces → dataset → fix</td><td>unsafe traces → dataset → stricter policy check</td></tr></tbody></table>

### Live walkthrough in the LangSmith UI [labels may differ; verify]

1. Sign up (free), create an API key, run `live_00_env.ps1` then `live_01_trace.py`.
2. Tracing → your project → click a trace → expand children → compare to the offline tree.
3. Run `live_02_dataset_experiment.py` → Datasets & Experiments → select two experiments → Compare. Read the flipped examples.
4. Run `live_03_feedback_and_query.py <run_id>` → find the feedback on the trace.
5. In your project, create an online evaluator rule with sampling rate 25% (UI), then watch the monitoring dashboards.

## Practice plan, flashcards, script

### 7-day plan (30-45 min a day)

<table><thead><tr><th>Day</th><th>Do</th><th>Proof</th></tr></thead><tbody><tr><td>1</td><td>Part 0-2, run <code>run_all.py</code> , write the lifecycle from memory</td><td>voice note: &quot;what is LLMOps&quot; in 60 s</td></tr><tr><td>2</td><td>Level 1, Lab 1; create free LangSmith account, run live 00-01</td><td>screenshot of your first real trace</td></tr><tr><td>3</td><td>Level 2: version a prompt, define your <code>prod</code> tag rule</td><td>explain why a prompt change is a release</td></tr><tr><td>4</td><td>Level 3, Lab 2, live 02 and Compare</td><td>explain flipped cases of v1 → v2</td></tr><tr><td>5</td><td>Level 4, Lab 3 (t7, fix sloppy)</td><td>explain pass@k vs pass^k with 0.85</td></tr><tr><td>6</td><td>Level 5, Lab 4; instrument YOUR real app with 3 traces</td><td>one trace you can narrate step by step</td></tr><tr><td>7</td><td>Teach: present &quot;LLMOps with LangSmith in 5 minutes&quot;</td><td>a friend can restate the loop + one incident</td></tr></tbody></table>

### Flashcards (cover the right side)

<table><thead><tr><th>Q</th><th>A</th></tr></thead><tbody><tr><td>Lifecycle?</td><td>Build, Trace, Evaluate, Deploy, Monitor, Improve, loop</td></tr><tr><td>Trace vs run?</td><td>trace = whole request tree; run = one step in it</td></tr><tr><td>Run types?</td><td>llm, retriever, tool, chain, prompt, embedding, parser</td></tr><tr><td>Tags vs metadata?</td><td>tags: short filter labels; metadata: key/values like version, env</td></tr><tr><td>Dataset vs experiment?</td><td>test cases vs one scored run of a version over them</td></tr><tr><td>Evaluator signature?</td><td>(run, example) -&gt; {&quot;key&quot;, &quot;score&quot;}</td></tr><tr><td>Offline vs online eval?</td><td>before release on a dataset vs after release on sampled live traces</td></tr><tr><td>Why log version?</td><td>to find which release caused a regression</td></tr><tr><td>Agent outcome check?</td><td>final world state, not chat text</td></tr><tr><td>pass^k?</td><td>all k trials pass; 0.8 per try over 5 = about 0.33</td></tr><tr><td>Cost control for tracing?</td><td>sampling rate, hide inputs, separate dev project</td></tr><tr><td>Flywheel?</td><td>production failure → dataset case → future gate</td></tr></tbody></table>

### Common mistakes

No version in metadata. • One project for dev and prod. • Logging customer personal data. • Comparing experiments on different datasets. Only averages, never the flipped cases. • An alert with no owner. • Judging every request when a sample would do.

### Your 60-second script

> **Say This:** "LLMOps is running LLM apps reliably in production. I instrument every step so each request is a trace I can inspect. I keep a golden dataset and run experiments so a prompt or model change is tested before release, with a gate that blocks regressions. In production I watch latency, errors, cost, user feedback and sampled online evals, tagged by version. When something breaks I find the bad traces, roll back, add them to the dataset, and fix forward, so the same failure can never ship twice."

Verified by running the SDK: traceable, evaluate (upload\_results, num\_repetitions), create\_dataset/examples/feedback, list\_runs, pull/push\_prompt, env vars for tracing, hiding and sampling. Not verified live: UI labels, online-evaluator setup, pricing (ZenML, 23 Sep 2026), thread key.
