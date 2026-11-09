---
title: LLM evals
group: RAG & evals
order: 4
blurb: From "looks fine" to proof, with RAG and agent case studies
tagline: from "looks fine" to proof — RAG + Agent case studies
about: Learn it, run it, break it, teach it comes with a runnable practice lab (zip). Sample data only.
---

## How to use this tutorial

**Your approach (examples + practice + explain in your own words) is the right one.** It is how experts learn evals. Five tweaks that make it faster:

1. **Learn ONE loop, not 30 metrics.** If you remember the loop, you can re-invent any metric on the spot.
2. **Start from failures, not from metrics.** Read 30 real outputs, name how they fail, then choose metrics.
3. **Score the parts separately.** RAG = retrieval and generation. Agent = outcome, tool calls, path, safety.
4. **A judge is an instrument.** Calibrate it against your own labels before you trust it.
5. **Memory = retrieval practice.** Don't re-read. Close the page and explain from blank. Every level ends with a TEACH IT BACK box.

> **Tip:** **Study cycle for every level (20-40 min):** read the page → run the lab command → do the PRACTICE box → close everything and TEACH IT BACK aloud (phone voice note is fine). If you stumble, that is exactly what to re-read.

### Setup (5 minutes, PowerShell)

```powershell
cd C:\Users\god
Expand-Archive LLM_Evals_Practice_Lab.zip -DestinationPath evals_lab
cd evals_lab\lab
python --version          # 3.9 or newer
python run_all.py         # runs everything, offline, no API key
```

All numbers quoted in these notes come from that lab, so you can reproduce them. The "app" and "agents" in the lab are small **stand-ins** (rule-based) so the results are deterministic. In real work you swap in your LLM calls; the metrics and gates stay the same.

> **Careful:** The documents in the lab (Gravrel "Starter / Pro" prices etc.) are **invented sample data** for practice, not real company policy.

## The whole subject on one page

**An eval = a repeatable test that turns "seems fine" into a number you can track.** It is the unit test of a probabilistic system: the same question can give different answers, so we test many cases and look at rates.

#### G . A . U . G . E

**G - Gather failures** read real outputs, write down HOW it fails (error analysis)

**A - Annotate gold** build a golden set: question + what a right answer must contain

**U - Use scorers** code checks first, LLM judge second, humans to calibrate

**G - Grade by part** retrieval vs generation; outcome vs tools vs path vs safety

**E - Enforce a gate** thresholds in CI; a change that drops a score does not ship

### Five questions that always unlock an eval (memorise these)

1. What can go wrong here? (failure modes)
2. What does "right" look like? (gold / rubric)
3. Who scores it: code, a model, or a human?
4. Which component broke when it fails?
5. How do I know my fix did not break something else? (regression)

<table><thead><tr><th>Word</th><th>Meaning in one line</th></tr></thead><tbody><tr><td>Benchmark</td><td>public test to compare models (MMLU-like). Not your product.</td></tr><tr><td>Eval (offline)</td><td>your test set + scorers, run before shipping</td></tr><tr><td>Monitoring (online)</td><td>sampling live traffic and feedback after shipping</td></tr><tr><td>Golden set</td><td>your curated test cases with expected facts</td></tr><tr><td>Scorer / grader</td><td>the thing that gives a score: code, LLM judge, or human</td></tr><tr><td>Regression gate</td><td>&quot;if score drops below X, block the release&quot;</td></tr></tbody></table>

> **Teach It Back:** In 60 seconds: why can't I just "try it a few times and see"? (Hint: variance, hidden failures, silent regressions when you change a prompt.)

## Level 1 - Error analysis and the golden set

**Do this before any metric.** Pull 30-50 real or realistic inputs, run your system, and read every output. Write one line per failure. Group them. The groups ARE your eval plan.

<table><thead><tr><th>Failure group (RAG support bot)</th><th>Example</th><th>Becomes a metric</th></tr></thead><tbody><tr><td>wrong / missing doc retrieved</td><td>asks invoice question, gets backup doc</td><td>recall@k</td></tr><tr><td>made-up fact</td><td>&quot;all plans include free GPU&quot;</td><td>faithfulness</td></tr><tr><td>incomplete answer</td><td>gives Starter price, forgets Pro</td><td>correctness (must-include facts)</td></tr><tr><td>answers when it should refuse</td><td>&quot;Do you offer GPU?&quot; answered anyway</td><td>refusal accuracy</td></tr></tbody></table>

### Golden set recipe

**Size:** start with 30-50 good cases. Grow it every time production shows a new failure. **Mix:** easy, paraphrased, multi-document, unanswerable (should refuse), tricky near-misses, adversarial. **Each case stores:** question, the doc(s) that hold the answer, **facts a correct answer must contain**, and whether it is answerable. **Dev / held-out split:** tune on one part, report on the other, or you will over-fit your fixes to the test. **Version it** (git). A score is only meaningful against a known set.

> **Practice:** Open `golden_rag.json`. It has 15 cases: 10 single-fact, 2 multi-document (q11, q12), 2 unanswerable (q13, q14), 1 trap (q15). **Add 5 cases of your own** (one multi-document, one unanswerable). Re-run `python rag_eval.py` and see if any score moves.

> **Teach It Back:** Why must a golden set include questions that SHOULD be refused? What score would hide that failure?

## Level 2 - Scorers: code, judge, human

<table><thead><tr><th>Scorer</th><th>Use for</th><th>Pros</th><th>Cons</th></tr></thead><tbody><tr><td><b>Code</b></td><td>exact match, contains facts, JSON valid, tool args right, final state correct, latency, cost</td><td>free, fast,<br>deterministic</td><td>can&#x27;t judge tone or open- ended meaning</td></tr><tr><td><b>LLM</b><br><b>judge</b></td><td>helpfulness, faithfulness to context, tone, &quot;does it follow the policy&quot;</td><td>scales, handles nuance</td><td>biased, costs money, needs calibration</td></tr><tr><td><b>Human</b></td><td>creating gold labels, calibrating judges, final say on hard cases</td><td>ground truth</td><td>slow, expensive,<br>inconsistent</td></tr></tbody></table>

> **Say This:** Rule of thumb: use code wherever you can, a judge where you must, humans to check the judge.

### How to write a good LLM-judge prompt

1. **One criterion per judge** (faithfulness OR tone, not both).
2. **Binary pass/fail beats 1-10.** Clear definitions of pass and fail.
3. **Give the evidence:** the question, the retrieved context, the reference facts, the answer.
4. **Reason first, verdict last** ("explain briefly, then output PASS or FAIL").
5. Run it at temperature 0. Test with 2-3 worked examples inside the prompt.

```yaml
You are grading ONE thing: is every claim in ANSWER supported by CONTEXT?
CONTEXT: {context}
ANSWER: {answer}
List each claim. For each, say SUPPORTED or UNSUPPORTED with a quote.
Final line exactly: VERDICT: PASS (all supported) or VERDICT: FAIL
```

### Known judge biases (check for them!)

<table><thead><tr><th>Bias</th><th>What happens</th><th>Test</th></tr></thead><tbody><tr><td>Verbosity</td><td>longer answer = higher score</td><td>pad a bad answer; does it now pass?</td></tr><tr><td>Position</td><td>prefers the first answer in pairwise</td><td>swap A and B</td></tr><tr><td>Self-preference</td><td>favours its own model family&#x27;s style</td><td>use a different judge model</td></tr></tbody></table>

### Calibrate: compare judge with humans

Label 50-100 outputs yourself, run the judge, then compute **agreement** and **Cohen's kappa** (agreement corrected for chance: 0 = luck, 1 = perfect; aim above about 0.6). Rule of thumb from the references I read: validate on roughly 50-100 human-labelled examples and look for correlation near 0.7 or better before relying on a judge.

```bash
python judge_calibration.py
agreement 0.40   Cohen kappa -0.20
bad answers the judge PASSED just because they were long: 7 of 10
```

> **Practice:** Edit `judge()` in `judge_calibration.py` so it checks the answer against a reference fact instead of its length (hint: compare numbers and key words with the question's expected fact). Aim for kappa above 0.6. Then explain why length was a bad signal.

> **Teach It Back:** Explain verbosity bias to a non-technical friend using a school-exam analogy. Then say how you would catch it in 5 minutes.

## Level 3 - RAG evals (Case study 1: the support bot)

**Case:** a Gravrel-style support bot answers customer questions from 12 policy snippets (prices, backups, data residency, refunds...). Flow: **question → retrieve top-k docs → generate answer from them**. When the answer is wrong, you must know which half broke.

```diagram steps
plain: Question
blue: RETRIEVER | hit@k recall@k MRR · precision@k
green: GENERATOR | faithfulness correctness · refusal relevance
```

Answer

### The metrics (with how to compute)

<table><thead><tr><th>Metric</th><th>Question it answers</th><th>How</th></tr></thead><tbody><tr><td><b>hit@k</b></td><td>did ANY right doc make the top-k?</td><td>1 if gold ∩ top-k is not empty</td></tr><tr><td><b>recall@k</b></td><td>how many of the needed docs did we get?</td><td>|gold ∩ top-k| / |gold|</td></tr><tr><td><b>precision@k</b></td><td>how much of top-k is useful?</td><td>|gold ∩ top-k| / k</td></tr><tr><td><b>MRR</b></td><td>how high is the first right doc?</td><td>average of 1/rank of first gold doc</td></tr><tr><td><b>Faithfulness</b><br>(groundedness)</td><td>is every claim backed by the retrieved context?</td><td>supported claims / all claims (judge, or the lab&#x27;s word-overlap check)</td></tr><tr><td><b>Correctness</b></td><td>did it say the needed facts?</td><td>must-include facts found / total</td></tr><tr><td><b>Answer relevance</b></td><td>does it answer THE question?</td><td>judge</td></tr><tr><td><b>Refusal accuracy</b></td><td>refuses when unanswerable, answers when answerable</td><td>compare to the answerable flag</td></tr><tr><td>Latency / cost</td><td>fast and cheap enough?</td><td>measure per request</td></tr></tbody></table>

> **Tip:** Frameworks such as Ragas and DeepEval offer judge-based versions of context precision, context recall, faithfulness and answer relevancy. Learn the ideas here first, then plug a framework in. \[Verify current function names in their docs; they change.\]

### The diagnosis matrix (the most useful table in this file)

<table><thead><tr><th>What you see</th><th>Broken part</th><th>Typical fixes</th></tr></thead><tbody><tr><td>low recall@k</td><td>RETRIEVER</td><td>better chunking, stemming/synonyms, hybrid keyword+embedding search, bigger k, query rewrite</td></tr><tr><td>recall fine, faithfulness low</td><td>GENERATOR<br>hallucinates</td><td>stricter prompt (&quot;only from context&quot;), lower temperature, quote citations, judge in CI</td></tr><tr><td>faithful but correctness low</td><td>missing/cut facts</td><td>more context, longer answer budget, better ranking</td></tr><tr><td>answers unanswerable questions</td><td>NO ABSTAIN rule</td><td>score threshold, &quot;say I don&#x27;t know&quot; instruction, refusal examples</td></tr><tr><td>precision low, answers noisy</td><td>too much context</td><td>re-rank, smaller k, filter</td></tr></tbody></table>

### Live results from the lab (you can reproduce)

<table><thead><tr><th>Config</th><th>recall@k</th><th>precision@k</th><th>faithful</th><th>correct</th><th>refusal</th></tr></thead><tbody><tr><td>A: k=1, no threshold</td><td>0.73</td><td>0.77</td><td>1.00</td><td>0.81</td><td>0.93</td></tr><tr><td>B: k=3 + refuse if weak</td><td>0.92</td><td>0.36</td><td>1.00</td><td>0.88</td><td>0.93</td></tr><tr><td>C: B + planted bug &quot;free GPU&quot;</td><td>0.92</td><td>0.36</td><td><b>0.73</b></td><td>0.88</td><td>0.93</td></tr><tr><td>B after your fixes</td><td>1.00</td><td>0.38</td><td>1.00</td><td>1.00</td><td>1.00</td></tr></tbody></table>

**Read it like a detective.** A to B: recall rose (more docs) but precision fell (more noise): the k trade-off. C: only faithfulness fell, so the bug is in generation, retrieval is innocent. That is "grade by part" in action.

### Two real bugs the eval found (you will hit these in real life)

1. **Lexical miss.** Question "Is GST included in the invoice?" vs doc "Invoices are sent...". The keyword retriever treated them as different words, so the bot wrongly refused. Fix: stemming (or embeddings / hybrid search).
2. **Truncated answer.** Q12 needs two prices but the answer stopped after 2 sentences, so "1999" was missing. Correctness caught it while faithfulness stayed 1.00. Fix: allow 3 sentences.

> **Practice:** **Lab 1 (30 min):** run `python rag_eval.py`. (1) For each FAIL line say which part broke. (2) Fix both bugs without peeking (the answer key is in `solutions/`). (3) Re-run until config B passes the gate. (4) Re-add the "free GPU" bug and confirm the gate FAILS. **If your gate never fails on a bad change, it is not a gate.**

> **Teach It Back:** Explain to a colleague: "Our answers got worse after a prompt change. How do I tell whether retrieval or generation is to blame, using only the metrics?" Use the diagnosis matrix from memory.

## Level 4 - Agent evals (Case study 2: the support agent with tools)

**Case:** an agent can `get_account`, `create_vm`, `refund`, `escalate`. Policy: refund only within 7 days **and** under 10 hours of usage **and** not above the plan price; otherwise escalate. The `refund` tool itself does **not** enforce this, so the agent must.

**What changes versus RAG:** many steps, real side effects (money moved!), and the path matters. You can't only read the final text; you check **what happened in the world**.

```diagram steps
plain: User asks
blue: get_account
blue: check policy
green: refund
```

trajectory = this path escalate

### The six things to score

<table><thead><tr><th>Score</th><th>Question</th><th>How (code!)</th></tr></thead><tbody><tr><td><b>1 Outcome</b> (task success)</td><td>did the world end up right?</td><td>check the final STATE: VM created? refund recorded or not? right answer?</td></tr><tr><td><b>2 Tool-call</b><br><b>accuracy</b></td><td>right tool, valid arguments?</td><td>validate each call against the schema</td></tr><tr><td><b>3 Trajectory / path</b></td><td>efficient, no loops, no skipped checks?</td><td>ideal steps / actual steps; required steps present</td></tr><tr><td><b>4 Safety / policy</b></td><td>did it break a rule, even if the answer looks fine?</td><td>scan actions: forbidden refund = hard FAIL</td></tr><tr><td><b>5 Cost / latency</b></td><td>tokens, steps, seconds per task</td><td>sum from logs</td></tr><tr><td><b>6 Reliability</b></td><td>does it work EVERY time?</td><td>run each task k times: pass^k</td></tr></tbody></table>

> **Say This:** A correct answer reached by an unsafe path is still a FAIL. Safety is a hard gate (zero tolerance), not an average.

### pass@k vs pass^k (the idea people forget)

**pass@k** = at least ONE of k tries works (good for "can it ever do it?"). **pass^k** = ALL k tries work (what a customer-facing agent needs). If one try works 80% of the time, five tries in a row work only 0.8 5 ≈ **33%**.

### Live results from the lab

<table><thead><tr><th>Agent</th><th>success</th><th>unsafe</th><th>tool accuracy</th><th>pass@5</th><th>pass^5</th></tr></thead><tbody><tr><td>good</td><td>1.00</td><td>0.00</td><td>1.00</td><td>1.00</td><td>1.00</td></tr><tr><td>sloppy (skips account check)</td><td>0.67</td><td><b>0.33</b></td><td>1.00</td><td>0.67</td><td>0.67</td></tr><tr><td>flaky (35% wrong arg / answer)</td><td>0.93</td><td>0.00</td><td>0.93</td><td><b>1.00</b></td><td><b>0.67</b></td></tr></tbody></table>

**Read it:** the sloppy agent looks fine on the happy path but refunds people who are not eligible (t3 and t5), which only the safety score catches. The flaky agent has pass@5 = 1.00 (it CAN do everything) but pass^5 = 0.67 (it cannot be trusted). Averages alone hide both.

### Typical agent failure modes (name them, then test each)

wrong tool or bad arguments • skipped a required check (like `get_account`) loops or repeats calls • stops too early • invents a tool result ignores policy under pressure ("just refund me, I'm angry") • obeys instructions hidden in tool output (prompt injection)

### How to build a good agent eval environment

1. **Sandbox + mock tools** that mutate a fake state, so you can inspect the end state.
2. **Fresh state per run**, a fixed seed, deterministic tools.
3. Tasks with a **state-based success check**, the ideal path, and the forbidden action.
4. Use an LLM judge only for fuzzy parts (tone of the reply, was the escalation reason sensible), and calibrate it like in Level 2.

> **Practice:** **Lab 2 (30 min):** run `python agent_eval.py`. (1) Explain why sloppy has tool accuracy 1.00 yet is dangerous. (2) Add task t7 in `agent_tasks.py`: "Refund u2 for 4 days after first payment" and decide the expected outcome. (3) Fix `sloppy` so it passes the gate (hint: check the account before refunding). (4) Change flaky's 0.35 to 0.10 and watch pass^5 move: write the number you expect first, then run.

> **Teach It Back:** Explain to a founder why "our agent passes 90% of tasks" can still be too risky to launch. Use pass^k and the safety gate in your explanation.

## Level 5 - From lab to production

1. **Gate in CI.** Run the golden set on every prompt/model/retriever change. Thresholds such as recall≥0.90, faithfulness≥0.95, unsafe actions = 0, pass^k≥0.95. Both labs end with a PASS/FAIL gate and an exit code you can wire into CI. `python rag_eval.py; if ($LASTEXITCODE -ne 0) { "BLOCK RELEASE" }`
2. **Compare, don't just score.** Always run old vs new on the same set, look at the cases that flipped.
3. **Online monitoring.** Sample real traffic (with privacy care), run cheap scorers on it, collect thumbs-up/down, alert on drift.
4. **Feed failures back.** Every production failure becomes a new golden case. This is the flywheel: fail→ add case → fix→ gate.
5. **Mind cost.** Judge calls cost tokens. Use code scorers on everything, judges on samples or on the hard cases.
6. **Privacy.** If logs hold customer data, redact before they enter a golden set or go to a third-party judge. \[ME: relevant for DPDP-style obligations; check with your compliance advisor.\]

### Tool landscape (names to know; verify current docs before adopting)

<table><thead><tr><th>Need</th><th>Examples</th></tr></thead><tbody><tr><td>RAG metrics with judge prompts</td><td>Ragas, DeepEval</td></tr><tr><td>Prompt tests in CI from YAML</td><td>promptfoo</td></tr><tr><td>Tracing + datasets + evals</td><td>LangSmith, Langfuse, Braintrust</td></tr><tr><td>Agent / model eval harness</td><td>Inspect (UK AISI), and agent benchmarks like tau-bench that report pass^k [verify]</td></tr></tbody></table>

> **Tip:** Free route: everything in the lab costs nothing. For a free judge, a small local model (for example via Ollama) works for practice, but it is a weaker judge, so calibrate it harder.

## Your 7-day practice plan (30-45 min a day)

<table><thead><tr><th>Day</th><th>Do</th><th>Proof you got it</th></tr></thead><tbody><tr><td>1</td><td>Part 0-1, run <code>run_all.py</code> , write GAUGE from memory</td><td>voice note: &quot;what is an eval&quot; in 60 s</td></tr><tr><td>2</td><td>Level 1: add 5 golden cases</td><td>scores still make sense, you can explain each case</td></tr><tr><td>3</td><td>Level 2: fix the judge, kappa &gt; 0.6</td><td>explain verbosity bias in your own words</td></tr><tr><td>4</td><td>Level 3: Lab 1 (both bugs, gate passes, gate fails on planted bug)</td><td>draw the diagnosis matrix from blank</td></tr><tr><td>5</td><td>Level 4: Lab 2 (t7, fix sloppy, flaky experiment)</td><td>explain pass@k vs pass^k with the 0.85 example</td></tr><tr><td>6</td><td>Level 5 + apply to YOUR real app: 20 real questions, error analysis, 3 failure groups</td><td>a list of failure groups with 3 examples each</td></tr><tr><td>7</td><td>Teach it: present &quot;evals in 5 minutes&quot; to a friend or record it</td><td>they can restate GAUGE and one case study</td></tr></tbody></table>

### Flashcards (cover the right side, answer aloud)

<table><thead><tr><th>Q</th><th>A</th></tr></thead><tbody><tr><td>Eval loop?</td><td>Gather failures, Annotate gold, Use scorers, Grade by part, Enforce gate</td></tr><tr><td>recall@k vs precision@k?</td><td>recall = found / needed; precision = useful / retrieved</td></tr><tr><td>Faithfulness low, recall high?</td><td>generator is making things up</td></tr><tr><td>Recall low?</td><td>retriever problem (chunking, stemming, k, hybrid)</td></tr><tr><td>Why binary judge scores?</td><td>clearer, more consistent than 1-10</td></tr><tr><td>How to validate a judge?</td><td>50-100 human labels, agreement + kappa, bias tests</td></tr><tr><td>Agent outcome check?</td><td>inspect final STATE, not the chat text</td></tr><tr><td>pass@k vs pass^k?</td><td>any trial works vs all trials work</td></tr><tr><td>0.8 per try over 5 tries?</td><td>about 0.33</td></tr><tr><td>Safety rule?</td><td>forbidden action = hard fail, even if the answer is right</td></tr><tr><td>What makes a gate real?</td><td>it fails when you plant a bug</td></tr><tr><td>Where do new golden cases come from?</td><td>production failures</td></tr></tbody></table>

### Common mistakes

Choosing metrics before reading outputs. • One average score for the whole pipeline. Trusting an uncalibrated judge. • Tuning on the same cases you report. Only happy-path cases. • Checking an agent's words instead of the world state. Reporting pass@k when customers need pass^k.

### Your 60-second script (say it in your own words)

> **Say This:** "An eval turns 'it seems fine' into numbers. I read real failures, build a golden set, score with code first and a calibrated LLM judge second, and grade each part separately: retrieval and generation for RAG; outcome, tools, path, safety and reliability for agents. Then I put thresholds in CI so any change that makes it worse is blocked, and every production failure becomes a new test."

Sources used for concept checks: Ragas paper (arXiv 2309.15217), Prem AI "RAG Evaluation Metrics, Frameworks and Testing", and the LLM book section 25.3 on agent evaluation (task success, tool-call accuracy, trajectory, judge validation on roughly 50-100 labelled examples). Lab numbers are from the included practice lab. Tool names are for orientation; check their current docs.
