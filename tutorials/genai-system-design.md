---
title: GenAI system design
group: System design
order: 1
blurb: From laptop prototype to production: the answer framework, five full designs and the 3 a.m. failure catalogue
tagline: from laptop prototype to production · scale · monitor · explain
about: For senior (10+ yrs) interviews — Oct 2026 · Frameworks · 5 full designs · failure catalogue · runnable labs (tested on mock models) · 20 Q&A
---

## How to use this tutorial

> **Say This:** A senior interviewer is not testing whether you know LangChain. They test whether you can take something that works in a demo and make it reliable, fast enough, affordable, safe and observable, and whether you can explain the trade-offs. Every answer below follows that shape.

<table><thead><tr><th>Section</th><th>You will be able to say</th></tr></thead><tbody><tr><td>1 Framework</td><td>&quot;Here is how I structure any GenAI design answer in 45 minutes.&quot;</td></tr><tr><td>2 Reference architecture</td><td>&quot;These are the boxes, and why each one exists.&quot;</td></tr><tr><td>3 Prototype to production</td><td>&quot;Here is why it worked on my laptop and what broke in prod.&quot;</td></tr><tr><td>4-8 Building blocks</td><td>latency, reliability, scale, RAG, agents, security, cost</td></tr><tr><td>9 Observability and evals</td><td>&quot;This is how I know it is healthy and not quietly wrong.&quot;</td></tr><tr><td>10 Capacity maths</td><td>&quot;On the back of an envelope, that is ~X QPS and ~$Y.&quot;</td></tr><tr><td>11 Five designs</td><td>RAG assistant, support agent, LLM gateway, batch pipeline, migration plan</td></tr><tr><td>12 Labs</td><td>things you ran yourself, with real outputs</td></tr><tr><td>13 Failures and Q&amp;A</td><td>the 3 a.m. stories and the model answers</td></tr></tbody></table>

> **Tip:** Tie each answer to your own 10+ years: databases, queues, caching, SRE, security, team leadership. GenAI design is ordinary distributed-systems design plus four new problems: **non-determinism, token cost, slow responses, and quality that can silently drift.**

## 1. The answer framework (use it every time)

```diagram steps
red: 1 Clarify | users, goal
red: 2 Require | func + SLOs
red: 3 Size | QPS, tokens
blue: 4 Draw | high level
blue: 5 Deep dive | 1-2 parts
green: 6 Harden | fail, safe
green: 7 Operate | watch, eval
```

### Questions to ask first (GenAI-specific)

<table><thead><tr><th>Ask</th><th>Why it changes the design</th></tr></thead><tbody><tr><td>Who uses it, how many, how often?</td><td>QPS, concurrency, cost</td></tr><tr><td>What counts as a good answer? Is a wrong answer costly (legal, medical, money)?</td><td>evals, human review, guardrails, model choice</td></tr><tr><td>Latency target? Chat feel or a background job?</td><td>streaming vs async, model size, caching</td></tr><tr><td>What data does it use? How fresh? Who may see what?</td><td>RAG design, access control, multi-tenancy</td></tr><tr><td>Can data leave our network?</td><td>hosted API vs self-hosted model</td></tr><tr><td>Budget per request or per month?</td><td>routing, caching, token limits</td></tr><tr><td>Does it take actions (tools) or only answer?</td><td>agent safety, approvals, idempotency</td></tr></tbody></table>

### Requirements template

```
Functional : ask questions over company docs, cite sources, remember the chat
Quality    : >= 90% correct on our test set, < 2% unsupported claims
Latency    : first token < 1.5 s, full answer p95 < 8 s
Availability: 99.9% (so we need fallback providers)
Cost       : < $0.01 per request on average
Security   : per-tenant data isolation, no PII in logs, injection-resistant
Scale      : 200k daily users, 5x peak
```

> **Say This:** Always state SLOs as numbers. "Fast" and "accurate" are not requirements; "p95 under 8 seconds" and "90% on the test set" are.

## 2. Reference architecture (memorise this picture)

```diagram grid
red: Cache | exact + semantic + prefix
blue: Retrieval | vector + keyword + rerank · ACL filter per tenant
blue: Tools / APIs | DB, search, ticketing
red: Client
blue: API gateway | auth, quotas · rate limit, WAF · request id
green: Orchestrator | stateless service · prompt build + routing · tool loop, retries · timeouts, streaming · input / output guardrails
red: API A
red: API B
red: LLM router | small model first · fallback provider
red: vLLM
blue: Session / DB | chat state, users
red: Queue + workers | long / batch jobs
blue: Config registry | prompts, models, flags
plain: Observability: traces · metrics · logs · cost · online evals · user feedback · alerts | watches every box above
```

<table><thead><tr><th>Box</th><th>Why it exists (the one-line reason)</th></tr></thead><tbody><tr><td>Gateway</td><td>one place for auth, per-user quotas, abuse control, request ids</td></tr><tr><td>Orchestrator</td><td>stateless so I can run N copies; owns prompts, retries, timeouts, guardrails</td></tr><tr><td>Cache</td><td>the cheapest and fastest answer is the one I do not generate again</td></tr><tr><td>Retrieval</td><td>fresh, private, citable facts instead of trusting model memory</td></tr><tr><td>LLM router</td><td>cost control and resilience: cheap model first, fallback on failure</td></tr><tr><td>Queue + workers</td><td>slow or bulk jobs must not hold HTTP connections</td></tr><tr><td>Config registry</td><td>change prompts and models without redeploying, and roll back</td></tr><tr><td>Observability</td><td>LLM bugs are quality bugs; without measurement you cannot see them</td></tr></tbody></table>

## 3. Why it works on my laptop but fails in production

> **Say This:** In a demo there is one user, a warm cache in your head, a happy-path prompt, a patient provider and no bill. Production has many users at once, bad inputs, slow and failing dependencies, hostile text, changing data, and a finance team.

<table><thead><tr><th>Laptop reality</th><th>Production reality</th><th>Fix</th></tr></thead><tbody><tr><td>One request at a time</td><td>hundreds in flight; provider returns 429 rate-limit errors</td><td>concurrency limit, queue, retry with backoff + jitter, quotas per user</td></tr><tr><td>No timeout, waits forever</td><td>one slow call ties up a worker; tail latency (p99) explodes</td><td>timeouts everywhere, streaming, fallbacks, circuit breaker</td></tr><tr><td>Provider always up</td><td>outages, degraded models, deprecations</td><td>second provider or model, health checks, pinned model versions</td></tr><tr><td>Prompt in a string in the code</td><td>prompt tweaks silently change behaviour</td><td>prompt versioning, eval gate in CI, canary release</td></tr><tr><td>You test five questions</td><td>users ask thousands of unexpected things</td><td>eval set from real logs, sampling reviews, user feedback</td></tr><tr><td>Docs loaded once</td><td>data changes, permissions differ per user</td><td>incremental ingestion, freshness checks, ACL filters</td></tr><tr><td>Keys in <code>.env</code></td><td>leaked keys, shared accounts</td><td>secret manager, rotation, per-service keys</td></tr><tr><td>Cost unnoticed</td><td>a loop or long context burns money overnight</td><td>token budgets, <code>max_tokens</code> , per-tenant spend caps, cost alerts</td></tr><tr><td>Trusted input</td><td>prompt injection, PII, data exfiltration</td><td>input/output guardrails, least-privilege tools, human approval</td></tr><tr><td>print() debugging</td><td>cannot reproduce a bad answer</td><td>traces with prompt, retrieved chunks, model, tokens, version</td></tr><tr><td>Agent loops forever</td><td>runaway tool calls and cost</td><td>max steps, wall-clock limit, idempotent tools, budgets</td></tr></tbody></table>

### The production-readiness checklist (say these out loud)

<table><thead><tr><th>Reliability</th><th>Quality</th><th>Safety</th><th>Operations</th></tr></thead><tbody><tr><td>timeouts<br>retries + jitter<br>circuit breaker<br>fallback model<br>backpressure<br>graceful degrade</td><td>offline eval set<br>CI gate<br>canary/A-B<br>online sampling<br>feedback loop<br>drift checks</td><td>input filters<br>output checks<br>PII redaction<br>least privilege<br>tenant isolation<br>audit log</td><td>traces + metrics<br>cost dashboard<br>alerts + runbooks<br>autoscaling<br>rollbacks<br>load tests</td></tr></tbody></table>

## 4. Latency: make it feel fast

LLM latency has two parts: **TTFT** (time to first token: queue + prompt processing) and **generation time** (roughly output tokens × time per token). Users forgive a long answer that starts quickly, so **stream**.

#### where the seconds go (example request)

auth retrieval rerank LLM queue + prefill (TTFTL)LM decoding (streamed tokens appear here) check

#### attack the biggest bars: parallelise, cache, shrink the prompt, use a smaller model, stream.

<table><thead><tr><th>Lever</th><th>How</th><th>Trade-off</th></tr></thead><tbody><tr><td><b>Streaming</b></td><td>send tokens as they come (SSE or WebSocket)</td><td>post-checks must work on partial output</td></tr><tr><td><b>Smaller model</b></td><td>route easy requests to an SLM</td><td>quality risk; needs routing + evals</td></tr><tr><td><b>Shorter prompts</b></td><td>fewer, better chunks; trim history; summarise</td><td>may lose context</td></tr><tr><td><b>Parallelism</b></td><td>run retrieval, tool calls and guardrails concurrently</td><td>more complex code</td></tr><tr><td><b>Prompt/prefix</b> <b>caching</b></td><td>reuse the processed static prefix (system prompt, docs) if the provider or server supports it</td><td>prefix must be identical; provider rules differ (verify)</td></tr><tr><td><b>Response caching</b></td><td>exact match, then semantic match</td><td>stale or wrong hits (see the cache lab)</td></tr><tr><td><b>Limit output</b></td><td><code>max_tokens</code> , concise instructions</td><td>truncated answers</td></tr><tr><td><b>Async for heavy</b> <b>work</b></td><td>return a job id, notify when done</td><td>UX change</td></tr></tbody></table>

### Caching layers (from cheapest to riskiest)

1. **Exact cache:** same normalised question + same context version gives the same stored answer. Safe, low hit rate.
2. **Prefix / prompt cache:** the model server reuses work on a shared prompt beginning. Safe, saves cost and TTFT.
3. **Semantic cache:** a similar question returns a stored answer. High hit rate, real risk of wrong answers. My lab shows "refund policy for the basic plan" matching the premium answer at similarity 0.91. Mitigate with high thresholds, scoping by tenant and product, short TTL, and skipping it for personalised or high-stakes questions.

> **Careful:** Cache keys must include everything that changes the answer: tenant, user permissions, prompt version, model version, and data version. Otherwise one tenant can see another tenant's answer.

## 5. Reliability: survive a flaky world

```diagram grid
red: request
blue: limit | concurrency
blue: breaker | open? skip
blue: timeout + | retry (jitter)
red: primary
green: fallback
note: cached / smal
```

<table><thead><tr><th>Pattern</th><th>What it does</th><th>Pitfall</th></tr></thead><tbody><tr><td><b>Timeout</b></td><td>cap waiting on any dependency</td><td>too long wastes workers, too short drops good answers</td></tr><tr><td><b>Retry + backoff +</b> <b>jitter</b></td><td>wait 0.5s, 1s, 2s (randomised) between tries</td><td>retries multiply load in an outage (retry storm); retry only safe, transient errors</td></tr><tr><td><b>Circuit breaker</b></td><td>after N failures, stop calling for a cooldown</td><td>must still probe to recover</td></tr><tr><td><b>Fallback</b></td><td>second provider, cheaper model, cached answer, or a polite refusal</td><td>behaviour differs; test the fallback regularly</td></tr><tr><td><b>Backpressure</b></td><td>reject early (HTTP 429/503 with Retry-After) instead of queueing forever</td><td>decide who gets priority</td></tr><tr><td><b>Idempotency key</b></td><td>repeating a request does not repeat its side effects</td><td>essential for tools that send email or move money</td></tr><tr><td><b>Graceful</b><br><b>degradation</b></td><td>if retrieval is down, answer from the base model with a disclaimer, or say so</td><td>never fake sources</td></tr></tbody></table>

> **Say This:** Tail latency rule: users feel p95 and p99, not the average. Reliability work is mostly about the tail.

## 6. Scaling the app and the model

### A. Scaling your service (the easy part)

Keep the orchestrator **stateless**; put chat state in Redis or a database. Then add replicas behind a load balancer and autoscale on **in-flight requests or queue depth**, not just CPU (LLM waiting is I/O, CPU stays low). Use **async I/O** so one worker holds many waiting requests. Limit concurrency per replica to protect memory and provider quota. **Little's law:** in-flight requests = QPS × latency. At 58 QPS and 8 s latency you hold about 460 requests open at once. Size connection pools and limits from that. Split **online** (chat) and **offline** (batch, ingestion, evals) workloads onto separate queues and workers so a big batch cannot starve users. **Provider limits** (requests and tokens per minute) are your real ceiling. Track them, request higher quota early, and spread across keys/regions/providers where terms allow.

### B. Scaling the model itself (when you self-host)

#### GPU memory = weights + KV cache (grows with each request) + overhead

<table><tbody><tr><td>weights (8B, fp16 = 16 GB)</td><td>KV cache: one slot per in-flight request</td><td>overhead</td></tr></tbody></table>

More concurrent users ⇒ more KV cache ⇒ out of memory. So:

- continuous batching: new requests join the running batch every step (vLLM, TGI)
- paged KV cache (PagedAttention) wastes less memory so more requests fit
- quantization, prefix caching, tensor parallelism across GPUs

**vLLM / PagedAttention:** the paper (Kwon et al., arXiv 2309.06180) says KV cache memory per request is huge and changes size, and that managing it like OS virtual-memory pages gives near-zero waste. The authors report 2- 4× higher throughput at the same latency versus systems such as FasterTransformer and Orca (their own results).

<table><thead><tr><th>Decision</th><th>Hosted API</th><th>Self-hosted</th></tr></thead><tbody><tr><td>Start-up effort</td><td>hours</td><td>weeks (GPUs, serving, on-call)</td></tr><tr><td>Cost shape</td><td>pay per token, grows with use</td><td>fixed GPU cost; cheaper only at high steady utilisation</td></tr><tr><td>Data control</td><td>provider terms apply</td><td>full control</td></tr><tr><td>Quality ceiling</td><td>frontier models</td><td>open models; often SLMs + fine-tuning</td></tr><tr><td>Reliability</td><td>provider SLA, rate limits</td><td>you own failures and scaling</td></tr></tbody></table>

> **Tip:** A sensible default story: start on a hosted API, add a gateway, measure traffic by task, then move the high-volume, narrow tasks to a self-hosted or small model once the numbers justify it.

## 7. RAG at production scale

#### Ingestion (offline, incremental)

```diagram grid
red: sources
blue: parse+clean
blue: chunk
blue: embed
green: index + metadata
note: tenant, ACL,
note: version, date
note: Query (online)
red: question
blue: rewrite
blue: hybrid search+ACL
blue: rerank
red: LLM + cite
green: check
note: Most "bad answers" are retrieval problems: wrong chunk, stale chunk, missing chunk, or a chunk the us
```

<table><thead><tr><th>Production issue</th><th>What to do</th></tr></thead><tbody><tr><td>Stale data</td><td>incremental ingestion by change events or hash; store source + version + timestamp; delete removed docs</td></tr><tr><td>Poor recall</td><td>hybrid search (keyword + vector), better chunking with overlap, query rewriting, reranker</td></tr><tr><td>Wrong tenant sees data</td><td>filter by tenant and ACL insidethe retrieval query, never after generation; test it as a security case</td></tr><tr><td>Index scale</td><td>approximate nearest-neighbour index (e.g. HNSW), shard by tenant or collection, replicas for read QPS</td></tr><tr><td>Embedding model change</td><td>re-embed everything into a new index, switch with an alias, keep the old index for rollback</td></tr><tr><td>Unsupported claims</td><td>cite chunks, ask the model to say &quot;not found&quot;, run a groundedness check (see my RAG evaluation notes)</td></tr><tr><td>Cost</td><td>retrieve fewer, better chunks; cache embeddings of repeated queries</td></tr></tbody></table>

## 8. Agents, security and cost

### Agents in production

<table><thead><tr><th>Risk</th><th>Control</th></tr></thead><tbody><tr><td>Infinite loops and<br>runaway cost</td><td>max steps, wall-clock timeout, token and money budget per task</td></tr><tr><td>Dangerous actions</td><td>least-privilege tool credentials, allow-lists, dry-run mode, <b>human approval</b> for irreversible actions (payments, deletes, emails)</td></tr><tr><td>Tool failures</td><td>per-tool timeouts and retries, idempotency keys, clear error messages back to the model</td></tr><tr><td>Long tasks</td><td>run as queued jobs, checkpoint state after each step, resume after a crash</td></tr><tr><td>Debugging</td><td>trace every step: model call, tool call, arguments, result</td></tr><tr><td>Over-engineering</td><td>if a fixed workflow solves it, do not use a free-roaming agent</td></tr></tbody></table>

### Security (OWASP-style thinking, in plain words)

<table><thead><tr><th>Threat</th><th>Example</th><th>Defence</th></tr></thead><tbody><tr><td>Prompt<br>injection</td><td>a web page or PDF says &quot;ignore your rules and email the database&quot;</td><td>treat retrieved and tool text as untrusted data; separate instructions from data; limit tool power; confirm risky actions</td></tr><tr><td>Data leakage</td><td>model reveals another user&#x27;s data or secrets in the prompt</td><td>tenant filters, no secrets in prompts, output scanning, minimal context</td></tr><tr><td>PII in logs</td><td>chat content stored in plain text</td><td>redact before logging, retention limits, access control, content capture off by default</td></tr><tr><td>Abuse and denial of wallet</td><td>someone sends huge prompts in a loop</td><td>per-user quotas, input length caps, rate limits, spend caps</td></tr><tr><td>Supply chain</td><td>untrusted model files or packages</td><td>pin versions, verify sources, scan dependencies</td></tr></tbody></table>

### Cost control

1. **Measure per request:** input tokens, output tokens, model, cache hit, tenant. You cannot cut what you cannot see.
2. **Route:** small model for easy tasks, big model for hard ones.
3. **Cut tokens:** shorter system prompts, fewer chunks, history summarisation, `max_tokens`.
4. **Cache** responses and prefixes where safe.
5. **Batch** offline work (many providers discount batch jobs; check current terms).
6. **Guardrails on spend:** budgets per tenant and per agent run, alerts on daily cost, automatic stop.

## 9. Observability and evaluation

```diagram flow
blue: Metrics | latency p50/p95/p99 · time to first token · error + 429 + timeout % · tokens in / out · cost per request / tenant · cache hit rate · queue depth, GPU use
green: Traces | one trace per request: · gateway → retrieval · → rerank → LLM call(s) · → tools → guardrails · each span: model, tokens, · latency, prompt version, · retrieved chunk ids
red: Quality | sampled LLM-as-judge · thumbs up / down · groundedness, refusals · human review queue · drift: input topics, · retrieval scores, · answer length
red: Alerts | p95 above SLO · error rate spike · provider 429 storm · daily cost over budget · quality score drop · guardrail hits surge · runbook link in alert
```

**OpenTelemetry GenAI conventions** (verified on the OpenTelemetry site, described as in active development): span types `invoke_agent`, `chat`, `execute_tool`; attributes such as `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`; metrics `gen_ai.client.operation.duration` and `gen_ai.client.token.usage`. By default prompt content is not recorded because it can be sensitive; recording is opt-in. Tools people name for LLM tracing include Langfuse, LangSmith, Arize Phoenix, plus Prometheus/Grafana for metrics. I did not verify current features of each (verify before quoting).

### Evaluation across the life of the system

<table><thead><tr><th>Stage</th><th>What you run</th><th>Gate</th></tr></thead><tbody><tr><td>Offline (dev)</td><td>golden set of 50-500 real cases with expected facts</td><td>score must not regress</td></tr><tr><td>CI</td><td>cheap subset on every prompt/model/retriever change</td><td>block the merge below threshold (lab 5)</td></tr><tr><td>Shadow</td><td>new version sees live traffic, answers are not shown, compare</td><td>no major regressions</td></tr><tr><td>Canary / A- B</td><td>1-5% of users on the new version</td><td>quality, latency, cost within bounds</td></tr><tr><td>Online</td><td>sample live traffic for judge scoring and human review; collect feedback</td><td>alerts on quality drop</td></tr></tbody></table>

> **Say This:** Version everything that can change an answer: prompt, model, retriever, index, guardrail rules. Record those versions in every trace so any bad answer is reproducible and any release is reversible.

## 10. Capacity maths (do it live on the whiteboard)

Example: 200,000 daily users, 5 requests each, peak 5× average, prompt 1,500 tokens (with retrieved context), answer 400 tokens, latency 8 s. Prices below are **placeholders**; always use the provider's current price list.

<table><thead><tr><th>Step</th><th>Formula</th><th>Result</th></tr></thead><tbody><tr><td>Requests/day</td><td>200,000 × 5</td><td>1,000,000</td></tr><tr><td>Average QPS</td><td>1,000,000 / 86,400</td><td>11.6</td></tr><tr><td>Peak QPS</td><td>11.6 × 5</td><td>57.9</td></tr><tr><td>Tokens/day</td><td>in 1,500M, out 400M</td><td>1.9B</td></tr><tr><td>Cost/day (placeholder $1 / $4 per 1M tokens)</td><td>1,500×1 + 400×4</td><td>$3,100 (~$93k/month, $0.0031 per request)</td></tr><tr><td>In-flight at peak (Little&#x27;s law)</td><td>57.9 × 8 s</td><td>~463</td></tr><tr><td>KV cache per token (example 8B model: 32 layers, 8 KV heads, head dim 128, fp16)</td><td>2 × 32 × 8 × 128 × 2 bytes</td><td>128 KB</td></tr><tr><td>KV per request (1,900 tokens)</td><td>128 KB × 1,900</td><td>238 MB</td></tr><tr><td>Sequences per 80 GB GPU</td><td>(80 − 16 weights − 8<br>overhead) GB / 238 MB</td><td>~241</td></tr></tbody></table>

That last line is memory only; real capacity is also bounded by compute throughput, so load-test before promising a GPU count. Run `capacity.py` in the labs to change the numbers yourself.

> **Tip:** What to say next: "At this volume cost dominates. I would add caching, route 60-70% of easy requests to a small model, and cut context tokens, then re-run the numbers." Showing the second pass of the maths is what impresses.

## 11. Five full designs

### Design 1 - Enterprise RAG assistant (multi-tenant)

<table><thead><tr><th>Part</th><th>Choice</th></tr></thead><tbody><tr><td>Goal</td><td>employees ask questions over internal documents with citations</td></tr><tr><td>Flow</td><td>gateway (SSO, quotas) → orchestrator → query rewrite → hybrid retrieval with tenant + ACL filter → rerank → LLM with cited chunks → groundedness check → stream answer</td></tr><tr><td>Data</td><td>ingestion workers on change events; chunks carry tenant, ACL, doc version, timestamp</td></tr><tr><td>Scale</td><td>stateless orchestrator autoscaled on in-flight requests; vector index sharded by tenant; read replicas</td></tr><tr><td>Reliability</td><td>timeouts, fallback model, &quot;no answer found&quot; path, retrieval-down degrade</td></tr><tr><td>Watch</td><td>retrieval hit rate, groundedness score, thumbs, p95, cost per tenant</td></tr><tr><td>Trade-off to name</td><td>stricter citation checks raise quality but add latency</td></tr></tbody></table>

### Design 2 - Customer-support agent with tools

<table><thead><tr><th>Part</th><th>Choice</th></tr></thead><tbody><tr><td>Flow</td><td>classify intent (small model) → FAQ via RAG, or tool path (order lookup, refund) → human handoff when confidence is low or the action is sensitive</td></tr><tr><td>Safety</td><td>tools use read-only credentials by default; refunds above a limit need human approval; idempotency keys; full audit log</td></tr><tr><td>State</td><td>conversation and case state in a database; agent steps checkpointed</td></tr><tr><td>Limits</td><td>max 8 steps, 30 s budget, per-conversation token cap</td></tr><tr><td>Success<br>metrics</td><td>resolution rate, escalation rate, customer rating, cost per resolved ticket</td></tr></tbody></table>

### Design 3 - Internal LLM gateway / platform for many teams

<table><thead><tr><th>Part</th><th>Choice</th></tr></thead><tbody><tr><td>Why</td><td>stop every team re-implementing keys, retries, logging and budgets</td></tr><tr><td>Features</td><td>one API, per-team keys and quotas, model routing and fallback, central logging with PII redaction, caching, cost showback, policy checks, prompt/model registry</td></tr><tr><td>Hard<br>parts</td><td>being a single point of failure (run it highly available), latency overhead (keep it thin), differing provider APIs (a common interface), governance without blocking teams</td></tr><tr><td>Metrics</td><td>gateway overhead ms, availability, spend per team, fallback rate</td></tr></tbody></table>

### Design 4 - Batch document pipeline (1M documents/day)

<table><thead><tr><th>Part</th><th>Choice</th></tr></thead><tbody><tr><td>Why async</td><td>no user is waiting; throughput and cost matter more than latency</td></tr><tr><td>Flow</td><td>object storage → queue → workers (parse, small-model extract to JSON schema, validate) → failures to a retry queue, then a dead-letter queue → database</td></tr><tr><td>Quality</td><td>schema validation, confidence checks, human review of a sample and of low-confidence items</td></tr><tr><td>Cost</td><td>smallest model that passes the eval; batch discounts; skip documents already processed (idempotent by content hash)</td></tr><tr><td>Capacity idea</td><td>1M/day is about 12 docs/second; with 10 s per doc that is ~120 workers in flight</td></tr></tbody></table>

### Design 5 - Moving a working prototype to production (your story)

<table><thead><tr><th>Phase</th><th>Do</th></tr></thead><tbody><tr><td>Week 1: Measure</td><td>build a golden set from real questions, add tracing and token/cost logging, load test to find the first break</td></tr><tr><td>Week 2: Harden</td><td>timeouts, retries, backpressure, fallback, secrets manager, input/output guardrails, containerise, CI with the eval gate</td></tr><tr><td>Week 3: Scale</td><td>stateless deploy, autoscaling on in-flight requests, caching, move state to Redis/DB, separate batch from online</td></tr><tr><td>Week 4: Release safely</td><td>shadow, then 5% canary, dashboards and alerts with runbooks, rollback plan, then ramp up</td></tr><tr><td>Ongoing</td><td>weekly review of failures and costs, update golden set, retrain or re-prompt, security review</td></tr></tbody></table>

## 12. Labs - run these yourself (Windows PowerShell)

All five run with a **mock model**, so no API key, cost or GPU. I ran each and the outputs shown are real.

```powershell
mkdir $HOME\sd-lab
cd $HOME\sd-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn httpx
```

### Lab 1 - Retries, circuit breaker and fallback

`@' import random, time`

`class RateLimited(Exception): pass class Timeout(Exception): pass`

`class FakeLLM: """Pretend provider: fails often, like a busy API.""" def __init__(self, fail_rate, rng): self.fail_rate, self.rng = fail_rate, rng def call(self, prompt): r = self.rng.random() if r < self.fail_rate / 2: raise RateLimited("429") if r < self.fail_rate: raise Timeout("timeout") return "ok"`

`class Breaker: """Open after N straight failures; stay open for cooldown seconds.""" def __init__(self, threshold=5, cooldown=30): self.threshold, self.cooldown = threshold, cooldown self.fails, self.opened_at = 0, None def allow(self, now): if self.opened_at is None: return True if now - self.opened_at >= self.cooldown: # half-open: let one try through self.opened_at = None; self.fails = 0; return True return False def record(self, ok, now): if ok: self.fails = 0 else: self.fails += 1 if self.fails >= self.threshold: self.opened_at = now`

`def call_with_retry(llm, now_fn, sleep_fn, rng, retries=3, base=0.5): for attempt in range(retries + 1): try: return llm.call("hi"), attempt except (RateLimited, Timeout): if attempt == retries: raise sleep_fn(base * 2 ** attempt * rng.uniform(0.5, 1.5)) # exponential backoff + jitter`

`def run(use_retry, use_fallback, n=2000, seed=1): rng = random.Random(seed) clock = [0.0] now = lambda: clock[0] def sleep(s): clock[0] += s primary, backup = FakeLLM(0.30, rng), FakeLLM(0.02, rng) # primary is flaky, backup is calm br = Breaker() ok = fb = 0 for _ in range(n): clock[0] += 0.05 try: if use_fallback and not br.allow(now()): raise RuntimeError("breaker open") if use_retry: call_with_retry(primary, now, sleep, rng)`

```bash
            else: primary.call("hi")
            if use_fallback: br.record(True, now())
            ok += 1
        except Exception:
            if use_fallback:
                br.record(False, now())
                try: backup.call("hi"); ok += 1; fb += 1
                except Exception: pass
    return ok / n, fb
for label, r, f in [("no protection", False, False), ("retry only", True, False),
                    ("retry + breaker + fallback", True, True)]:
    rate, fb = run(r, f)
    print(f"{label:28} success {rate*100:5.1f}%   served by fallback: {fb}")
'@ | Set-Content resilience.py
python resilience.py
```

Output:

```
no protection                success  70.8%   served by fallback: 0
retry only                   success  99.5%   served by fallback: 0
retry + breaker + fallback   success 100.0%   served by fallback: 11
```

> **Tip:** Story to tell: a provider failing 30% of the time looks like 71% success with no protection and about 99.5% with retries. Add a breaker and a calm fallback and users effectively never see it. Experiment: raise `FakeLLM(0.30` to `0.90` and watch retries alone collapse while the fallback saves you.

### Lab 2 - Exact vs semantic cache (and its danger)

```python
@'
import math, re
from collections import Counter
def vec(text): return Counter(re.findall(r"[a-z0-9]+", text.lower()))
def cos(a, b):
    dot = sum(a[k] * b.get(k, 0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values())); nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0
class Cache:
    def __init__(self, threshold=0.8): self.exact, self.items, self.t = {}, [], threshold
    def get(self, q):
        key = " ".join(q.lower().split())
        if key in self.exact: return "EXACT HIT", self.exact[key]
        v = vec(q)
        best = max(self.items, key=lambda it: cos(v, it[0]), default=None)
        if best and cos(v, best[0]) >= self.t: return f"SEMANTIC HIT ({cos(v, best[0]):.2f})",
best[1]
        return "MISS", None
    def put(self, q, ans):
        self.exact[" ".join(q.lower().split())] = ans; self.items.append((vec(q), ans))
c = Cache(0.8)
c.put("What is the refund policy for the premium plan?", "Premium: 30-day refund.")
for q in ["what is the refund policy for the premium plan?",
          "Tell me the refund policy for the premium plan",
          "What is the refund policy for the basic plan?",
          "How do I reset my password?"]:
    kind, ans = c.get(q)
    print(f"{kind:22} | {q} -> {ans}")
'@ | Set-Content cache.py
python cache.py
EXACT HIT              | what is the refund policy for the premium plan? -> Premium: 30-day refund.
SEMANTIC HIT (0.82)    | Tell me the refund policy for the premium plan -> Premium: 30-day refund.
SEMANTIC HIT (0.91)    | What is the refund policy for the basic plan? -> Premium: 30-day refund.
MISS                   | How do I reset my password? -> None
```

> **Careful:** Line 3 is a wrong answer served at similarity 0.91. This toy uses word overlap, but real embedding caches have the same failure on near-identical questions with different key words. Scope caches by product/tenant and use high thresholds.

### Lab 3 - Capacity calculator

```bash
@'
# Back-of-envelope sizing. Prices are PLACEHOLDERS: put your provider's current numbers in.
DAU = 200_000
REQ_PER_USER = 5
PEAK_FACTOR = 5                      # peak QPS vs average
IN_TOK, OUT_TOK = 1500, 400          # prompt (with RAG context) and answer, per request
PRICE_IN_PER_M, PRICE_OUT_PER_M = 1.0, 4.0     # USD per 1M tokens (placeholder)
req_day = DAU * REQ_PER_USER
avg_qps = req_day / 86400
peak_qps = avg_qps * PEAK_FACTOR
tok_day_in, tok_day_out = req_day * IN_TOK, req_day * OUT_TOK
cost_day = tok_day_in / 1e6 * PRICE_IN_PER_M + tok_day_out / 1e6 * PRICE_OUT_PER_M
print(f"requests/day {req_day:,} | avg QPS {avg_qps:.1f} | peak QPS {peak_qps:.1f}")
print(f"tokens/day in {tok_day_in/1e6:,.0f}M out {tok_day_out/1e6:,.0f}M")
print(f"cost/day ${cost_day:,.0f}  cost/month ${cost_day*30:,.0f}  per request
${cost_day/req_day:.4f}")
# Concurrency by Little's law: in-flight = QPS x latency
LAT_S = 8.0
print(f"in-flight requests at peak: {peak_qps*LAT_S:.0f}  (QPS x {LAT_S}s latency)")
# Self-hosting KV cache (example config: 32 layers, 8 KV heads, head_dim 128, fp16)
layers, kv_heads, head_dim, bytes_ = 32, 8, 128, 2
kv_per_token = 2 * layers * kv_heads * head_dim * bytes_
ctx = IN_TOK + OUT_TOK
kv_per_seq = kv_per_token * ctx
print(f"KV cache per token {kv_per_token/1024:.0f} KB | per request ({ctx} tok)
{kv_per_seq/2**20:.0f} MB")
gpu_gb, weights_gb, overhead_gb = 80, 16, 8         # example 80 GB GPU, 8B model in fp16
free = (gpu_gb - weights_gb - overhead_gb) * 2**30
seqs = int(free // kv_per_seq)
print(f"concurrent sequences per GPU (memory bound): ~{seqs}")
print(f"GPUs for peak in-flight: ~{-(-int(peak_qps*LAT_S)//seqs)}  (memory view only; throughput may
bind first)")
'@ | Set-Content capacity.py
python capacity.py
```

Edit the numbers at the top (users, tokens, latency, placeholder prices, GPU size) and discuss how each changes cost and GPUs.

## 12b. Labs continued - a production-style service

### Lab 4 - A small API with timeout, backpressure, request ids, metrics and streaming

`@' import asyncio, json, logging, time, uuid from fastapi import FastAPI, Request from fastapi.responses import JSONResponse, StreamingResponse`

`logging.basicConfig(level=logging.INFO, format="%(message)s") log = logging.getLogger("svc") app = FastAPI() MAX_CONCURRENT, LLM_TIMEOUT_S = 2, 1.0 slots = asyncio.Semaphore(MAX_CONCURRENT) metrics = {"requests": 0, "ok": 0, "timeouts": 0, "rejected": 0, "latency_sum": 0.0}`

`async def fake_llm(prompt: str, delay: float) -> str: await asyncio.sleep(delay) # pretend the model is thinking return f"answer to: {prompt}"`

`@app.middleware("http") async def request_id(request: Request, call_next): rid = request.headers.get("x-request-id", str(uuid.uuid4())[:8]) t0 = time.time() resp = await call_next(request) resp.headers["x-request-id"] = rid log.info(json.dumps({"rid": rid, "path": request.url.path, "status": resp.status_code, "ms": round((time.time() - t0) * 1000)})) return resp`

`@app.get("/healthz") def healthz(): return {"ok": True}`

`@app.get("/metrics") def get_metrics(): return metrics`

`@app.get("/chat") async def chat(q: str, delay: float = 0.1): metrics["requests"] += 1 if slots.locked(): # backpressure: refuse instead of queueing forever metrics["rejected"] += 1 return JSONResponse({"error": "busy, retry later"}, status_code=429, headers={"Retry-After": "1"}) async with slots: t0 = time.time() try: ans = await asyncio.wait_for(fake_llm(q, delay), timeout=LLM_TIMEOUT_S) except asyncio.TimeoutError: metrics["timeouts"] += 1 return JSONResponse({"error": "model timeout", "fallback": "Sorry, try again."}, status_code=504) metrics["ok"] += 1; metrics["latency_sum"] += time.time() - t0 return {"answer": ans}`

`@app.get("/stream") async def stream(q: str): async def gen(): for word in f"streamed answer to {q}".split(): yield f"data: {word}\n\n" await asyncio.sleep(0.05) yield "data: [DONE]\n\n"`

```bash
    return StreamingResponse(gen(), media_type="text/event-stream")
'@ | Set-Content service.py
uvicorn service:app --port 8000
```

Open a second PowerShell window in the same folder, activate the venv, then:

```python
Invoke-RestMethod "http://localhost:8000/chat?q=hello"
Invoke-RestMethod "http://localhost:8000/metrics"
@'
import httpx, concurrent.futures as cf, collections, time
URL = "http://localhost:8000/chat"
def hit(i):
    r = httpx.get(URL, params={"q": f"q{i}", "delay": 0.5}, timeout=10)
    return r.status_code
t0 = time.time()
with cf.ThreadPoolExecutor(10) as ex:
    codes = list(ex.map(hit, range(10)))
print(dict(collections.Counter(codes)), f"in {time.time()-t0:.1f}s")
'@ | Set-Content load.py
python load.py
Invoke-RestMethod "http://localhost:8000/metrics"
```

What I saw with 10 parallel callers and a limit of 2:

```json
{200: 2, 429: 8} in 1.0s
{"requests":10,"ok":2,"timeouts":0,"rejected":8,"latency_sum":1.0013089179992676}
```

<table><thead><tr><th>Feature in the code</th><th>Interview point</th></tr></thead><tbody><tr><td><code>Semaphore</code> + 429 with <code>Retry-After</code></td><td>backpressure: refuse early rather than collapse</td></tr><tr><td><code>asyncio.wait_for</code> + 504 with fallback text</td><td>timeouts and graceful degradation</td></tr><tr><td>middleware with <code>x-request-id</code> and JSON log line</td><td>correlation and structured logs</td></tr><tr><td><code>/metrics</code> counters</td><td>the seed of real metrics (use Prometheus/OpenTelemetry in production)</td></tr><tr><td><code>/stream</code> server-sent events</td><td>streaming improves perceived latency</td></tr><tr><td><code>/healthz</code></td><td>load balancer and orchestrator health checks</td></tr></tbody></table>

Try it: change the `delay` query value to `2`: `Invoke-RestMethod "http://localhost:8000/chat? q=slow&delay=2"` raises an HTTP 504 (PowerShell shows an error), because the 1-second timeout fired. Replace `fake_llm` with a real client later; the protections stay the same. In PowerShell 5.1 use `try { ... } catch { $_.Exception.Response.StatusCode }` to see status codes.

### Lab 5 - Evaluation gate for CI

```python
@'
import sys
CASES = [("2+2", "4"), ("capital of France", "Paris"), ("refund window premium", "30 days"),
("opening hours", "9-5")]
def my_app(q):                      # replace with a call to your real pipeline
    return {"2+2": "4", "capital of France": "Paris", "refund window premium": "14 days", "opening
hours": "9-5"}[q]
passed = sum(expected.lower() in my_app(q).lower() for q, expected in CASES)
rate = passed / len(CASES)
print(f"pass rate {rate:.0%} ({passed}/{len(CASES)})")
THRESHOLD = 0.9
if rate < THRESHOLD:
    print("GATE FAILED: block the release"); sys.exit(1)
print("GATE OK")
'@ | Set-Content eval_gate.py
python eval_gate.py; echo "exit code: $LASTEXITCODE"
```

```
pass rate 75% (3/4)
GATE FAILED: block the release
exit code: 1
```

The "app" gives a stale 14-day refund answer, so the gate fails. Put this in a pipeline step and a bad prompt or data change cannot ship silently. Replace `my_app` with your real pipeline and grow the case list from real user questions.

> **Say This:** I can show you working pieces: resilience, caching with its risk, capacity maths, a hardened API, and an eval gate. They run on a mock model, but the architecture is the same one I would put in front of a real provider.

## 13. The 3 a.m. failure catalogue

<table><thead><tr><th>Symptom</th><th>Likely cause</th><th>Detect</th><th>Fix / prevent</th></tr></thead><tbody><tr><td>Wave of 429/timeouts</td><td>provider rate limit or outage; retry storm</td><td>error-rate and 429 alerts</td><td>backoff + jitter, breaker, fallback, quota increase, queue</td></tr><tr><td>p99 latency jumps</td><td>long prompts, slow provider, GPU queue</td><td>latency by model and prompt size</td><td>timeouts, shorter context, route to smaller model, scale</td></tr><tr><td>Bill doubles overnight</td><td>agent loop, huge contexts, abuse, cache miss</td><td>cost per hour alert, tokens per request</td><td>budgets, max steps, quotas, caps</td></tr><tr><td>&quot;It started giving wrong answers&quot;</td><td>prompt/model change, stale index, bad ingestion</td><td>online quality score, eval on versions</td><td>version pinning, canary, rollback</td></tr><tr><td>Answers cite old policy</td><td>ingestion lag or deleted docs still indexed</td><td>freshness metric, doc version in trace</td><td>incremental sync, deletes, TTL</td></tr><tr><td>User sees another tenant&#x27;s data</td><td>missing ACL filter or shared cache key</td><td>security tests, audit log</td><td>filter in query, tenant in cache key, incident process</td></tr><tr><td>Agent emailed the wrong people</td><td>injected instruction, over- powered tool</td><td>tool-call audit</td><td>approval step, least privilege, allow-lists</td></tr><tr><td>Out-of-memory on GPU</td><td>too many concurrent long sequences</td><td>GPU memory, queue depth</td><td>limit concurrency and context, paged KV cache, add GPUs</td></tr><tr><td>Streaming cuts off</td><td>proxy buffering or idle timeout</td><td>client errors by path</td><td>proxy settings, heartbeats</td></tr><tr><td>JSON output breaks parser</td><td>model ignores format</td><td>parse-failure rate</td><td>structured output mode, validation + one repair retry</td></tr></tbody></table>

> **Say This:** For any incident: detect, mitigate (flip a flag, switch model, roll back), find root cause, add a test or alert so it cannot recur, and write a blameless postmortem.

## 14. Interview Q&A (model answers)

**Q1. Design a RAG chatbot for 10,000 employees.** Clarify quality, latency, security. Then: gateway, stateless orchestrator, hybrid retrieval with ACL filter, reranker, LLM with citations, groundedness check, streaming, cache, tracing. Size QPS and tokens, then discuss freshness, multi-tenancy and evals. Close with trade-offs.

**Q2. Your app works locally but fails in production. Why?** Concurrency, rate limits, no timeouts, provider failures, cost, unseen inputs, stale data, security. I would add measurement first (traces, golden set), then harden (timeouts, retries, breaker, fallback), then scale and release safely (canary, rollback).

**Q3. How do you reduce latency?** Stream; shorten prompts; parallelise retrieval and tools; cache (prefix, exact, careful semantic); route to smaller models; limit output; make heavy tasks async. Measure TTFT and p95 per stage first.

**Q4. How do you handle provider rate limits and outages?** Client-side concurrency limits, queue, retry with exponential backoff and jitter, circuit breaker, fallback provider/model, quota planning, backpressure with 429 and Retry-After to my own callers.

**Q5. How do you control cost?** Measure tokens and cost per request/tenant; route by difficulty; trim context; cache; batch offline; budgets and alerts; set `max_tokens`; stop runaway agents.

**Q6. How do you monitor an LLM app?** Classic SRE metrics plus LLM specifics: tokens, TTFT, cost, cache hit, per-step traces with prompt and model versions, sampled quality scoring, user feedback, drift and guardrail alerts.

**Q7. How do you know a change did not make it worse?** Golden set with an automated CI gate, then shadow and canary on live traffic, comparing quality, latency and cost, with versioned prompts so I can roll back.

**Q8. Hosted API or self-host?** Start hosted for speed. Self-host when data control, steady high volume, or cost justify GPU operations. Often a hybrid: frontier model for hard tasks, self-hosted small model for narrow high-volume ones.

**Q9. What is continuous batching and why does it matter?** The server adds new requests to the running batch at each decoding step instead of waiting for a whole batch to finish, which raises GPU utilisation. Together with paged KV cache (vLLM) it increases throughput; the paper reports 2-4× at similar latency.

**Q10. How do you secure it against prompt injection?** Assume retrieved and tool content is hostile. Keep instructions separate, minimise tool permissions, require approval for irreversible actions, filter outputs, test with adversarial cases, and log tool calls.

**Q11. How do you build multi-tenant RAG safely?** Tenant and ACL metadata on every chunk, filter inside the vector query, include tenant in cache keys, test isolation explicitly, audit access.

**Q12. Chat or batch: sync or async?** Humans waiting: stream over HTTP/SSE. Long or bulk: return a job id, process in queues with retries and dead-letter handling, notify on completion.

**Q13. What goes in a trace?** Request id, user/tenant (hashed if needed), each span's model, prompt version, tokens, latency, retrieved chunk ids, tool calls, guardrail results. Prompt text only when policy allows.

**Q14. Semantic cache: good or bad?** Powerful but risky: similar is not the same. Use for low-stakes FAQs with high thresholds, scoped keys and short TTL; skip personalised or critical answers; monitor false-hit complaints.

**Q15. How do you scale to 10x?** Recompute the maths; autoscale stateless services on in-flight load; raise provider quotas or add providers; cache and route more traffic to small models; shard the index; add GPUs with continuous batching if self-hosted; load-test before launch.

**Q16. Agent vs fixed workflow?** Workflow when steps are known: cheaper, predictable. Agent when the path depends on intermediate results; add step, time and cost limits and approvals.

**Q17. How do you handle hallucinations in production?** Retrieval with citations, "I don't know" behaviour, groundedness checks, constrained outputs, human review for high-stakes cases, and measurement via the evaluation set and online sampling.

**Q18. How would you roll out a new model version?** Offline eval, shadow, 1-5% canary with automatic rollback triggers, ramp up, keep the previous version warm for fast revert.

**Q19. What is your biggest design principle for GenAI systems?** Treat the model as an unreliable, expensive, slow dependency: wrap it with limits, measurement, fallbacks and evaluation, and keep deterministic code around it wherever possible.

<table><thead><tr><th>Verified</th><th>Not verified / do yourself</th></tr></thead><tbody><tr><td>OpenTelemetry GenAI span and metric names (from the OpenTelemetry blog). vLLM PagedAttention claims (from the arXiv abstract, authors&#x27; own results). The five labs ran with mock models and the outputs are real. The capacity arithmetic ran in <code>capacity.py</code> .</td><td>I did not test against a real LLM provider, real GPUs, a real vector database, Kubernetes or production traffic. Prices are placeholders. Provider features (prompt caching rules, batch discounts, rate limits) and observability tool features change; check current docs. Rules of thumb (thresholds, canary percentages, timeouts) are starting points to tune, not standards. Windows PowerShell 5.1 shows HTTP errors as exceptions.</td></tr></tbody></table>

**Q20. How does your 10-year background help here?**

Fill in your own story: for example, "I have run services with queues, caches, databases and on-call; GenAI adds new failure modes, so I reused those habits (SLOs, backpressure, observability, safe releases) and added evals and guardrails." Add one real project of yours with numbers.

Honesty page

Sources: arxiv.org/abs/2309.06180 (PagedAttention / vLLM); opentelemetry.io/blog/2026/genai-observability (GenAI conventions); the labs in this file.
