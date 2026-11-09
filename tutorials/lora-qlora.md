---
title: LoRA & QLoRA
group: Models & training
order: 7
blurb: Teach a giant model new tricks without retraining the giant
tagline: teach a giant model new tricks without retraining the giant W (frozen) + × tiny!
about: From scratch, with pictures, labs and interview answers · Papers and Hugging Face PEFT docs checked 25 Oct 2026 · labs run and verified
---

## 1. The problem (start here)

> **Say This:** A big language model has billions of numbers (weights) learned from the internet. To make it good at my job (my tone, my data format, my domain) I must train it a bit more. That is **fine-tuning**. Normal fine-tuning changes every weight, which is slow, needs huge GPU memory, and gives me a full-size copy of the model for every task. LoRA and QLoRA are tricks that make fine-tuning small, cheap and swappable.

### Picture: why full fine-tuning hurts

#### Full fine-tuning: update everything (7B model)

```diagram grid
red: weights 14 GB
red: gradients 14 GB
red: Adam optimizer states ~56 GB
note: ~100 GB+
note: LoRA: freeze the base, train small add-ons
blue: weights 14 GB (frozen)
note: adapter grads + optimizer: tiny (tens of MB)
note: QLoRA: also squeeze the frozen base to 4 bits
note: base ~3.5 GB + tiny adapters
```

Sizes are rule-of-thumb estimates (mixed-precision Adam needs about 12-16 bytes per parameter; this ignores activations). They show the idea, not a measured benchmark.

> **Tip:** Kitchen analogy: full fine-tuning rewrites the whole cookbook for every customer. LoRA keeps one printed cookbook (frozen) and clips a small sticky-note recipe card per customer. QLoRA prints the cookbook in a smaller font so it fits a small shelf.

## 2. Where they came from

<table><tbody><tr><td>2019</td><td>2021</td><td>2021</td><td>2023</td></tr><tr><td>Adapters</td><td>Prefix-tuning</td><td>LoRA</td><td>QLoRA</td></tr><tr><td>(Houlsby et al.)</td><td>(Li &amp; Liang)</td><td>(Hu et al., Microsoft)</td><td>(Dettmers et al.)</td></tr></tbody></table>

<table><thead><tr><th>Idea</th><th>What it did</th><th>Its drawback (why LoRA won)</th></tr></thead><tbody><tr><td><b>Adapters</b> (2019)</td><td>insert small extra layers inside the model and train only them</td><td>extra layers run at inference, so a bit of added latency</td></tr><tr><td><b>Prefix / prompt</b><br><b>tuning</b> (2021)</td><td>train learned &quot;virtual tokens&quot; fed to the model</td><td>uses up context length; harder to optimise</td></tr><tr><td><b>LoRA</b> (2021)</td><td>train a low-rank update to the existing weights; merge it back afterwards</td><td>(this is the one that stuck)</td></tr><tr><td><b>QLoRA</b> (2023)</td><td>LoRA on top of a frozen 4-bit base</td><td>some extra training time from dequantizing</td></tr></tbody></table>

**LoRA** = "Low-Rank Adaptation of Large Language Models", Edward Hu, Yelong Shen and colleagues at Microsoft (arXiv 2106.09685, ICLR 2022). Headline claims on GPT-3 175B vs full fine-tuning with Adam: about **10,000× fewer trainable parameters**, about **3× less GPU memory**, and **no extra inference latency** because the update can be merged into the weights.

**QLoRA** = "Efficient Finetuning of Quantized LLMs", Tim Dettmers, Artidoro Pagnoni, Ari Holtzman and Luke Zettlemoyer (arXiv 2305.14314). Headline: fine-tune a **65B** model on a **single 48 GB GPU** with no loss in task performance versus 16-bit fine-tuning. Their Guanaco models reached 99.3% of ChatGPT on the Vicuna benchmark (GPT-4 as judge).

The adapter/prefix rows describe the idea as I know it; I read the LoRA and QLoRA papers' abstracts today but not those two.

## 3. LoRA from scratch

### Step 1 - what is a weight matrix doing?

Each attention or MLP layer holds a big matrix **W** (for example 4096 × 4096 = 16.8 million numbers). The layer computes `h = W x`. Fine-tuning wants a new matrix `W + ΔW`. **Step 2 - the key bet: Δ W is "low rank"** The LoRA authors guessed the change needed for a new task lives in a small subspace (low "intrinsic rank"). So instead of a full Δ W (d × d), write it as the product of two thin matrices:

```diagram grid
red: Δ W
green: B
green: A
note: r × d = 65,536 numbers
note: 2 × 4096 × 8
note: d × d (4096×4096) d × r
note: only 0.39% of full
note: 16,777,216 numbers
```

Rank = how many independent directions a matrix has. `B×A` can never have rank above r. Choosing a small r forces the update to be simple. The paper found even r of 1 or 2 can work on some tasks, even when d is 12,288.

### Step 3 - the forward pass (what really runs)

```diagram grid
blue: W x (frozen, locked)
red: +
green: A (r×d)
green: B (d×r)
red: × alpha / r
note: h = W x + (alpha / r) · B (A x) only A and B get gradients
```

### Step 4 - the three details people forget

1. **Initialisation:** A starts random small (Gaussian), **B starts at zero**. So `BA = 0` and the model begins exactly as the original. (My lab shows the loss sitting flat, then dropping once B moves.)
2. **Scaling:** the update is multiplied by `alpha / r`. Alpha is just a volume knob; the paper sets it once and does not tune it. With `r = 16, alpha = 32` the scale is 2.
3. **Merging:** after training, compute `W' = W + (alpha/r) B A` and throw A and B away. The model is the same size and speed as the original: **zero extra inference latency**. Or keep adapters separate and swap them per task: one base model, many megabyte-sized adapters ("SQL", "legal tone", "Hindi support").

## 4. Where LoRA is attached and the knobs

```diagram grid
note: LoraConfig dials
note: r: rank, bigger = more capacity
plain: one Transformer block | every red name is a Linear layer · a LoRA pair (A,B) can sit by any of them · paper: mostly Wq, Wv | now: "all-linear"
blue: Attention | q k v o _proj
blue: MLP | gate up down _proj
note: lora_alpha: volume, scale = alpha/r
note: target_modules: which layers
note: lora_dropout: regularisation
note: bias: usually "none"
```

<table><thead><tr><th>Setting</th><th>PEFT default</th><th>What it does / how I choose</th></tr></thead><tbody><tr><td><code>r</code></td><td>8</td><td>rank. Start 8-16; raise (32-64) if the task is complex and the model underfits. More = more trainable params.</td></tr><tr><td><code>lora_alpha</code></td><td>8</td><td>numerator of the scale <code>alpha/r</code> . Common habit: alpha = r or 2r. If you raise r but keep alpha, the scale shrinks.</td></tr><tr><td><code>target_modules</code></td><td>None (auto by<br>architecture)</td><td>list of layer names, a regex, or <code>&quot;all-linear&quot;</code> for every linear layer except the output layer. QLoRA uses all-linear.</td></tr><tr><td><code>lora_dropout</code></td><td>0.0</td><td>dropout on the adapter path; 0.05-0.1 helps on small datasets.</td></tr><tr><td><code>bias</code></td><td>&quot;none&quot;</td><td>train no biases; &quot;all&quot;/&quot;lora_only&quot; make the model differ from base even with adapters off.</td></tr><tr><td><code>use_rslora</code></td><td>False</td><td>rank-stabilised scaling: <code>alpha / sqrt(r)</code> instead of <code>alpha / r</code> , so changing r matters less.</td></tr><tr><td><code>task_type</code></td><td>None</td><td>e.g. <code>&quot;CAUSAL_LM&quot;</code> for chat/text-generation models.</td></tr></tbody></table>

Defaults and scaling formulas from the Hugging Face PEFT LoRA reference. My own advice (start values, dropout range) is rule of thumb, not official.

**Learning rate:** LoRA usually tolerates a higher learning rate than full fine-tuning because few parameters move (often around 1e-4 to 2e-4 in tutorials; tune it, verify on your task).

## 5. Lab A - feel LoRA with plain numpy (CPU only)

No GPU, no model download. Only `pip install numpy`. This is the best way to be able to explain LoRA on a whiteboard.

```powershell
mkdir $HOME\lora-lab
cd $HOME\lora-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install numpy scipy
```

### A1. Count parameters and prove merging works

```python
@'
import numpy as np
rng = np.random.default_rng(0)
# 1) Parameter counting for ONE weight matrix of a 7B-class model
d_out, d_in, r = 4096, 4096, 8
full = d_out * d_in
lora = r * d_in + d_out * r          # A is r x d_in, B is d_out x r
print(f"full matrix : {full:,} params")
print(f"LoRA r={r}   : {lora:,} params  ({100*lora/full:.2f}% of full)")
# 2) Merge equivalence: W + scale*B@A  gives the same output as base + adapter path
alpha = 16
scale = alpha / r
W = rng.normal(size=(d_out, d_in)) / np.sqrt(d_in)
A = rng.normal(size=(r, d_in)) * 0.01
B = rng.normal(size=(d_out, r)) * 0.01
x = rng.normal(size=(5, d_in))
two_path = x @ W.T + scale * (x @ A.T) @ B.T
merged   = x @ (W + scale * B @ A).T
print("max difference merged vs two-path:", float(np.abs(two_path - merged).max()))
print("rank of update B@A:", np.linalg.matrix_rank(B @ A), "(never more than r =", r, ")")
'@ | Set-Content lora_math.py
python lora_math.py
```

Output I got:

```
full matrix : 16,777,216 params
LoRA r=8   : 65,536 params  (0.39% of full)
max difference merged vs two-path: 4.551914400963142e-15
rank of update B@A: 8 (never more than r = 8 )
```

> **Tip:** The tiny difference (1e-15) is just floating-point noise: merged and unmerged are the same function. That is the "no inference latency" claim, proved.

### A2. Train a LoRA by hand (manual gradients)

```python
@'
import numpy as np
rng = np.random.default_rng(1)
d_in, d_out, r, n = 64, 64, 4, 512
alpha = 8
scale = alpha / r
W0 = rng.normal(size=(d_out, d_in)) / np.sqrt(d_in)          # frozen "pretrained" weight
true_delta = rng.normal(size=(d_out, 2)) @ rng.normal(size=(2, d_in)) * 0.2   # hidden rank-2 change
x = rng.normal(size=(n, d_in))
y = x @ (W0 + true_delta).T                                    # new task data
A = rng.normal(size=(r, d_in)) * 0.01                          # trainable, small random
B = np.zeros((d_out, r))                                       # trainable, ZERO at start
print("trainable:", A.size + B.size, "| frozen:", W0.size)
lr = 0.05
for step in range(1, 101):
    h = x @ A.T                                                # n x r
    pred = x @ W0.T + scale * h @ B.T
    G = 2 * (pred - y) / (n * d_out)                           # d loss / d pred
    dB = scale * G.T @ h
    dA = scale * (G @ B).T @ x
    B -= lr * dB * 10
    A -= lr * dA * 10
    if step in (1, 5, 10, 25, 50, 100):
        print(f"step {step:3d}  loss {np.mean((pred - y) ** 2):.6f}")
Wm = W0 + scale * B @ A
print("error of merged weight vs target:", float(np.abs(Wm - (W0 + true_delta)).mean()))
'@ | Set-Content lora_train.py
python lora_train.py
```

Output I got:

```
trainable: 512 | frozen: 4096
step   1  loss 3.665588
step   5  loss 3.663637
step  10  loss 3.619627
step  25  loss 0.063228
step  50  loss 0.000007
step 100  loss 0.000000
error of merged weight vs target: 1.133500878939547e-07
```

The hidden "true change" has rank 2; our adapter has rank 4, so it can capture it. Only 512 numbers were trained while 4,096 stayed frozen. The flat start is the zero-initialised B at work: no signal flows until B leaves zero. **Experiment:** change `r = 4` to `r = 1` and rerun. The loss stops above zero because rank 1 cannot express a rank-2 change. That one experiment is your answer to "what does rank control?".

## 6. QLoRA from scratch

> **Say This:** QLoRA = LoRA + a 4-bit frozen base model. I keep the base weights stored in 4 bits, dequantize each layer to 16-bit only while computing, and train LoRA adapters in 16-bit. Gradients flow through the 4-bit base into the adapters; the base itself never changes.

```diagram grid
note: Three inventions in the paper
blue: W stored in 4-bit NF4 (frozen)
note: (4-bit NormalFloat)
plain: one layer inside QLoRA | dequantize to bf16 on
note: the fly
note: levels placed where normal-distributed
note: weights actually are, not evenly spaced
red: W (bf16, temporary) × x
green: + LoRA A,B in bf16 (trained)
note: quantize the quantization constants too:
note: saves ~0.37 bits/param (~3 GB on 65B)
note: spill optimizer state to CPU RAM on spikes
```

### 1. NF4

### 2. Double quantization

### 3. Paged optimizers

### What "quantization" means (tiny example)

Take 64 weights (a block). Find the biggest absolute value (absmax). Divide all by it, so everything sits in \[-1, 1\]. Snap each to the nearest of 16 allowed levels (4 bits = 16 values), and store the 4-bit index plus one absmax number per block. To use a weight later: look up the level, multiply by absmax. You lose a little precision but save 4x memory vs 16-bit.

**Why NF4?** Trained weights look like a bell curve: most near zero, few large. Evenly spaced levels waste resolution on the rare large values. NF4 puts more levels near zero (at quantiles of a normal distribution), so average error is lower.

### Lab B - see it in numbers

```python
@'
import numpy as np
from scipy.stats import norm
rng = np.random.default_rng(2)
w = rng.normal(size=64 * 4096)                 # fake weights, normally distributed
blocks = w.reshape(-1, 64)
absmax = np.abs(blocks).max(axis=1, keepdims=True)
scaled = blocks / absmax                       # every block now lies in [-1, 1]
uniform = np.linspace(-1, 1, 16)               # 16 evenly spaced levels = 4 bits
q = (np.arange(16) + 0.5) / 16                 # normal-quantile levels, scaled to [-1, 1]
codebook = norm.ppf(q); codebook = codebook / np.abs(codebook).max()
def quant(vals, levels):
    idx = np.abs(vals[..., None] - levels).argmin(axis=-1)
    return levels[idx]
for name, lv in [("uniform 4-bit", uniform), ("normal-quantile 4-bit (NF4-style)", codebook)]:
    rec = quant(scaled, lv) * absmax
    print(f"{name:36} MSE = {np.mean((blocks - rec) ** 2):.6f}")
# constants overhead: one 32-bit absmax per 64 weights
plain = 32 / 64
double = 8 / 64 + 32 / (64 * 256)              # constants themselves quantized to 8 bit in blocks
of 256
print(f"constants overhead: {plain:.3f} bits/param -> {double:.3f} bits/param, saves {plain-
double:.3f}")
print("4-bit weights of a 7B model:", f"{7e9*4/8/1e9:.1f} GB (+ constants {7e9*double/8/1e9:.2f}
GB)")
'@ | Set-Content quant_demo.py
python quant_demo.py
```

Output I got:

```
uniform 4-bit                        MSE = 0.010134
normal-quantile 4-bit (NF4-style)    MSE = 0.008382
constants overhead: 0.500 bits/param -> 0.127 bits/param, saves 0.373
4-bit weights of a 7B model: 3.5 GB (+ constants 0.11 GB)
```

> **Careful:** This is a simplified teaching version. The real NF4 table and bitsandbytes kernels differ in detail. The numbers show the idea: normal-shaped levels give lower error, and the 0.373 bits saved matches the paper's "about 0.37 bits per parameter".

### Memory picture (7B model, weights only, bits ÷ 8)

```diagram grid
note: 16-bit
blue: 14 GB
note: 8-bit
blue: 7 GB
note: 4-bit base)
green: 3.5 GB (QLoRA
```

## 7. Real QLoRA code (needs an NVIDIA GPU)

> **Careful:** QLoRA uses the bitsandbytes library and a CUDA GPU. Easiest for practice: a free Colab GPU notebook or a Linux/WSL machine with an NVIDIA GPU. I did not run this on a GPU, so treat the training part as a template (verify). The config blocks below are copied from the Hugging Face PEFT quantization guide.

```bash
# in a GPU notebook or WSL
pip install -U transformers peft bitsandbytes accelerate datasets trl
```

```python
@'
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
MODEL = "Qwen/Qwen3-1.7B"      # any small causal LM from huggingface.co (check the id)
bnb = BitsAndBytesConfig(
    load_in_4bit=True,                      # store base weights in 4-bit
    bnb_4bit_quant_type="nf4",              # NormalFloat4
    bnb_4bit_use_double_quant=True,         # quantize the constants too
    bnb_4bit_compute_dtype=torch.bfloat16,  # math happens in bf16
)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=bnb, device_map="auto")
model = prepare_model_for_kbit_training(model)
cfg = LoraConfig(r=16, lora_alpha=32, target_modules="all-linear",
                 lora_dropout=0.05, bias="none", task_type="CAUSAL_LM")
model = get_peft_model(model, cfg)
model.print_trainable_parameters()          # expect well under 2% trainable
# ... train with your Trainer or TRL SFTTrainer on your dataset ...
model.save_pretrained("my-adapter")         # saves ONLY the small adapter files
'@ | Set-Content qlora_setup.py
```

### Reading it line by line

<table><thead><tr><th>Line</th><th>Meaning</th></tr></thead><tbody><tr><td><code>load_in_4bit</code></td><td>quantize the base to 4 bits as it loads</td></tr><tr><td><code>nf4</code> + <code>double_quant</code></td><td>the paper&#x27;s data type and constant-saving trick</td></tr><tr><td><code>compute_dtype bfloat16</code></td><td>dequantized math runs in bf16 for speed and stability</td></tr><tr><td><code>prepare_model_for_kbit_training</code></td><td>get the quantized model ready for training (gradient settings, norm layers)</td></tr><tr><td><code>get_peft_model</code></td><td>wraps the model: freezes the base, inserts trainable A,B</td></tr><tr><td><code>save_pretrained</code></td><td>writes only the adapter (megabytes)</td></tr></tbody></table>

### Using the adapter afterwards

```python
# load base + adapter, or fold the adapter into the weights
from peft import PeftModel
model = PeftModel.from_pretrained(base_model, "my-adapter")
merged = model.merge_and_unload()   # W + (alpha/r) B A baked in
```

> **Tip:** Merging precision: folding an adapter into a 4-bit base is lossy. The usual practice is to merge into a 16-bit copy of the base model, then quantize again if needed. The PEFT page I read lists merge limits for several other quantizers; check the current PEFT notes for bitsandbytes (verify).

```json
{"prompt": "Extract invoice fields: INV-204 Acme Rs 14500 ...", "completion": "
{\"invoice_no\":\"INV-204\", ...}"}
# training data: a few hundred to a few thousand clean examples like this; hold out 10-20% to test
```

## 8. Compare, choose, and traps

<table><thead><tr><th></th><th>Full fine-tune</th><th>LoRA</th><th>QLoRA</th></tr></thead><tbody><tr><td>Base<br>weights</td><td>trained</td><td>frozen, 16-bit</td><td>frozen, 4-bit</td></tr><tr><td>Trainable</td><td>all</td><td>small adapters</td><td>small adapters</td></tr><tr><td>GPU<br>memory</td><td>highest</td><td>much lower</td><td>lowest</td></tr><tr><td>Speed</td><td>slowest per step</td><td>faster</td><td>a bit slower than LoRA (dequantizing)</td></tr><tr><td>Output</td><td>full model copy</td><td>adapter file (or<br>merged)</td><td>adapter file (merge into 16-bit)</td></tr><tr><td>Quality</td><td>best ceiling</td><td>close on most tasks</td><td>reported on par with 16-bit fine-tuning (paper)</td></tr><tr><td>Best when</td><td>lots of data and GPUs, big behaviour change</td><td>one GPU, several tasks</td><td>limited VRAM, big model on small GPU</td></tr></tbody></table>

### Decision flow

<table><thead><tr><th>Question</th><th>If yes</th></tr></thead><tbody><tr><td>Is the issue missing or changing facts?</td><td>Use RAG, not fine-tuning</td></tr><tr><td>Is it format or style, fixable with a good prompt and examples?</td><td>Prompt first</td></tr><tr><td>Need a consistent skill/style with hundreds+ labelled examples?</td><td>LoRA</td></tr><tr><td>Model does not fit my GPU in 16-bit?</td><td>QLoRA</td></tr></tbody></table>

### Variants worth naming (one line each)

**rsLoRA:** scale by `alpha/sqrt(r)` for stable training across ranks (in PEFT as `use_rslora`). **LoftQ:** quantization-aware initialisation for LoRA on quantized models; PEFT notes it works best with `all-linear` and NF4. Others exist (DoRA, AdaLoRA and more); I did not verify their details, so mention them only as "further variants".

### Traps and honest limits

LoRA changes behaviour better than it injects reliable new facts. Facts stay with RAG. Bad or tiny data gives a confident bad model. Always test on held-out examples. Too high rank/learning rate can overfit; too low underfits. Adapters are tied to the base model they were trained on. Change the base, retrain. Check the base model's license before fine-tuning and releasing.

## 9. Explain it to anyone

> **Say This:** **10 seconds:** "LoRA teaches a big AI model a new skill by training two tiny add-on matrices instead of the whole model. QLoRA does the same while keeping the big model in 4-bit so it fits a small GPU."

> **Say This:** **60 seconds:** "A model's knowledge sits in huge weight matrices. Fine-tuning normally edits all of them, which needs enormous memory and a full copy per task. LoRA freezes them and learns the change as the product of two thin matrices, like writing a short sticky note instead of reprinting the book. That is under one percent of the parameters. When training ends I can merge the note back, so there is no slowdown. QLoRA adds one more trick: store the frozen book in 4 bits, so even a 65B model can be tuned on one 48 GB GPU."

### Whiteboard script (draw these in order)

1. Draw a big square W and write "frozen" with a lock.
2. Next to it, draw a tall thin B and a wide thin A. Write `d × r` and `r × d`.
3. Write `h = Wx + (alpha/r) B A x`. Say "B starts at zero".
4. Do the numbers: 4096×4096 = 16.8M vs 65,536 at r=8 (0.39%).
5. Draw a 16-bit bar, then a 4-bit bar a quarter the length. Say "that is QLoRA".

### One-page cheat sheet

<table><thead><tr><th>Formula / fact</th><th>Value</th></tr></thead><tbody><tr><td>Update</td><td><code>W&#x27; = W + (alpha/r) B A</code> , B: d×r, A: r×d</td></tr><tr><td>Init</td><td>A random Gaussian, B zeros</td></tr><tr><td>Params per matrix</td><td><code>r (d_in + d_out)</code></td></tr><tr><td>Memory of weights</td><td>params × bits / 8</td></tr><tr><td>QLoRA parts</td><td>NF4, double quantization, paged optimizers, bf16 compute</td></tr><tr><td>Paper claims</td><td>LoRA: ~10,000× fewer trainable params, ~3× less memory (GPT-3 175B). QLoRA: 65B on 48 GB</td></tr></tbody></table>

## 10. Interview Q&A

**Q1. What is LoRA?** A parameter-efficient fine-tuning method. Freeze the pretrained weights and learn the weight update as a low-rank product B×A, scaled by alpha/r. Only A and B train.

**Q2. Why does low rank work?** Hypothesis from the paper: the update needed to adapt a pretrained model has low intrinsic rank, so a few directions are enough. Empirically small r (even 1-2 on some tasks) works.

**Q3. Why initialise B to zero?** So B×A = 0 at the start and the model equals the base model; training departs smoothly from a known good point. A is random so gradients can flow to B.

**Q4. What do r and alpha do?** r sets capacity (trainable params). Alpha scales the update via alpha/r, like a learning-rate-style volume. Raising r with fixed alpha lowers the scale; rsLoRA uses alpha/sqrt(r) to reduce that sensitivity.

**Q5. Which layers do you target?** The paper mostly used query and value projections. Today I usually target all linear layers (`"all-linear"`), which QLoRA-style recipes recommend, trading a few more parameters for quality.

**Q6. Does LoRA slow inference?** No, if merged: W' = W + (alpha/r)BA has the original shape. If kept separate, there is a small extra computation but it allows adapter swapping.

**Q7. What is QLoRA?** LoRA on a frozen 4-bit quantized base. Gradients pass through the dequantized base into 16-bit adapters. It made 65B fine-tuning possible on one 48 GB GPU with performance matching 16-bit fine-tuning (per the paper).

**Q8. Name QLoRA's innovations.** NF4 data type for normally distributed weights; double quantization (about 0.37 bits per parameter saved); paged optimizers using unified memory to avoid out-of-memory spikes; plus bf16 compute.

**Q9. Why NF4 instead of plain int4?** Weights are roughly normal, so putting quantization levels at normal quantiles gives lower expected error than evenly spaced levels. My toy test showed lower error for the normal-quantile codebook.

**Q10. Is the 4-bit base updated?** No. It stays frozen. Only LoRA adapters are trained and kept in higher precision.

**Q11. LoRA vs full fine-tuning, trade-offs?** Full has the highest ceiling and costs the most. LoRA is far cheaper, stores small adapters, avoids touching base weights, and is close in quality on most tasks, but may fall short when the change needed is large.

**Q12. LoRA or RAG?** RAG for knowledge that changes or must be cited. LoRA for behaviour: style, format, domain language, tool-use patterns. They combine well.

**Q13. How do you choose r?** Start small (8-16), evaluate on a held-out set, increase only if underfitting, and check that gains justify the extra parameters.

**Q14. How do you serve many customers?** One shared base model plus one small adapter per customer or task, loaded on demand or merged for the hottest ones.

**Q15. What could go wrong?** Poor data, overfitting, evaluating on training data, adapter/base mismatch, lossy merges into a quantized base, and expecting fine-tuning to add reliable facts.

**Q16. How would you prove it worked?** Same test set before and after, task metrics plus a human spot check, compare against a strong prompt and a RAG baseline, and report cost and latency.

### Honesty page

<table><thead><tr><th>Verified</th><th>Not verified / do yourself</th></tr></thead><tbody><tr><td>Papers&#x27; authors and headline claims (read from arXiv text today). PEFT LoraConfig defaults, scaling formulas, and the QLoRA BitsAndBytesConfig recipe from Hugging Face docs. The three numpy labs were run and the outputs shown are real.</td><td>I did not run the QLoRA code on a GPU or on Windows; bitsandbytes needs CUDA and Windows support may vary (use Colab or WSL; verify). Learning-rate and rank suggestions are rules of thumb. Adapters and prefix-tuning history is from my own knowledge. Memory estimates for full fine-tuning are approximations that ignore activations.</td></tr></tbody></table>

Sources: arXiv 2106.09685 (LoRA); arXiv 2305.14314 (QLoRA); huggingface.co/docs/peft (LoRA reference, quantization guide).
