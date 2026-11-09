---
title: FastAPI
group: APIs & backend
order: 15
blurb: Build a real API one small task at a time, up to database, tests and Docker
tagline: build a real API, one small task at a time
about: The Gravrel Tickets API, from hello-world to database, tests and Docker every step has a command, an expected result, and a small task
---

## How to use this tutorial

**Small tasks + real scenarios + exact commands is the best way to learn FastAPI.** Four tweaks:

1. **One API, eight steps.** The "Gravrel Tickets API" grows each level (hello → params → validation → CRUD → auth → database → extras → Docker). It is the same shape as real company back-ends.
2. **Expected output for every step** so you know at once if you did it right.
3. **Break it on purpose.** Send bad data, read the error. Errors teach faster than success.
4. **Teach-back + a final mini-project** (your own API from a blank file) turn it into skill.

> **Careful:** **What is tested, honestly.** I ran every code file myself: 7 automated tests pass, and I started a real server and sent real requests (the 422 and 404 messages in these notes are copied from real output). Versions used: FastAPI 0.143.3, Uvicorn 0.53, SQLAlchemy 2.1, Pydantic v2, Python 3.13. **Not tested by me:** Windows PowerShell commands (written to standard behaviour), and the Dockerfile.

### Setup (PowerShell, 5 min)

```powershell
cd C:\Users\god
Expand-Archive FastAPI_Practice_Lab.zip -DestinationPath fastapi
cd fastapi\lab
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser
RemoteSigned
pip install -r requirements.txt
pytest -q test_all.py               # expect: 7 passed
```

> **Tip:** **Cycle for every level (20-30 min):** read → run the command → do the TASK box → close the page and explain it aloud.

> **Careful:** **PowerShell trap:** `curl` in PowerShell is NOT real curl. Use `Invoke-RestMethod` (shown below) or the browser page `/docs` (best for beginners).

## The big picture

**An API is a waiter.** The client (browser, mobile app, another server) gives an order in a fixed format; the kitchen (your code + database) cooks; the waiter returns the dish in a fixed format. **FastAPI** is a Python tool to build that waiter quickly.

```diagram steps
plain: client
blue: Uvicorn
blue: FastAPI app
plain: your code
green: DB
```

<table><thead><tr><th>Piece</th><th>Job</th><th>Analogy</th></tr></thead><tbody><tr><td><b>Uvicorn</b></td><td>web server that listens on a port and speaks HTTP to FastAPI</td><td>the door of the restaurant</td></tr><tr><td><b>FastAPI</b></td><td>routes each URL to your function, checks input, builds output, writes docs</td><td>the waiter + the menu</td></tr><tr><td><b>Pydantic</b></td><td>defines the shape of data and rejects bad data</td><td>the order form with required boxes</td></tr><tr><td><b>Your</b><br><b>functions</b></td><td>the real business logic</td><td>the kitchen</td></tr></tbody></table>

### HTTP words you must know

<table><thead><tr><th>Method</th><th>Meaning</th><th>Gravrel example</th><th>Success code</th></tr></thead><tbody><tr><td>GET</td><td>read</td><td>list tickets</td><td>200</td></tr><tr><td>POST</td><td>create</td><td>open a ticket</td><td>201</td></tr><tr><td>PUT / PATCH</td><td>replace / change part</td><td>edit / close ticket</td><td>200</td></tr><tr><td>DELETE</td><td>remove</td><td>delete ticket</td><td>204 (no body)</td></tr></tbody></table>

Error codes: **401** not allowed (no/bad key), **404** not found, **422** your data has the wrong shape, **500** bug in your code.

> **Teach It Back:** **(30 s)** Explain the waiter analogy using Uvicorn, FastAPI, Pydantic and your code, out loud, once.

## Level 1: Hello, API (file `s01_hello.py`)

```python
from fastapi import FastAPI
app = FastAPI(title="Gravrel Tickets API")
@app.get("/")
def home():
    return {"service": "gravrel-tickets", "status": "running"}
@app.get("/health")
def health():
    return {"ok": True}
```

Read it: `app` is the application. `@app.get("/")` is a **decorator** meaning "when someone does GET on /, run the function below". The returned dict becomes JSON automatically.

### Run

```bash
uvicorn s01_hello:app --reload
# s01_hello = file name, app = the variable, --reload = restart on save
```

Open **http://127.0.0.1:8000/** → `{"service":"gravrel-tickets","status":"running"}`. Open **http://127.0.0.1:8000/docs** → a free interactive page listing your endpoints with a "Try it out" button. This is FastAPI's signature feature (it is generated from your code, standard OpenAPI 3.1 at `/openapi.json`).

```powershell
# second PowerShell window:
Invoke-RestMethod http://127.0.0.1:8000/health      # ok : True
```

> **Practice:** **Tasks (15 min):** (1) Run it and open `/docs`; click "Try it out" on `/health`. (2) Add `@app.get("/version")` returning `{"version": "0.1"}`; save and see it appear in `/docs` without restarting (that is `--reload`). (3) Stop the server with Ctrl+C. (4) Change the port: `uvicorn s01_hello:app --port 9000`.

> **Key idea:** decorator = URL + method → function. Return a dict = JSON.

> **Teach It Back:** Explain what `s01_hello:app` means to a friend who has never used Python modules.

## Level 2: path and query parameters (`s02_params.py`)

Scenario: a support agent wants to look up ticket 2, or list only open tickets.

```python
@app.get("/tickets")                                   # query params
def list_tickets(status: str | None = None, limit: int = 10):
    rows = [t for t in TICKETS if status is None or t["status"] == status]
    return rows[:limit]
@app.get("/tickets/{ticket_id}")                       # path param
def get_ticket(ticket_id: int): ...
```

<table><thead><tr><th>Kind</th><th>Looks like</th><th>Use for</th></tr></thead><tbody><tr><td><b>Path</b></td><td><code>/tickets/2</code></td><td>identify ONE thing</td></tr><tr><td><b>Query</b></td><td><code>/tickets?status=open&amp;limit=1</code></td><td>filter, sort, page a list</td></tr></tbody></table>

**The type hint does the work:** `ticket_id: int` makes FastAPI convert "2" to the number 2 and reject "abc" with a 422 error. No manual checking.

```powershell
uvicorn s02_params:app --reload
Invoke-RestMethod "http://127.0.0.1:8000/tickets?status=open"
Invoke-RestMethod http://127.0.0.1:8000/tickets/2
```

> **Careful:** **Expected:** status=open returns 2 tickets; limit=1 returns 1; `/tickets/abc` in the browser shows a 422 error about parsing an integer (verified by test).

> **Practice:** **Tasks (20 min):** (1) Call the 4 URLs above in the browser. (2) Add a `dept: str | None = None` filter. (3) Make `limit` default to 2. (4) Open `/tickets/abc` and read the message: which part says what is wrong? (5) Open `/tickets/99`: it returns an "error" dict with status 200, which is a bad habit. Write in one line why (answer in step 4).

> **Teach It Back:** Which would you use: `/tickets/5` or `/tickets?id=5`? Explain the difference between path and query in 2 sentences.

## Level 3: models and validation (`s03_models.py`)

Scenario: customers submit tickets. Bad data must never reach your logic.

```python
class Dept(str, Enum):
    billing = "billing"; technical = "technical"; sales = "sales"
class TicketIn(BaseModel):                     # what the client SENDS
    title: str = Field(min_length=3, max_length=80)
    dept: Dept
    urgent: bool = False                       # optional, default False
class TicketOut(TicketIn):                     # what we SEND BACK
    id: int
    status: str = "open"
@app.post("/tickets", response_model=TicketOut, status_code=201)
def create_ticket(t: TicketIn): ...
```

**Why two models?** The client must not choose the `id` or `status`. `response_model` also filters the reply so you never leak fields like passwords.

```powershell
uvicorn s03_models:app --reload
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/tickets -ContentType "application/json" -
Body '{"title":"SSH down","dept":"technical"}'
```

**Expected:** `id 1, status open, urgent False`. Now break it in `/docs` (Try it out) with `{"title":"x","dept":"legal"}`. Real reply I got:

```
422 {"detail":[{"type":"string_too_short","loc":["body","title"],"msg":"String should have at least
3 characters",...},
 {"type":"enum","loc":["body","dept"],"msg":"Input should be 'billing', 'technical' or
'sales'",...}]}
```

FastAPI listed **both** errors, with the exact field path in `loc`. You wrote zero validation code.

> **Practice:** **Tasks (25 min):** (1) Create 2 tickets via `/docs`. (2) Send bad data and read the 422. (3) Add `phone: str | None = None` to `TicketIn` and send it. (4) Add a new department `"legal"` to the Enum and retry. (5) Remove `response_model` and notice what `/docs` loses.

> **Key idea:** Pydantic model = the contract. Bad data → automatic 422. In/Out models keep secrets safe.

> **Teach It Back:** Explain to a shop owner why "TicketIn" and "TicketOut" are different.

## Level 4: full CRUD with proper errors (`s04_crud.py`)

CRUD = Create, Read, Update, Delete. Still in memory (a dict), so data vanishes on restart: that is the reason for Level 6.

```python
@app.get("/tickets/{tid}", response_model=TicketOut)
def read(tid: int):
    if tid not in DB:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return DB[tid]
@app.delete("/tickets/{tid}", status_code=204)
def delete(tid: int): ...
```

<table><thead><tr><th>Action</th><th>Request</th><th>Result</th></tr></thead><tbody><tr><td>Create</td><td>POST /tickets</td><td>201 + new ticket</td></tr><tr><td>List + filter</td><td>GET /tickets?dept=billing</td><td>200 list</td></tr><tr><td>Read one</td><td>GET /tickets/1</td><td>200, or 404 <code>{&quot;detail&quot;:&quot;Ticket not found&quot;}</code> (verified)</td></tr><tr><td>Update</td><td>PUT /tickets/1</td><td>200 updated</td></tr><tr><td>Delete</td><td>DELETE /tickets/1</td><td>204 empty, then 404</td></tr></tbody></table>

```bash
uvicorn s04_crud:app --reload       # then do everything in /docs
```

> **Practice:** **Tasks (30 min), the real-life flow:** (1) Create 3 tickets (one billing, one urgent). (2) List with `dept=billing`. (3) PUT ticket 1 with a new title. (4) DELETE ticket 2, then GET it and see 404. (5) Restart the server and list: everything is gone. Say why. (6) Add `PATCH /tickets/{tid}/close` that sets `status` to "closed". Hint: `DB[tid].status = "closed"`.

> **Key idea:** Right verb + right status code. Missing thing → raise HTTPException(404), never return 200 with "error".

> **Teach It Back:** Why is 204 returned with no body, and why must "not found" be 404 and not 200?

## Level 5: dependencies and API-key protection (`s05_deps_auth.py`)

**Depends() = "run this helper first and give me the result".** It removes repeated code and is how auth, database sessions and paging are done in real apps.

```python
def require_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Bad or missing API key")
@app.post("/tickets", dependencies=[Depends(require_key)], ...)
def create(t: TicketIn): ...
def paging(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": min(limit, 50)}   # cap at 50
@app.get("/tickets")
def list_(p: dict = Depends(paging)): ...
$env:GRAVREL_API_KEY = "my-secret"           # set a real key (default is practice-key)
uvicorn s05_deps_auth:app --reload
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/tickets -ContentType "application/json" -
Headers @{"x-api-key"="my-secret"} -Body '{"title":"Secured one","dept":"sales"}'
```

**Expected:** without the header → 401; with the right header → 201; `/public/ping` needs no key (all verified by tests, default key).

> **Careful:** An API key in a header is the simplest protection and fine for practice and internal tools. For user logins use OAuth2/JWT (next step after these notes). Never commit real keys to GitHub; keep them in environment variables.

> **Practice:** **Tasks (25 min):** (1) Call without the key and read the 401. (2) Call with it. (3) Protect `/public/ping` too by adding the dependency; test. (4) Ask for `limit=500` and confirm the cap of 50 applies.

5. Put a different key in `$env:GRAVREL_API_KEY` and restart: old key now fails.

> **Teach It Back:** Explain Depends() with a security-guard analogy at an office gate.

## Level 6: a real database (`s06_db.py`)

Data must survive restarts. We use **SQLite** (a file, no install) through **SQLAlchemy**. The same code works with PostgreSQL later by changing one line (the connection string) \[ME\].

<table><thead><tr><th>Piece</th><th>Meaning</th></tr></thead><tbody><tr><td><code>engine</code></td><td>connection to the database file</td></tr><tr><td><code>Ticket(Base)</code></td><td>the TABLE (one class = one table, one object = one row)</td></tr><tr><td><code>get_db()</code></td><td>opens a session per request, always closes it (a dependency with <code>yield</code> )</td></tr><tr><td><code>from_attributes=True</code></td><td>lets the response model read DB objects</td></tr></tbody></table>

```python
@app.post("/tickets", response_model=TicketOut, status_code=201)
def create(t: TicketIn, db: Session = Depends(get_db)):
    row = Ticket(title=t.title, dept=t.dept.value, urgent=t.urgent)
    db.add(row); db.commit(); db.refresh(row)
    return row
```

```bash
uvicorn s06_db:app --reload      # creates gravrel.db next to the file
```

**Expected:** create a ticket, stop the server, start it again: the ticket is still there. Tests confirm create, close, filter and 404.

> **Practice:** **Tasks (30 min):** (1) Create 3 tickets, restart, list them. (2) Close ticket 1 with the PATCH endpoint, list `?status=closed`. (3) Delete `gravrel.db` and restart: empty again. (4) Add a column `created_at`? First read the warning below, then try.

> **Careful:** **Real-world note:** `create_all` only creates missing tables; it does not change existing ones. Real projects use migration tools (Alembic). For practice, delete the .db file after changing a column.

> **Teach It Back:** Draw on paper: request → endpoint → session → table → response, and explain why the session is closed in `finally`.

## Level 7: tests, background tasks, middleware, async (`s07_extras.py`, `test_all.py`)

### Tests: your safety net

```bash
from fastapi.testclient import TestClient
c = TestClient(app)
assert c.post("/tickets", json={"title":"x","dept":"technical"}).status_code == 422
pytest -q test_all.py        # 7 passed
```

TestClient calls your app without starting a server: fast. Write one test per behaviour: success, bad input, not found, no key.

### Four useful extras

<table><thead><tr><th>Tool</th><th>Use</th><th>Gravrel scenario</th></tr></thead><tbody><tr><td><b>BackgroundTasks</b></td><td>do slow work AFTER replying</td><td>send &quot;ticket received&quot; email without making the customer wait</td></tr><tr><td><b>Middleware</b></td><td>code around every request</td><td>add <code>X-Process-Time-ms</code> header to measure speed</td></tr><tr><td><b>CORS</b></td><td>allow a browser app on another address to call you</td><td>React dashboard on localhost:3000 calling your API</td></tr><tr><td><b>async def</b></td><td>wait without blocking</td><td>calling another service or <code>await asyncio.sleep</code></td></tr></tbody></table>

> **Say This:** **def vs async def (simple rule):** plain `def` endpoints are run in a thread pool by FastAPI, so normal blocking code (like our SQLite calls) is fine. Use `async def` only when you `await` async libraries. Never put slow blocking code inside `async def`: it freezes everything.

> **Practice:** **Tasks (30 min):** (1) Run `uvicorn s07_extras:app --reload`, call `/slow-async` and look at the `X-Process-Time-ms` header in the `/docs` response. (2) Call `/notify?to=a@b.com`. (3) Write a new test in `test_all.py` for a missing ticket (404) and run `pytest -q`. (4) Break a test on purpose and read the failure message.

> **Teach It Back:** Explain BackgroundTasks to a restaurant owner: why not make the customer wait for the receipt printer?

## Level 8: ship it, cheat sheet, mini-project

### Run for real (not `--reload`)

```bash
uvicorn s06_db:app --host 0.0.0.0 --port 8000        # reachable from other machines
docker build -t gravrel-tickets . ; docker run -p 8000:8000 gravrel-tickets   # Dockerfile provided,
NOT tested by me
```

> **Careful:** **Before a public server:** real secrets in env vars, HTTPS in front (a reverse proxy such as Nginx or Caddy), a proper database, limit CORS origins, and keep `/docs` private if the API is internal \[ME, standard practice\].

### Common errors

<table><thead><tr><th>You see</th><th>Cause</th><th>Fix</th></tr></thead><tbody><tr><td>422 Unprocessable</td><td>wrong shape of data</td><td>read <code>loc</code> and <code>msg</code></td></tr><tr><td>&quot;Error loading ASGI app&quot;</td><td>wrong <code>file:app</code> name or wrong folder</td><td>cd into the lab folder, check name</td></tr><tr><td>&quot;Address already in use&quot;</td><td>old server still running</td><td>Ctrl+C or use another <code>--port</code></td></tr><tr><td>401</td><td>missing/wrong key</td><td>send <code>x-api-key</code> header</td></tr><tr><td>500</td><td>bug in your code</td><td>read the traceback in the server window</td></tr><tr><td>Table has no column</td><td>changed model, old .db file</td><td>delete .db (practice) or migrate</td></tr></tbody></table>

### Cheat sheet

```python
@app.get/post/put/patch/delete("/path")   route
x: int / q: str | None = None             path / query param
class M(BaseModel)                        body + validation
response_model=M, status_code=201         output shape + code
raise HTTPException(404, "msg")           error
Depends(fn)                               reuse helper (auth, db, paging)
BackgroundTasks / middleware / CORS       extras
TestClient(app)                           tests
```

### Final mini-project (2 hours, from a BLANK file)

> **Practice:** **Build "Gravrel Servers API":** a server has `name` (3-40 chars), `region` (Enum: bhubaneswar, mumbai), `cpu` (1-64), `status` (running/stopped). Endpoints: create, list with `?region=`, get one (404), `PATCH /servers/{id}/stop`, delete, API key on writes, SQLite storage, 5 tests. Rule: no copying; look at your notes only when stuck. When done, explain the request flow to someone for 2 minutes.

### 7-day plan (30-40 min a day)

<table><thead><tr><th>Day</th><th>Do</th></tr></thead><tbody><tr><td>1</td><td>Parts 0-2 (hello, docs)</td></tr><tr><td>2</td><td>Part 3 (params)</td></tr><tr><td>3</td><td>Part 4 (models, 422)</td></tr><tr><td>4</td><td>Part 5 (CRUD)</td></tr><tr><td>5</td><td>Parts 6 (Depends, auth)</td></tr><tr><td>6</td><td>Parts 7-8 (database, tests)</td></tr><tr><td>7</td><td>Part 9 mini-project start; finish next day</td></tr></tbody></table>

<table><tbody><tr><td>Flashcards</td></tr><tr><td><b>Q</b></td><td><b>A</b></td></tr><tr><td>Uvicorn vs FastAPI?</td><td>server that listens vs framework that routes and validates</td></tr><tr><td>Where do /docs come from?</td><td>generated from your code and type hints (OpenAPI)</td></tr><tr><td>Why 422?</td><td>request data did not match the model/type</td></tr><tr><td>Path vs query?</td><td>identify one thing vs filter a list</td></tr><tr><td>Why response_model?</td><td>controls and filters what leaves the API</td></tr><tr><td>What does Depends do?</td><td>runs a helper first and injects its result</td></tr><tr><td>def vs async def?</td><td>def runs in a thread pool; async only with await</td></tr></tbody></table>

Your 60-second script

> **Say This:** "FastAPI is a Python framework for building web APIs. Uvicorn runs it; I define endpoints with decorators, and the type hints and Pydantic models validate input automatically, so bad data gets a clear 422 before my code runs. It writes interactive docs for free. I reuse logic like API-key checks and database sessions with Depends, store data with SQLAlchemy, and protect behaviour with TestClient tests. I built a tickets API step by step: params, validation, CRUD, auth, database."

**Verified by running:** all 7 lab tests; a live server with real requests (422, 404, /docs 200, OpenAPI 3.1.0); FastAPI 0.143.3, Pydantic v2, SQLAlchemy 2.1. **Not verified:** PowerShell command behaviour on your PC, Dockerfile, anything about deployment hosts. FastAPI changes often: check fastapi.tiangolo.com for your installed version.
