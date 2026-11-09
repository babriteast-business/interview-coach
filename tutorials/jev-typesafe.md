---
title: Jev by TypeSafe AI
group: RAG & evals
order: 6
blurb: The model that does not write, it decides: a ticket router and judge
tagline: the model that does not write — it decides
about: Support-ticket router + judge, one real story comes with an offline lab (simulated) and exact real-API code for when you get a key
---

## How to use this tutorial

**Your approach (levels → real case → practice → explain it back) is right,** and Jev needs it because it is a different kind of model. Four tweaks:

1. **Learn the idea, not the product.** Jev is days-old (first public release in Sep 2026, early access). Names and prices will change. The idea will not: use a fast model for small structured decisions, and use its confidence to decide who handles the hard ones.
2. **Trust levels.** Every claim below is tagged: \[official\] from TypeSafe's own docs/blog, \[paper\] the CMU study, \[3rd\] Arize / HoneyHive articles, \[mock\] my offline simulation, \[ME\] my reasoning. Vendor numbers are marketing until you test on your data.
3. **One story all the way:** Gravrel Cloud's support inbox. Same tickets in every level, so you feel one journey.
4. **Practice offline first (free, instant), live later** with your own key. Then teach it back.

> **Careful:** **Honest status.** I read TypeSafe's blog and docs, the CMU paper and two third-party articles. I could **not** call real Jev (no key, paid API). The lab uses `mock_jev.py`: it copies Jev's response shape and the documented confidence formulas with a keyword scorer. Its numbers prove the **pattern**, never how good Jev is. `live/` holds the official quickstart code, syntax-checked only.

### Setup (PowerShell)

```powershell
cd C:\Users\god
Expand-Archive LLM_JEV_Practice_Lab.zip -DestinationPath jev
cd jev\lab
python run_all.py        # offline, free, no account
```

> **Tip:** **Cycle per level (30 min):** read → run the script → do the PRACTICE box → close the page and explain aloud from blank.

## The big picture: System One vs System Two

Psychologist Kahneman: **System 1** = fast gut call. **System 2** = slow reasoning. TypeSafe borrows this \[official\] . LLMs write long text token by token (slow, flexible). **Jev is a "System One model"**: you give it a **state** (text or data) and **typed questions**; it returns **typed answers with probabilities**. It cannot write sentences.

> **Say This:** **Kitchen picture:** an LLM is a chef who can cook anything but takes 20 minutes. Jev is the person at the counter who looks at an order and instantly says "kitchen A, urgent, 90% sure". You don't ask him to cook. You ask him to **decide**.

<table><thead><tr><th></th><th>LLM</th><th>Jev (as described)</th></tr></thead><tbody><tr><td><b>Output</b></td><td>free text (then you parse it)</td><td>fixed types: choice / score / yes-no, with probabilities</td></tr><tr><td><b>Speed</b></td><td>seconds to minutes</td><td>vendor: 70–500 ms end to end [official]</td></tr><tr><td><b>Price</b></td><td>input $0.20–$10 per million tokens, output ~5x</td><td>input $0.042 per million tokens; output free [official]</td></tr><tr><td><b>Explains</b><br><b>itself?</b></td><td>can write a reason</td><td>no explanation [3rd]</td></tr><tr><td><b>Best at</b></td><td>chat, coding, open tasks</td><td>classify, route, score, extract, verify [official]</td></tr></tbody></table>

```diagram grid
plain: STATE (ticket)
blue: questions | Choice Score Noul
blue: JEV
green: typed answers + | probabilities
plain: REMEMBER: state + typed questions → typed answers + probabilities. | No prose.
```

> **Teach It Back:** **(30 s)** "Why can a decision model be 100x cheaper than an LLM for routing a ticket?" (Hint: no long text to generate, output is a small fixed type.)

\[ME\] The "100x" is vendor speed/cost claims for decision-shaped work (40–200x faster, 40–400x cheaper \[official\] ). Do not repeat it as fact; say "TypeSafe claims".

## Level 1: the three question types (primitives)

Every question you ask Jev is one of three kinds \[official docs\] . You can send several in one request; each is answered independently against the same state.

<table><thead><tr><th>Type</th><th>You ask</th><th>You get back</th><th>Gravrel example</th></tr></thead><tbody><tr><td><b>Choice</b></td><td>pick 1 option (up to 255)</td><td><code>choice</code> , <code>probabilities</code> , <code>confidence</code></td><td>department = billing / technical / sales</td></tr><tr><td><b>Score</b></td><td>rate on 2–10 ordered levels</td><td><code>score</code> (0–1), probabilities, confidence</td><td>frustration: calm / annoyed / angry</td></tr><tr><td><b>Noul</b></td><td>yes/no</td><td><code>noul</code> = probability of yes (no confidence field)</td><td>is_urgent?</td></tr></tbody></table>

### The real call (official quickstart, I did not run it)

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient
with TypeSafeClient(model="jev-latest") as client:   # reads TYPESAFE_API_KEY
    r = client.system_one(state=ticket, questions={
      "department": Choice(instructions="Which team should handle this",
          criteria={"billing":"Payment or subscription issues",
                    "technical":"Bugs or integration problems",
                    "sales":"Pricing or account questions"}),
      "frustration": Score(instructions="How frustrated the customer appears",
          criteria=["Calm","Frustrated but civil","Very angry"]),
      "is_urgent": Noul(instructions="The message conveys urgency"),
    })
print(r.choices["department"].choice)
```

### What comes back (raw API: POST https://api.typesafe.ai/v1/systemone)

```
"department": {"type":"choice","choice":"technical","confidence":1.0,
               "probabilities":{"technical":1.0,"billing":0.0,"sales":0.0}}
"frustration":{"type":"score","score":0.67,"confidence":0.5,"probabilities":{...}}
"is_urgent":  {"type":"noul","noul":0.99}
"usage":      {"input_tokens":428,"output_tokens":73}
```

> **Practice:** **Lab 1 (15 min):** run `python p01_shape.py`. (1) Find the choice, its probabilities and confidence for each ticket. (2) Notice the second ticket ("server down AND charged") is less sure. Say why in one sentence.

3. Answer the printed question: why is confidence not equal to the top probability?

> **Teach It Back:** Name the 3 question types and give one Gravrel example of each, without looking.

## Level 2: confidence, the superpower

Because Jev returns **probabilities**, it can say "I'm not sure". This is what lets you build safe automation. \[official docs\] define confidence (0 to 1) from the probabilities:

<table><thead><tr><th>Type</th><th>Formula (docs)</th></tr></thead><tbody><tr><td>Choice, n options</td><td><code>(p_max − 1/n) / (1 − 1/n)</code></td></tr><tr><td>Score</td><td>1 minus spread-from-top-level (nearby levels hurt less than far ones)</td></tr><tr><td>Noul</td><td>none; optional <code>|2p − 1|</code> (0 at p=0.5)</td></tr></tbody></table>

> **Say This:** **Worked example:** 3 departments, top probability 0.50. Confidence = (0.50 − 0.333)/(0.667) = **0.25**, not 0.5. Because 0.333 is already random guessing. Confidence measures how far above guessing.

### Three zones (the docs' routing idea)

```diagram steps
red: LOW: do not act | human / ask / fallback
plain: MEDIUM: careful | confirm / gather more
green: HIGH: auto-act | no human needed
```

0 ----------------- confidence ----------------- 1 **CAREFUL: Careful (important):** the docs make **no calibration promise** for confidence ("0.8 does not mean right 80% of the time"). The 0.5 and 0.9 numbers in the docs are **examples**. You must pick thresholds by measuring on your own tickets \[official\] . Thresholds should grow with risk: refunding money needs a higher bar than tagging a ticket \[ME\] .

> **Practice:** **Lab 2 (30 min):** run `python p02_router.py` \[mock\] . (1) Read the table: as the floor rises, auto-handled share falls and accuracy rises. That is the **coverage vs accuracy trade**. (2) Find the one confident-but-WRONG ticket and explain why it fooled the model (it mentions both billing and server). (3) Choose the floor you would use if wrong refunds cost real money. (4) Add 3 tickets in `tickets.py` and re-run.

> **Key idea:** confidence is for routing, not a guarantee. Measure thresholds on your data.

> **Teach It Back:** Explain "coverage vs accuracy" to a shop owner using a cashier who calls the manager only when unsure.

## Level 3: the real-world case study (Gravrel support inbox)

**Problem:** Gravrel gets 2,000 tickets a month. A person reads each one, picks a team, guesses urgency. Slow at night, inconsistent, costs time.

**Design with Jev \[ME\]:** one Jev call per ticket with 3 questions. Then plain code (not AI) applies business rules.

```diagram grid
green: auto-route + tag
plain: new ticket
blue: JEV x3 Q
plain: your code: | confidence gate
plain: agent confirms
red: human queue
```

```
dept = r.choices["department"]
if dept.confidence < 0.5:          route = "HUMAN"          # unsure
elif is_urgent > 0.9 and angry:    route = "PRIORITY " + dept.choice
else:                              route = dept.choice       # auto
```

<table><thead><tr><th>Ticket (invented)</th><th>What should happen</th></tr></thead><tbody><tr><td>&quot;API 500 errors, production down, urgent&quot;</td><td>technical, urgent, very high confidence → auto, priority</td></tr><tr><td>&quot;Server down AND I was charged for downtime&quot;</td><td>two teams plausible → mock gave <b>billing 0.76 (wrong!)</b>; in real life send to human or split ticket</td></tr><tr><td>&quot;Card payment failed but money deducted&quot;</td><td>billing + money at stake → require higher bar before auto-refund</td></tr></tbody></table>

> **Say This:** **Cost math (arithmetic I did):** a 428-token ticket costs 428 × $0.042 / 1,000,000 ≈ **$0.000018**. 1 million such tickets ≈ **$18** at the quoted price. Output is free. \[price is vendor-stated, may change.\]

> **Practice:** **Lab 3 (30 min):** write on paper (no code): for 3 actions (tag, route, auto-refund) choose a confidence floor each and justify with cost of a wrong action. Then in `p02_router.py` try your floors and check what share goes to humans.

> **Teach It Back:** "Why is the business rule in code, not in the model?" (Answer idea: rules must be predictable and auditable; Jev only supplies the judgment.)

## Level 4: accept when confident, escalate when unsure

Jev is not always right, so pair it with a stronger, slower model. **Let Jev answer when confident; send the doubtful ones to the big LLM.** A CMU study did exactly this for judging answers \[paper, arXiv 2609.26550\] .

<table><thead><tr><th>Finding (paper)</th><th>Number</th></tr></thead><tbody><tr><td>Cascade: accepted by Jev at threshold 0.9</td><td>53.7% of 510 pairs</td></tr><tr><td>Cascade accuracy vs big model alone</td><td>92.5% vs 93.1%</td></tr><tr><td>Cost of cascade vs big model alone</td><td>56.8%</td></tr><tr><td>Jev alone on a hard set (JudgeBench)</td><td>78.6% vs 93.1% big model</td></tr><tr><td>Jev alone on RM-Bench hard</td><td>74.8% vs 94.6%</td></tr><tr><td>Prose with no reference answer</td><td>confidence near chance (AUROC 0.518): gating does not help</td></tr></tbody></table>

> **Careful:** **Read this twice:** Jev alone was **much worse on hard cases**. The win came from the **cascade**, not from replacing the big model. Also: one hosted Jev version, one annotator checked disagreements, thresholds partly tuned after seeing data. Authors are from CMU, not TypeSafe, but they tested TypeSafe's service.

> **Practice:** **Lab 4 (30 min):** run `python p03_cascade.py` \[mock\] . (1) Read the cost column: higher threshold means more escalation, more accuracy, more cost. (2) The script **assumes** the big model is perfect. Edit `slow_llm` to be wrong 1 time in 10 and see how the best threshold changes. (3) State the sweet spot in one sentence.

> **Key idea:** Jev for the easy 50–80%, big LLM for the doubtful rest. Measure both.

> **Teach It Back:** Explain the hospital triage nurse analogy for the cascade, then say what the paper's warning is.

## Level 5: Jev as an evaluator (links to your Evals notes)

In your Evals notes you used an LLM judge. Jev can play judge with cheap **yes/no (Noul)** checks on each answer: "Did the reply address the request?" "Is it clear?" "Shows empathy?" \[3rd, HoneyHive\] gave an example where a reply scored request-addressed 0.10, clear 0.78, empathy 0.04: three separate checks show which behaviour to fix.

<table><thead><tr><th>Do</th><th>Why</th></tr></thead><tbody><tr><td>Many small yes/no checks, combine in code</td><td>multi-step or double-negative questions are less reliable</td></tr><tr><td>Pin a model version (e.g. a numbered one), not <code>jev-latest</code></td><td>latest changes on release; your scores would drift</td></tr><tr><td>Send only the relevant part of the trace</td><td>less noise, cheaper</td></tr><tr><td>Validate against human labels first; look at disagreements both ways</td><td>a judge you never checked is a guess</td></tr><tr><td>Put 0.4–0.6 band to human review</td><td>that is where it is unsure</td></tr></tbody></table>

> **Careful:** **Limits \[3rd\] :** no explanations; poor at exact counting/dates; injected text in the input can steer it (test before using as a guardrail); cannot discover new failure types (do human error analysis first); cannot verify events missing from the input ("I transferred you" is not proof).

**Evidence from Arize \[3rd\] :** on 18,514 spam emails zero-shot Jev scored 98.3% vs 98.4% for a trained classifier; emails under 0.1 were 0.1% spam; 0.9+ were 99.9% spam; the 0.5–0.6 band was 38% spam. Sending the 4.6% scored 0.3– 0.7 to humans left the rest at 99.5%. Arize also called "cannot hallucinate" an overreach: it can still be wrong inside its allowed answers. Their results were early and partly vendor-reported.

> **Practice:** **Lab 5 (25 min):** run `python p04_judge.py` \[mock\] . (1) Find the reply sent to HUMAN (p=0.50). (2) Find the line marked DISAGREES WITH HUMAN: the mock was fooled by a polite sentence containing "refund". Explain how that could happen to a real judge. (3) Add 4 replies of your own with human labels and compute agreement.

> **Teach It Back:** "Why validate a judge against human labels before trusting it?" Use the disagreement you found.

## Level 6: when to use, when NOT to use, and myths

<table><thead><tr><th>Use Jev-style decisions</th><th>Use an LLM instead</th></tr></thead><tbody><tr><td>classify / route / score / extract a field</td><td>write a reply, summary, code</td></tr><tr><td>real-time (≈100 ms) and high volume</td><td>open-ended reasoning, tool-using agents</td></tr><tr><td>verify / judge / jailbreak check at scale</td><td>need a written reason for an auditor</td></tr><tr><td>need probabilities to route to humans</td><td>prototype where you don&#x27;t know the question yet</td></tr></tbody></table>

### Myths vs reality

**"It can't hallucinate."** Official: it cannot produce an invalid format (type-safe). It can still pick the wrong option. Arize called the broader claim an overreach \[official vs 3rd\] . **"It's just a small LLM."** TypeSafe says it is a new model class (parallel sampling, trained with RL for calibrated decisions) \[official\] . I could not verify the internals independently; the technical FAQ on training data/benchmarks had no answer text in what I fetched. **"Confidence 0.9 = 90% right."** No. Docs make no such promise. **"Cheaper means replace everything."** The CMU paper shows hard cases still need the big model.

**Known limits \[official\] :** no string output; choice up to 255 options (more uses two stages and can be slower); request up to 64k tokens \[3rd\] ; early access via waitlist.

> **Teach It Back:** Give me a 3-row table of "use Jev / use LLM / use both" for tasks in your own Gravrel Cloud business.

## Go live, 7-day plan, flashcards, 60-second script

### Go live (when you have a key)

```powershell
pip install typesafe-sdk                 # Python 3.10+
$env:TYPESAFE_API_KEY = "your-key"       # PowerShell
python live\live_01_quickstart.py
python live\live_02_route_with_gate.py
```

Then replace the 24 sample tickets with 100 of your own with correct labels, rerun the floor table from Lab 2, and choose thresholds from **your** table.

### 7-day plan (30–40 min a day)

<table><thead><tr><th>Day</th><th>Do</th><th>Proof you got it</th></tr></thead><tbody><tr><td>1</td><td>Parts 0–1</td><td>explain System One vs LLM aloud</td></tr><tr><td>2</td><td>Part 2 + Lab 1</td><td>name 3 types from memory</td></tr><tr><td>3</td><td>Part 3 + Lab 2</td><td>draw the 3 zones and the trade</td></tr><tr><td>4</td><td>Part 4 + Lab 3</td><td>design the ticket flow on paper</td></tr><tr><td>5</td><td>Part 5 + Lab 4</td><td>explain cascade and the paper&#x27;s warning</td></tr><tr><td>6</td><td>Part 6 + Lab 5</td><td>list 3 judge pitfalls</td></tr><tr><td>7</td><td>Parts 7–8, record yourself</td><td>60-second script without notes</td></tr></tbody></table>

<table><tbody><tr><td>Flashcards</td></tr><tr><td><b>Q</b></td><td><b>A</b></td></tr><tr><td>What goes in / out of Jev?</td><td>state + typed questions → typed answers + probabilities</td></tr><tr><td>Three question types?</td><td>Choice, Score, Noul</td></tr><tr><td>Choice confidence?</td><td>(p_max − 1/n)/(1 − 1/n): how far above guessing</td></tr><tr><td>Is confidence a calibrated probability?</td><td>No promise in the docs; tune on your data</td></tr><tr><td>What does the cascade do?</td><td>Jev when confident, big LLM when not</td></tr><tr><td>Biggest warning from the CMU paper?</td><td>Jev alone drops a lot on hard cases</td></tr><tr><td>Why pin the model version?</td><td><code>latest</code> changes; scores drift</td></tr><tr><td>Cannot do?</td><td>write text, explain, exact maths, verify missing events</td></tr></tbody></table>

Your 60-second script

> **Say This:** "Jev from TypeSafe AI is a decision model, not a text writer. I give it some data and a few typed questions, like which team, how angry, is it urgent, and it answers instantly with probabilities and a confidence. I use that confidence as a gate: confident answers run automatically, doubtful ones go to a stronger model or a human. A study from CMU found a cascade like that kept about 99% of a big model's accuracy at roughly 57% of the cost, but Jev alone was much weaker on hard cases, so I never let it work unchecked. I test thresholds on my own labelled tickets and I pin the model version."

**Sources:** TypeSafe blog "Introducing System One Models & Jev" (15 Sep 2026); docs.typesafe.ai quickstart and confidence pages; deepeval.com TypeSafe integration; arXiv 2609.26550 (CMU); HoneyHive and Arize blogs on Jev as a judge. **Verified by me:** the offline lab runs (mock, not real Jev); cost arithmetic. **Not verified:** any real Jev call, accuracy on your data, internals, pricing beyond vendor statement, current model names. Check docs before relying on any number.
