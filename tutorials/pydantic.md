---
title: Pydantic
group: APIs & backend
order: 16
blurb: The bouncer at the door of your code, in seven levels
tagline: the bouncer at the door of your code
about: Seven levels, each with a real Gravrel scenario, commands and small tasks · Pydantic v2 — every example was run by me
---

## How to use this tutorial

**Pydantic suits practice-first learning perfectly:** every idea gives instant pass or fail. Three tweaks:

1. **One picture: a bouncer.** Data arrives at the door of your code. The bouncer checks the ID (type, range, shape), fixes harmless things ("29" becomes 29) and throws out the rest with a clear reason. Every level adds one more rule for the bouncer.
2. **Always read the error.** Half the skill is reading `ValidationError`. Each level has a "send bad data" task.
3. **Why it matters for you:** Pydantic runs inside FastAPI (your last notes) and is the standard way to check structured output from LLMs, so Level 7 validates a messy LLM-style reply. That is directly useful for GenAI roles \[ME\].

> **Careful:** **What is tested, honestly.** All 7 scripts ran and 7 pytest tests pass, with Pydantic 2.13.5 and pydantic-settings 2.16.2 on Python 3.13. Outputs in these notes are copied from real runs. **Not tested:** your Windows PowerShell session (commands are standard). Pydantic v1 code looks different (`validator`, `.dict()`); these notes are v2 only.

### Setup (PowerShell, 3 min)

```powershell
cd C:\Users\god
Expand-Archive Pydantic_Practice_Lab.zip -DestinationPath pydantic
cd pydantic\lab
python -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
pytest -q test_all.py           # expect: 7 passed
```

> **Tip:** **Cycle per level (20 min):** read → run `python pNN_*.py` → do the TASK box → close the page and explain aloud.

## Level 1: your first model (`p01_basics.py`)

Scenario: a customer signs up. You receive name, age, email, sometimes as text from a form.

```python
from pydantic import BaseModel, ValidationError
class Customer(BaseModel):
    name: str
    age: int
    email: str
c = Customer(name="Asha", age="29", email="asha@gravrel.example")
print(c)              # name='Asha' age=29 email='asha@gravrel.example'
print(type(c.age))    # <class 'int'>   "29" became 29 (coercion)
```

### The 5 moves you will use daily

<table><thead><tr><th>Move</th><th>Code</th><th>Gives</th></tr></thead><tbody><tr><td>make from keywords</td><td><code>Customer(name=..)</code></td><td>object</td></tr><tr><td>make from dict</td><td><code>Customer.model_validate(d)</code></td><td>object</td></tr><tr><td>make from JSON text</td><td><code>Customer.model_validate_json(s)</code></td><td>object</td></tr><tr><td>to dict</td><td><code>c.model_dump()</code></td><td>dict</td></tr><tr><td>to JSON text</td><td><code>c.model_dump_json()</code></td><td>str</td></tr></tbody></table>

### Bad data

```
try: Customer(name="Bad", age="twenty", email="b@x.com")
except ValidationError as e:
    for err in e.errors(): print(err["loc"], err["type"], err["msg"])
# ('age',) int_parsing Input should be a valid integer, unable to parse string as an integer
```

Each error has **loc** (where), **type** (code you can test for) and **msg** (human text).

> **Practice:** **Tasks (15 min):** (1) Run it. (2) Change age to `"29.7"` and then `29.0`: which pass? (3) Remove `email` and read the "missing" error. (4) Pass a list for `name` and read the type. (5) Add a field `city: str = "Bhubaneswar"`; create without it.

> **Key idea:** Model = class with typed fields. Good data in → clean object. Bad data in → ValidationError with loc, type, msg.

> **Teach It Back:** Explain "coercion" to a friend with the example of "29" and 29.

## Level 2: Field rules, defaults, aliases (`p02_fields.py`)

Scenario: signup form with real rules: username 3-20 lowercase chars, adults only, optional nickname.

```python
class Signup(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-z0-9_]+$")
    age: int = Field(ge=18, le=100)
    plan: str = "free"                               # default
    nickname: str | None = None                      # optional
    tags: list[str] = Field(default_factory=list)    # fresh empty list per object
    created: datetime = Field(default_factory=datetime.now)
    email_address: str = Field(alias="email")        # incoming key is "email"
```

<table><thead><tr><th>Constraint</th><th>Meaning</th></tr></thead><tbody><tr><td><code>ge / gt / le / lt</code></td><td>≥ / &gt; / ≤ / &lt; for numbers</td></tr><tr><td><code>min_length / max_length</code></td><td>length of str or list</td></tr><tr><td><code>pattern</code></td><td>regular expression</td></tr><tr><td><code>default_factory</code></td><td>run a function for each new object (use for lists, dates)</td></tr><tr><td><code>alias</code></td><td>name in the incoming data differs from your field</td></tr></tbody></table>

**Real outputs:** username "AB" + age 17 gave `string_too_short` and `greater_than_equal`; age 200 gave `less_than_equal`; no email gave `missing` (with loc `email`, the alias).

**Reusable type:** `Age = Annotated[int, Field(ge=0, le=120)]` then `age: Age` anywhere.

> **Practice:** **Tasks (20 min):** (1) Run it; send each bad case and read the codes. (2) Make a second Signup and prove `tags` are not shared between objects (the test does this). (3) Add `phone` with pattern for exactly 10 digits. (4) Try `Signup(username="abc", age=18, email_address="a@x.com")`: does the field name work? Why not? (answer: only the alias is accepted by default).

> **Teach It Back:** Why is `default_factory=list` safer than a shared default list? Say it in one sentence.

## Level 3: custom validators and computed fields (`p03_validators.py`)

Scenario: an order. Clean the item name, qty must be positive, a discount needs a coupon, total is calculated.

```python
@field_validator("item")                 # ONE field
@classmethod
def clean_item(cls, v): v = v.strip().lower(); ...; return v
@model_validator(mode="after")           # WHOLE model, after fields passed
def coupon_rule(self):
    if self.discount_pct > 0 and not self.coupon:
        raise ValueError("discount needs a coupon code")
    return self
@computed_field
@property
def total(self) -> float: return round(self.qty*self.unit_price*(1-self.discount_pct/100), 2)
```

**Real output:** `Order(item=" VPS-2GB ", qty=3, unit_price=499, discount_pct=10, coupon="DIWALI")` → item `vps-2gb`, total **1347.3**; total also appears in `model_dump()`. Errors: `Value error, item cannot be blank` etc.

<table><thead><tr><th>Use</th><th>When</th></tr></thead><tbody><tr><td>Field constraint (Level 2)</td><td>simple rule on one value</td></tr><tr><td><code>field_validator</code></td><td>custom rule or cleaning for one field</td></tr><tr><td><code>model_validator</code></td><td>rule that compares several fields</td></tr><tr><td><code>computed_field</code></td><td>derived value you want in the output</td></tr></tbody></table>

> **Practice:** **Tasks (25 min):** (1) Run and read each error message. (2) Add a rule: `discount_pct` must be 0-

50. (3) Add a model rule: `qty > 100` requires a coupon. (4) Add computed field `gst` = 18% of total. (5) Use `mode="before"` on a field validator to turn "1,000" into 1000.

> **Key idea:** field\_validator = one field. model\_validator = many fields. Raise ValueError to reject.

> **Teach It Back:** Give a real-shop example of a rule that needs a model validator, not a field validator.

## Level 4: nested models, Enum, Literal, unions (`p04_nested.py`)

Scenario: a server with several disks and a region; and a checkout that accepts card or UPI.

```python
class Disk(BaseModel):
    size_gb: int = Field(gt=0)
    kind: Literal["ssd", "hdd"] = "ssd"
class Server(BaseModel):
    name: str
    region: Region               # Enum: bhubaneswar / mumbai
    disks: list[Disk]            # list of models
    labels: dict[str, str] = {}
```

Nested dicts are validated and turned into objects automatically. **Error location is a path:** bad disk size gave `('disks', 0, 'size_gb')`: field, list index, inner field.

### Discriminated union (pick the model by a tag)

```python
class Card(BaseModel): type: Literal["card"]; last4: str
class Upi(BaseModel):  type: Literal["upi"];  vpa: str
Payment = Annotated[Union[Card, Upi], Field(discriminator="type")]
# {"pay": {"type":"upi","vpa":"a@upi"}}  ->  Upi object
```

<table><thead><tr><th>Tool</th><th>Use</th></tr></thead><tbody><tr><td>Enum</td><td>fixed set that you reuse in code ( <code>.value</code> gives text)</td></tr><tr><td>Literal</td><td>quick fixed set right in the type</td></tr><tr><td>discriminator</td><td>different shapes chosen by one field; clearer errors, faster</td></tr></tbody></table>

> **Practice:** **Tasks (25 min):** (1) Run it. (2) Send a server with no disks: allowed? Make it invalid with `Field(min_length=1)`. (3) Add a third payment type `netbanking` with `bank`. (4) Send `{"type":"cash"}` and read the error. (5) Add a nested `Owner` model with email to Server.

> **Teach It Back:** Draw Server → Disk on paper and explain where the error path comes from.

## Level 5: config, secrets, strict mode, output control (`p05_config_serialize.py`)

Scenario: user accounts. Trim spaces, reject unknown fields, hide passwords, rename keys in the output.

```python
class User(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str
    password: SecretStr
    user_id: int = Field(alias="userId", serialization_alias="id")
```

<table><thead><tr><th>Setting</th><th>Real result I saw</th></tr></thead><tbody><tr><td><code>str_strip_whitespace</code></td><td>&quot; Asha &quot; → &#x27;Asha&#x27;</td></tr><tr><td><code>extra=&quot;forbid&quot;</code></td><td>unknown field <code>role</code> → error type <code>extra_forbidden</code></td></tr><tr><td><code>frozen=True</code></td><td>assigning later → <code>frozen_instance</code> error</td></tr><tr><td><code>strict=True</code></td><td>qty=&quot;5&quot; rejected ( <code>int_type</code> ); no coercion</td></tr><tr><td><code>SecretStr</code></td><td>prints as <code>**********</code> ; <code>.get_secret_value()</code> reveals it</td></tr><tr><td><code>model_dump(by_alias=True, exclude=</code> <code>{&quot;password&quot;})</code></td><td><code>{&#x27;name&#x27;: &#x27;Asha&#x27;, &#x27;id&#x27;: 7}</code></td></tr><tr><td><code>@field_serializer</code></td><td>paise 49900 → <code>&#x27;Rs 499.00&#x27;</code> in output</td></tr></tbody></table>

> **Say This:** **Lax vs strict:** by default Pydantic is **lax**: it converts sensible things ("29" → 29, even "yes" → True). **Strict** refuses conversions. Use strict for money-like or security-sensitive input; lax for forms and query strings.

> **Practice:** **Tasks (25 min):** (1) Run it. (2) Remove `extra="forbid"`, send `role`: it is silently ignored. Which is safer for an API, and why? (3) Print the user without `exclude`: is the password visible in the JSON? (4) Make a frozen model and try to change it. (5) Add a serializer that returns the name in upper case.

> **Teach It Back:** Explain lax vs strict with the bouncer: "fix harmless mistakes" vs "refuse anything not exact".

## Level 6: settings from environment variables (`p06_settings.py`)

Scenario: your app needs a DB URL, a debug flag and an API key, and they must NOT be hard-coded. Install once: `pip install pydantic-settings` (a separate package in v2).

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GRAVREL_", env_file=".env", extra="ignore")
    db_url: str = "sqlite:///./gravrel.db"
    debug: bool = False
    max_users: int = Field(default=100, ge=1)
    api_key: SecretStr = SecretStr("dev-only")
```

```powershell
$env:GRAVREL_DEBUG = "true"
$env:GRAVREL_MAX_USERS = "250"
python p06_settings.py        # True 250 sqlite:///./gravrel.db **********
```

Environment variables are always text; Pydantic converts "true" to True and "250" to 250 and validates them. A wrong value (`GRAVREL_MAX_USERS=0`) stops the app at startup with a clear error: good, you find the mistake immediately.

> **Careful:** Put real secrets in env vars or a `.env` file, and add `.env` to `.gitignore`. Never commit them to GitHub.

> **Practice:** **Tasks (20 min):** (1) Run it with and without the env vars. (2) Set `$env:GRAVREL_MAX_USERS = "0"` and read the error. (3) Create a `.env` file containing `GRAVREL_DB_URL=sqlite:///./test.db` and rerun. (4) Which wins when both exist? Test it (I tested it: the environment variable wins over .env). (5) Clear: `Remove-Item Env:GRAVREL_DEBUG`.

> **Teach It Back:** Why is "crash at startup on a bad setting" better than "fail later at 2 am"?

## Level 7: validating LLM output and everyday tools (`p07_llm_json.py`)

Scenario: an LLM triages tickets and replies with JSON, but models often add chatter, code fences, or wrong values. Pydantic is the guard before the data touches your system.

```python
class TicketTriage(BaseModel):
    department: Literal["billing","technical","sales"]
    urgent: bool
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(max_length=120)
def extract_json(text): ...        # regex: first {...} block
ok = TicketTriage.model_validate_json(extract_json(llm_text))
```

**Real results of 3 replies:**

<table><thead><tr><th>LLM reply</th><th>Result</th></tr></thead><tbody><tr><td>chatter + fenced valid JSON</td><td>OK (JSON extracted, validated)</td></tr><tr><td><code>{&quot;department&quot;:&quot;legal&quot;,&quot;urgent&quot;:&quot;yes&quot;,&quot;confidence&quot;:1.4,...}</code></td><td>REJECT: 2 validation errors (department, confidence). Note: <code>&quot;yes&quot;</code> was accepted as True (lax mode!)</td></tr><tr><td>&quot;I cannot help with that.&quot;</td><td>REJECT: no JSON found</td></tr></tbody></table>

On REJECT, a real app **retries the model** with the error text appended, or sends the case to a human. Also useful: `TicketTriage.model_json_schema()` gives a JSON Schema you can hand to an LLM tool, and `TypeAdapter(list[int]).validate_python(["1",2,"3"])` validates without writing a model (`[1, 2, 3]`).

> **Practice:** **Tasks (30 min):** (1) Run it. (2) Make `urgent` strict: `Field(strict=True)`; does "yes" fail now?

3. Add `reply_language: Literal["en","hi","or"]`. (4) Write a loop: if parsing fails, print the error text you would send back to the model for a retry. (5) Print the schema and find where `enum` lists the departments.

> **Teach It Back:** Why can't you just trust an LLM's JSON? Give two ways it can be wrong while looking fine.

## Cheat sheet, mini-project, plan, flashcards

### Cheat sheet

```python
class M(BaseModel): a: int; b: str | None = None
M(**d) / M.model_validate(d) / M.model_validate_json(s)
m.model_dump() / m.model_dump_json(exclude=..., by_alias=True)
Field(ge=, le=, min_length=, max_length=, pattern=, alias=, default_factory=)
@field_validator("x")  @model_validator(mode="after")  @computed_field
ConfigDict(extra="forbid", strict=True, frozen=True, str_strip_whitespace=True)
list[Model], dict[str, X], Literal[...], Enum, Annotated[Union[A,B], Field(discriminator="t")]
ValidationError -> e.errors() -> loc / type / msg
BaseSettings (pip install pydantic-settings)   TypeAdapter(T).validate_python(x)
```

### Common mistakes

<table><thead><tr><th>Mistake</th><th>Fix</th></tr></thead><tbody><tr><td>using v1 names ( <code>.dict()</code> ,<br><code>@validator</code> )</td><td>v2: <code>model_dump()</code> , <code>field_validator</code></td></tr><tr><td>assuming &quot;yes&quot;/&quot;1&quot; fail for bool</td><td>lax mode accepts them; use strict if needed</td></tr><tr><td>sharing a mutable default</td><td>use <code>default_factory</code></td></tr><tr><td>import error for BaseSettings</td><td><code>pip install pydantic-settings</code> , import from<br><code>pydantic_settings</code></td></tr><tr><td>trusting <code>model_construct</code> for input</td><td>it skips validation [official behaviour]; use only on already-trusted data</td></tr></tbody></table>

### Final mini-project (90 min, blank file)

> **Practice:** **"Gravrel Invoice" model:** customer (nested: name, email), items (list of: name, qty ≥ 1, unit\_price &gt; 0), currency (Literal "INR"/"USD"), optional coupon. Computed fields: `subtotal`, `gst` (18%), `total`. A model validator: coupon "FREE" requires subtotal &lt; 1000. `extra="forbid"`. Test with 3 valid and 5 invalid payloads, and write 5 pytest tests. Then explain it for 2 minutes without notes.

### 7-day plan (20-30 min a day)

<table><thead><tr><th>Day</th><th>Do</th></tr></thead><tbody><tr><td>1</td><td>Parts 0-1</td></tr><tr><td>2</td><td>Part 2</td></tr><tr><td>3</td><td>Part 3</td></tr><tr><td>4</td><td>Part 4</td></tr><tr><td>5</td><td>Part 5</td></tr><tr><td>6</td><td>Parts 6-7</td></tr><tr><td>7</td><td>Mini-project and teach-back</td></tr></tbody></table>

<table><tbody><tr><td>Flashcards</td></tr><tr><td><b>Q</b></td><td><b>A</b></td></tr><tr><td>What does Pydantic do?</td><td>validates and converts data using Python type hints</td></tr><tr><td>dict → model? model → JSON?</td><td><code>model_validate</code> ; <code>model_dump_json</code></td></tr><tr><td>Error has which 3 parts?</td><td>loc, type, msg</td></tr><tr><td>field vs model validator?</td><td>one field vs rules across fields</td></tr><tr><td>lax vs strict?</td><td>converts sensible values vs refuses conversion</td></tr><tr><td>Where do settings come from?</td><td>BaseSettings reads env vars / .env</td></tr><tr><td>Relation to FastAPI?</td><td>FastAPI uses Pydantic models for request/response validation</td></tr></tbody></table>

Your 60-second script

> **Say This:** "Pydantic checks and converts data using Python type hints. I describe the shape once as a model, like a customer with a name, age and email, and every input is validated: sensible things are converted, bad data raises a ValidationError that says exactly which field and why. I add rules with Field limits and validators, nest models for real structures like servers with disks, and use settings classes to read configuration safely from environment variables. FastAPI uses it for requests, and I use it to validate LLM JSON before trusting it." **Verified by running:** all 7 lab scripts and 7 tests (Pydantic 2.13.5, pydantic-settings 2.16.2, Python 3.13). **Not verified:** PowerShell behaviour on your PC; nothing major; env var beating .env was tested by me. Pydantic evolves: check docs.pydantic.dev for your installed version.
