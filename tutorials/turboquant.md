---
title: TurboQuant
group: Models & training
order: 8
blurb: Shrink the numbers, keep the meaning, measured on your own laptop
tagline: shrink the numbers, keep the meaning
about: Rotate, round with the best codebook, fix the bias; measured on your own laptop a small educational re-build of the idea, with honest labels on what is paper, press, and my simulation
---

## How to use this tutorial

**TurboQuant is research-level, so the way to own it is to shrink real numbers yourself and measure the damage.** Four tweaks:

1. **Problem before trick.** Level 1 shows why an LLM's "memory of the chat" (the KV cache) fills a GPU. Then the trick has a reason to exist.
2. **Baseline first.** You quantize with a plain method, see it fail on outliers, then fix it step by step: rotate, best codebook, bias fix. Each step is measured.
3. **Trust levels on every claim:** \[paper\] arXiv 2504.19874, \[press\] Google's blog as reported by others (I could not open the blog itself), \[critic\] an independent arXiv study, \[lab\] my numpy simulation, \[ME\] my reasoning.
4. **Real scenario:** your own GPU server (an A40-class card, 48 GB) and "how many users fit".

> **Careful:** **What is tested, honestly.** I read the paper (arXiv listing and full text summary), a Wikipedia summary, a math explainer, and an independent study. I wrote `tq_core.py`, a **small educational numpy re-implementation** of the steps the paper describes. It is **not Google's code**, uses **synthetic data**, and 7 tests pass. My lab numbers match the paper's theory (see Level 4/5), but they say nothing about speed on a GPU or accuracy on real LLMs. For those I only quote the paper, labelled.

> **Careful:** **Two things I could not verify:** (1) Google's own blog page was not reachable for me, so "6x memory" and "8x faster on H100" are \[press\] only. (2) I found conflicting hints about a conference venue, so I name none; the arXiv listing says preprint, v1.

### Setup (PowerShell, 3 min)

```powershell
cd C:\Users\god
Expand-Archive TurboQuant_Practice_Lab.zip -DestinationPath tq
cd tq\lab
python -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
pytest -q test_all.py           # expect: 7 passed
```

> **Tip:** **Cycle per level (20-30 min):** read → run the file → do the TASK box → close the page and explain aloud.

## The big picture: what is TurboQuant?

**Quantization = storing numbers with fewer bits.** Like writing 3.14159 as 3.1: smaller, slightly wrong. A vector (a list of numbers, such as one token's "key" in an LLM or one document's embedding) can be shrunk the same way. The art is shrinking a lot while keeping the **geometry** (distances and dot products) almost intact.

> **Say This:** **Photo analogy:** shrinking a photo. A bad method blurs the faces. A smart method first rearranges the pixels so that no single bright spot ruins the compression, then compresses evenly.

<table><thead><tr><th>Fact</th><th>Source</th></tr></thead><tbody><tr><td>Authors: Amir Zandieh, Majid Daliri, Majid Hadian, Vahab Mirrokni (Google Research, NYU, Google DeepMind)</td><td>paper listing /<br>Wikipedia</td></tr><tr><td>arXiv 2504.19874, submitted 28 Apr 2025, one version, 25 pages</td><td>paper</td></tr><tr><td>Title: &quot;TurboQuant: Online Vector Quantization with Near-optimal Distortion Rate&quot;</td><td>paper</td></tr><tr><td>Google Research blog post dated 24 Mar 2026; wide press in Mar 2026</td><td>press (Wikipedia)</td></tr></tbody></table>

### The recipe in one picture

```diagram steps
plain: vector x | (spiky)
blue: 1 random | rotation
blue: 2 round each value | with a best codebook
green: 3 (optional) 1-bit | bias fix: QJL
plain: small code
```

<table><thead><tr><th>Word</th><th>Meaning</th></tr></thead><tbody><tr><td><b>Online / data-oblivious</b></td><td>needs no training or calibration data; each vector is compressed on arrival [paper]</td></tr><tr><td><b>KV cache</b></td><td>the saved keys and values of every earlier token, so an LLM need not recompute them</td></tr><tr><td><b>Distortion (MSE)</b></td><td>how far the shrunk vector is from the original</td></tr><tr><td><b>Bits per channel</b></td><td>bits stored for each number in the vector</td></tr></tbody></table>

> **Teach It Back:** **(30 s)** Explain quantization with the photo analogy, then say what "keep the geometry" means.

## Level 1: why compress? Memory maths (`t01_memory_math.py`)

An LLM keeps keys and values for every token of every user. Per token: `2 (K and V) × layers × KV-heads × head-size × bytes`. For a Llama-3.1-8B-style shape (32 layers, 8 KV heads, head size 128 \[general knowledge, check the model card\]) in 16-bit: **128 KiB per token**.

```bash
python t01_memory_math.py
```

**Real output (my arithmetic) for a 48 GB GPU, 16 GB of weights, 32k context per user, 10% kept free:**

<table><thead><tr><th>Cache format</th><th>per user</th><th>users that fit</th></tr></thead><tbody><tr><td>16-bit</td><td>4.00 GiB</td><td><b>6</b></td></tr><tr><td>4-bit</td><td>1.00 GiB</td><td>27</td></tr><tr><td>3.5-bit</td><td>0.88 GiB</td><td>31</td></tr><tr><td>2.5-bit</td><td>0.62 GiB</td><td>43</td></tr></tbody></table>

One user with 128k tokens in 16-bit needs **16 GiB** for the cache alone. This is why a cheaper cache means more users per GPU: a direct business lever for a cloud company like Gravrel \[ME\].

> **Careful:** Rough planning numbers: they ignore per-vector norms, activations and fragmentation. Fewer bits never means "free"; it means more users if quality holds. That "if" is the rest of these notes.

> **Practice:** **Tasks (15 min):** (1) Run it. (2) Change the GPU to 24 GB and the context to 8192; how many users now? (3) Put your own model's layers/heads in (find them on its model card). (4) Compute by hand the compression ratio of 3.5-bit vs 16-bit (answer 16/3.5 ≈ 4.6x) and of 2.5-bit (≈ 6.4x). Note: the paper says "at least 4.5x" \[paper\] ; press says "at least 6x" \[press\] . Which bit setting would each correspond to?

> **Teach It Back:** Explain to a startup founder why the KV cache, not the model weights, limits how many users share one GPU for long chats.

## Level 2: the plain quantizer and why outliers hurt (`t02_baseline.py`)

The simplest quantizer: find the min and max of the vector, split that range into `2^bits` equal steps, round each number to a step.

```bash
python t02_baseline.py
```

<table><thead><tr><th>Data</th><th>2-bit error</th><th>3-bit</th><th>4-bit</th></tr></thead><tbody><tr><td>well-behaved</td><td>0.253</td><td>0.046</td><td>0.010</td></tr><tr><td>spiky (4 channels 12x bigger)</td><td><b>1.227</b></td><td>0.216</td><td>0.047</td></tr></tbody></table>

Error = `||x - x'||² / ||x||²` (relative). Above 1.0 means the shrunk vector is **worse than just storing zeros**. \[lab, real run\]

> **Say This:** **Why:** one huge value stretches the min-max range, so all the small values fall into just 1-2 steps and get crushed. Real LLM keys often have a few big "outlier channels" \[general knowledge, and the reason many methods treat outliers specially\].

> **Practice:** **Tasks (15 min):** (1) Run it. (2) Change `outlier_scale` in `make_spiky` to 2, then 30; plot or write the 3-bit error each time. (3) Predict: with 0 outlier channels, is more rotation needed? (Look at Level 3.) (4) Explain in one sentence why error above 1.0 is possible.

> **Key idea:** Min-max steps + one outlier = everything else gets crushed.

> **Teach It Back:** Explain the outlier problem with a class photo where one person stands in a bright spotlight.

## Level 3: the rotation trick (`t03_rotation.py`)

**Idea:** multiply every vector by the same random rotation. Rotation does not change lengths or dot products, so no information is lost, but it **spreads a spike across all coordinates**, making them look like an even bell curve.

```bash
python t03_rotation.py
```

**Real output \[lab\]:**

<table><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody><tr><td>norm and dot product kept</td><td>1.000000; -0.604433 vs -0.604433 (identical)</td></tr><tr><td>peak / typical value</td><td>12.7 before, 7.3 after</td></tr><tr><td>inside one vector: std of its rotated coordinates (after ×√d)</td><td>0.996 (≈ 1, Gaussian-like)</td></tr><tr><td>kurtosis of rotated values</td><td>2.95 (Gaussian = 3)</td></tr><tr><td>theory [paper]</td><td>each coordinate of a random unit vector ≈ N(0, 1/d); for d=128 that is 0.088</td></tr></tbody></table>

> **Careful:** **A subtle truth the lab shows:** the guarantee is "for a fixed vector, over the random choice of rotation". With one fixed rotation applied to structured data, a single coordinate watched across many vectors still varies (std from 0.56 to 1.76 in my run). The independent study \[critic\] makes a related point: the nice marginal shape does not guarantee everything about the joint structure (it found low-rank keys are a hard case). So rotation is powerful, not magic.

> **Practice:** **Tasks (20 min):** (1) Run it. (2) Change the seed of the rotation: do the numbers change much? (3) Apply the rotation twice (`R@R`): still norm-preserving? (4) Make data with outliers only in channel 0 and compare the peak ratio. (5) Say: why must the same rotation be used for stored vectors and for the query?

> **Key idea:** Rotation = same lengths, same dot products, but spikes spread out into an even bell curve.

> **Teach It Back:** Explain rotation with a flashlight beam hitting a wall from a new angle: the shape is the same, the bright spot is smeared.

## Level 4: the best codebook for a bell curve (`t04_lloyd_max.py`)

After rotation every value follows a known bell curve, so we can design, once and for all, the **best set of 2 b rounding values** (a "codebook") for that curve. This is the **Lloyd-Max quantizer**: put levels where the data is dense. Two rules, repeated until stable: (a) each boundary sits at the midpoint of neighbouring levels; (b) each level sits at the average of the values in its zone.

```bash
python t04_lloyd_max.py
```

<table><thead><tr><th>Bits</th><th>Levels</th><th>My MSE (N(0,1))</th><th>Paper&#x27;s value [paper]</th></tr></thead><tbody><tr><td>1</td><td>2 (±0.798)</td><td>0.3634</td><td>≈ 0.36</td></tr><tr><td>2</td><td>4</td><td>0.1175</td><td>≈ 0.117</td></tr><tr><td>3</td><td>8</td><td>0.0345</td><td>≈ 0.03</td></tr><tr><td>4</td><td>16</td><td>0.0095</td><td>≈ 0.009</td></tr></tbody></table>

The 1-bit centroid is ±√(2/π) = 0.7979 (matches the paper's note). Evenly spaced grids on the same bell curve are clearly worse (2-bit: 0.1895 vs 0.1175; 3-bit: 0.0481 vs 0.0345) \[lab\].

> **Say This:** **Each extra bit cuts error about 4x** (0.36 → 0.117 → 0.035 → 0.0095). That "4-b" shape is also in the paper's theory: the best any method can do is about 4-b, and TurboQuant's upper bound is about 2.7 times that

> **Practice:** **Tasks (20 min):** (1) Run it. (2) Print all 8 centroids for 3 bits and confirm they are symmetric and denser near 0. (3) Compute the ratio of errors between successive bits: is it about 3-4? (4) Change `iters` to 5 and see how close the result gets (converges quickly?). (5) Say why storing the codebook costs almost nothing (it is computed once per bit-width and shared by all vectors).

> **Teach It Back:** Explain Lloyd-Max with a bus-stop analogy: where would you put 4 bus stops on a street where most people live in the middle?

## Level 5: assemble TurboQuant (MSE version) (`t05_turboquant_mse.py`)

**Steps (as in the paper) \[paper\] :** (1) store the vector's length; (2) divide by it so length = 1; (3) multiply by the random rotation; (4) replace each coordinate by the index of its nearest codebook level (b bits each); to **decode**: look up levels, rotate back, multiply by the stored length.

```bash
python t05_turboquant_mse.py
```

**Real output on spiky vectors \[lab\] (relative error, lower is better):**

<table><thead><tr><th>bits</th><th>plain uniform</th><th>TurboQuant (mine)</th><th>theory</th></tr></thead><tbody><tr><td>1</td><td>14.89</td><td><b>0.359</b></td><td>0.363</td></tr><tr><td>2</td><td>1.240</td><td><b>0.116</b></td><td>0.1175</td></tr><tr><td>3</td><td>0.215</td><td><b>0.034</b></td><td>0.0345</td></tr><tr><td>4</td><td>0.047</td><td><b>0.009</b></td><td>0.0095</td></tr></tbody></table>

The error of the rotated-and-Lloyd-Max pipeline sits right on the theoretical curve even for spiky data, while the plain method is 5-40x worse. That is the whole "near-optimal" idea in numbers. **Data-oblivious** means I never trained anything on this data.

> **Careful:** **Cost the "b bits" hides \[paper limitations\] :** the vector's length is stored as a float and is not counted; the paper also notes it did not use entropy coding. And my dense rotation costs d² operations per vector: real systems need a fast structured rotation \[ME / the independent study uses a Walsh-Hadamard transform\]. I did not measure speed.

> **Practice:** **Tasks (25 min):** (1) Run it. (2) Try `d=64` and `d=512`: does it still match theory? (Paper: it is best for larger d.) (3) Quantize, then compute the dot product of a stored vector with a query and compare with the true one. (4) Count total bytes for 100k vectors of d=1536 at 3 bits including a 4-byte norm each, versus float32.

5. Say what "online" buys you: new vectors arrive and need no retraining.

> **Key idea:** TurboQuant-MSE = store length, rotate, round each value with the Lloyd- Max codebook, rotate back to decode.

> **Teach It Back:** Explain the 4 steps of encode and 3 of decode to a friend without any maths words.

## Level 6: the bias problem and the 1-bit fix (`t06_bias_qjl.py`)

Attention in an LLM is built from **dot products** (query · key). A quantizer that minimises squared error can still be **biased** for dot products: on average it gives a smaller answer than the truth. The paper shows that at 1 bit the estimate shrinks by a factor of 2/π \[paper\] .

```bash
python t06_bias_qjl.py
```

<table><thead><tr><th>Method (1 bit each)</th><th>mean estimate / truth</th><th>spread (std)</th></tr></thead><tbody><tr><td>MSE quantizer</td><td><b>0.638</b> (paper: 2/π = 0.637)</td><td>-</td></tr><tr><td>QJL sign sketch only</td><td>0.997</td><td>0.095</td></tr><tr><td>TurboQuant_prod: (b-1) bits MSE + 1 bit QJL of the residual</td><td><b>0.999</b></td><td>0.071</td></tr></tbody></table>

True mean dot product was 0.699 \[lab\]. **QJL** (quantized Johnson-Lindenstrauss): multiply the leftover error (the "residual") by a random matrix and keep only the **signs** (1 bit each) plus its length. Because `E[sign(g·e)·(g·q)] = √(2/π)·(q·e)/||e||`, scaling by √(π/2) removes the bias \[math explainer + paper\] .

> **Say This:** **Plain words:** first compress the vector as best you can. Then look at what you got wrong (the residual), and spend one more bit per number on a cheap sign-based sketch of that mistake. The sketch is noisy but **correct on average**, so dot products stop being systematically too small.

> **Careful:** **Does it help in practice? Opinions differ.** An independent simulation study \[critic\] argues QJL on the **keys** raises variance (at least π/2) and that softmax amplifies it, so under an equal bit budget plain MSE bits on keys can be better, with QJL more useful on values. It is a simulation, partly heuristic, by a single author. So: the fix is mathematically sound, whether it is the best use of a bit in every setting is **still debated**.

> **Practice:** **Tasks (25 min):** (1) Run it. (2) Repeat with 2-bit MSE: is the bias smaller? (paper: it shrinks as b grows). (3) Use `d=64` and compare the spread. (4) Run the experiment with a different QJL seed: does the mean stay near 1? (5) In one sentence: "unbiased" does not mean "every estimate is right"; what does it mean?

> **Teach It Back:** Explain "biased but low error" versus "unbiased but noisy" using a weighing scale that always reads 36% light versus one that jitters but averages right.

## Level 7 and 8: attention and vector search (`t07_attention_sim.py`, `t08_vector_search.py`)

### Level 7: does it change what the model attends to? [lab, synthetic keys, NOT a real LLM]

```bash
python t07_attention_sim.py
```

<table><thead><tr><th>bits</th><th>uniform: KL / same top token</th><th>TurboQuant: KL / same top token</th></tr></thead><tbody><tr><td>2</td><td>3.199 / 7%</td><td><b>0.159 / 27%</b></td></tr><tr><td>3</td><td>0.338 / 18%</td><td><b>0.048 / 55%</b></td></tr><tr><td>4</td><td>0.062 / 51%</td><td><b>0.014 / 78%</b></td></tr></tbody></table>

KL measures how different the attention weights become (0 = identical). Lower is better. Even at 4 bits only 78% of queries keep the same most-attended token on this hard spiky toy; real models behave differently, so read this as direction, not as a promise.

### Level 8: vector search [lab, synthetic clusters]

```bash
python t08_vector_search.py
```

<table><thead><tr><th>bits (vs float32)</th><th>uniform recall@10</th><th>TurboQuant recall@10</th></tr></thead><tbody><tr><td>2 (16x smaller)</td><td>0.247</td><td><b>0.449</b></td></tr><tr><td>3 (11x)</td><td>0.443</td><td><b>0.645</b></td></tr><tr><td>4 (8x)</td><td>0.674</td><td><b>0.789</b></td></tr></tbody></table>

Recall@10 = share of the true top-10 neighbours still found in the compressed copy. These recalls are modest because my toy data is noisy; sizes exclude the stored norms.

> **Practice:** **Tasks (30 min):** (1) Run both. (2) In Level 7 raise `n_tokens` to 2048: do the numbers hold? (3) In Level 8 reduce the noise from 0.6 to 0.3 (easier data) and see recall rise. (4) Combine: search the compressed DB, then re-rank the top-50 candidates with exact vectors; measure recall@10. (This "compress then re-rank" pattern is common in practice \[general\].) (5) Write a 3-line summary of when you would still keep 16-bit.

> **Teach It Back:** Explain recall@10 to a librarian who must find the 10 best books but only looks at tiny thumbnails of the covers.

## What the paper really claims, hype check, mini-project

**The paper's own numbers \[paper, quoted not re-run\]**

<table><thead><tr><th>Claim</th><th>Number</th></tr></thead><tbody><tr><td>distance to the best possible (information-theoretic lower bound)</td><td>within a factor ≈ 2.7 (√3π/2); about 1.45 at 1 bit</td></tr><tr><td>KV cache quality</td><td>neutral at 3.5 bits per channel; marginal loss at 2.5 bits</td></tr><tr><td>LongBench-E average, Llama-3.1-8B</td><td>full cache (16-bit) 50.06; TurboQuant 3.5-bit 50.06; 2.5-bit 49.44; KIVI 3-bit 48.50</td></tr><tr><td>Needle-in-a-Haystack (4k-104k tokens)</td><td>0.997 for both full precision and TurboQuant, at &gt;4x compression</td></tr><tr><td>Nearest-neighbour quantization time (4-bit, d=1536)</td><td>0.0013 s vs product quantization 239.75 s</td></tr><tr><td>Press-reported (Google blog, not verified by me)</td><td>≥6x KV memory, up to 8x faster attention logits on H100 vs 32- bit keys</td></tr></tbody></table>

### Hype check

**"6x with zero loss"** mixes things. From the paper: 3.5 bits = about 4.6x with no loss; 2.5 bits = about 6.4x with marginal loss (my arithmetic). "Up to 8x faster" depends on hardware and baseline \[press\] . **Limits the paper states:** not exactly optimal (2.7x gap); needs larger d for the theory; norms not counted; two LLMs tested for the KV results; in the nearest-neighbour tests the product-quantization baseline was trained on the evaluation data (which favours it, the paper says), while RabitQ ran as a CPU implementation with overheads the paper did not count (which can flatter TurboQuant's timing). **Independent study** \[critic\] : rotation stage works as described for near-isotropic and heavy-tailed keys, fails for some structures (low-rank keys), and doubts the QJL-on-keys design. Single-author simulation. **I could not find a verified official library** to give you. Do not assume a pip package exists. Check Google's blog and repositories yourself.

### Cheat sheet

```
x -> store ||x||, u = x/||x|| -> z = R u * sqrt(d) (R random rotation) -> idx = nearest Lloyd-Max
level
decode: R^T (level[idx]/sqrt(d)) * ||x||
error ~ 4^-b (1 bit .36, 2 bit .117, 3 bit .035, 4 bit .0095)
MSE quantizer: biased dot products (1 bit: x 2/pi). TurboQuant_prod: (b-1) bits MSE + 1 bit
QJL(residual): unbiased
memory ratio vs 16-bit: 16/bits  (3.5 -> 4.6x, 2.5 -> 6.4x), norms extra
```

### Final mini-project (2 hours)

> **Practice:** **"Gravrel Compressed Search":** take 20,000 real text embeddings you generate yourself (any sentence-embedding model you can run), save as a float32 file. Compress with (a) a plain uniform 4-bit quantizer and (b) the TurboQuant pipeline from `tq_core.py` at 4, 3 and 2 bits. Measure memory (including norms), recall@10 against exact search, and time. Then add "compress, search, re-rank top-50 exactly" and measure again. Write one page: which setting would you ship for a customer with a 16 GB RAM server? Explain it in 2 minutes without notes.

### 7-day plan (25-30 min a day)

<table><thead><tr><th>Day</th><th>Do</th></tr></thead><tbody><tr><td>1</td><td>Parts 0-2 (problem and memory maths)</td></tr><tr><td>2</td><td>Level 2 baseline + Level 3 rotation</td></tr><tr><td>3</td><td>Level 4 codebook</td></tr><tr><td>4</td><td>Level 5 assemble</td></tr><tr><td>5</td><td>Level 6 bias and QJL</td></tr><tr><td>6</td><td>Levels 7-8 and the hype check</td></tr><tr><td>7</td><td>Mini-project and teach-back</td></tr></tbody></table>

### Flashcards

<table><thead><tr><th>Q</th><th>A</th></tr></thead><tbody><tr><td>What does TurboQuant do?</td><td>compresses vectors to few bits while keeping distances and dot products, with no training data</td></tr><tr><td>Three steps?</td><td>random rotation, per-value Lloyd-Max rounding, optional 1-bit QJL on the residual</td></tr><tr><td>Why rotate?</td><td>spreads outliers so every value looks like the same bell curve</td></tr><tr><td>Why a Lloyd-Max codebook?</td><td>best levels for a known bell curve, computed once</td></tr><tr><td>Why QJL?</td><td>MSE quantizers shrink dot products; sign sketch of the residual makes them unbiased</td></tr><tr><td>Error vs bits?</td><td>about 4x lower per extra bit</td></tr><tr><td>Paper&#x27;s headline for KV cache?</td><td>quality neutral at 3.5 bits, marginal loss at 2.5</td></tr><tr><td>What did I not verify?</td><td>Google blog&#x27;s 6x and 8x claims, GPU speed, real-model accuracy</td></tr></tbody></table>

### Your 60-second script

> **Say This:** "TurboQuant is a Google Research method for squeezing vectors, like an LLM's key-value cache or search embeddings, into a few bits per number without training data. First it applies a random rotation, which keeps lengths and dot products but spreads out any outlier spikes so every value follows the same bell curve. Then it rounds each value with a precomputed best codebook for that curve, and error drops about four times for each extra bit. Because that rounding makes dot products slightly too small, a second version spends one bit on a sign sketch of the leftover error to make them unbiased. The paper reports neutral quality at 3.5 bits and small loss at 2.5 bits, about 4.6 to 6.4 times less memory than 16-bit; I rebuilt the idea in numpy and my errors matched the paper's theory, but I have not verified the GPU speed claims, and an independent study questions part of the design."

**Sources:** arXiv 2504.19874 (abstract page and full-text summary); Wikipedia "TurboQuant" (for the Google blog date and press claims); "The Mathematics of Google's TurboQuant" explainer; arXiv 2605.08114 (independent KV-cache study). **Verified by running:** 7 tests; all outputs above (numpy 2.5.3, synthetic data, my re-implementation). **Not verified:** Google's blog itself, 6x/8x/H100 claims, any real-LLM or real-embedding result, venue, speed of a fast rotation, any official code. Check the paper and Google's blog before quoting any number.
