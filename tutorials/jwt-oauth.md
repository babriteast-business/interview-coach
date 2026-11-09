---
title: JWT & OAuth
group: APIs & backend
order: 17
blurb: The signed ID card, and how apps get permission
tagline: the signed ID card, and how apps get permission
about: Build a token by hand, a login API, refresh tokens, and a full OAuth flow with PKCE break every token on purpose — all code was run by me
---

## How to use this tutorial

**Security topics are usually memorised as words ("bearer", "scope", "refresh") without being understood.** Practice fixes that, because you can break a token and watch the server say no. Four tweaks:

1. **Separate the two ideas first. JWT is a format** (a signed ID card). **OAuth is a process** (how an app gets permission without ever seeing your password). Mixing them up is the number-one confusion. Part 1 fixes it.
2. **Hotel key-card picture.** The front desk checks your ID once and gives a card with an expiry date. Doors only read the card. Login → token → protected routes.
3. **Attack it yourself.** Tamper, expire, replay, reuse. You only trust security you have tried to break.
4. **Honest limits.** I cannot sign in to Google or GitHub from my sandbox, so OAuth is practised against a small **local "provider"** that I built and tested (with PKCE). The real-provider steps at the end are general guidance, marked untested.

> **Careful:** **What is tested, honestly.** 5 pytest tests pass (hand-made token, all failure cases, login API with roles, refresh rotation, OAuth flow with three blocked attacks). I also ran a real login server and sent real requests; outputs below are copied. Versions: PyJWT 2.14.0, FastAPI 0.143.3, Python 3.13. **Not tested:** real Google/GitHub sign-in, browsers, PowerShell on your PC. The lab uses **fake users and practice secrets**; never reuse them.

### Setup (PowerShell, 3 min)

```powershell
cd C:\Users\god
Expand-Archive JWT_OAuth_Practice_Lab.zip -DestinationPath jwt
cd jwt\lab
python -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
pytest -q test_all.py           # expect: 5 passed
```

> **Tip:** **Cycle per level (20-30 min):** read → run the file → do the TASK box → close the page and explain aloud.

## The big picture

<table><thead><tr><th>Word</th><th>Question it answers</th><th>Hotel</th></tr></thead><tbody><tr><td><b>Authentication</b></td><td>who are you?</td><td>front desk checks your ID</td></tr><tr><td><b>Authorization</b></td><td>what may you do?</td><td>your card opens room 204 but not the safe</td></tr><tr><td><b>JWT</b></td><td>a token format: signed JSON</td><td>the card itself, with a signature the doors can check</td></tr><tr><td><b>OAuth 2.0</b></td><td>a processto let App A act for you at Service B without your password</td><td>you tell the desk &quot;give my friend a card for room 204 only, 1 hour&quot;</td></tr><tr><td><b>OpenID</b><br><b>Connect</b></td><td>OAuth plus &quot;who is this user&quot; (an ID token)</td><td>&quot;Sign in with Google&quot; [general knowledge]</td></tr></tbody></table>

```diagram steps
plain: user + pass
blue: login (check)
green: JWT token
plain: send in every request: | Authorization: Bearer <token>
```

### Why tokens instead of server-side sessions?

<table><thead><tr><th></th><th>Session (server remembers)</th><th>JWT (card carries the facts)</th></tr></thead><tbody><tr><td>Server lookup per request</td><td>yes, needs a store</td><td>no, just verify the signature</td></tr><tr><td>Cancel one login now</td><td>easy (delete session)</td><td>hard until it expires, so keep tokens short-lived</td></tr><tr><td>Good for</td><td>classic websites</td><td>APIs, mobile apps, many services</td></tr></tbody></table>

> **Teach It Back:** **(30 s)** Explain authentication vs authorization using the hotel, then say in one sentence what JWT is and what OAuth is.

## Level 1: what is inside a JWT (`j01_jwt_anatomy.py`)

A JWT is three pieces joined by dots: **header.payload.signature**. We build one with only the Python standard library.

```
h = b64url(json.dumps({"alg":"HS256","typ":"JWT"}))
p = b64url(json.dumps({"sub":"asha","role":"user","exp":4102444800}))
sig = hmac.new(SECRET, f"{h}.{p}".encode(), hashlib.sha256).digest()
token = f"{h}.{p}.{b64url(sig)}"
```

```bash
python j01_jwt_anatomy.py
```

**Real output:**

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhc2hhIiwi...
HEADER : {"alg":"HS256","typ":"JWT"}
PAYLOAD: {"sub":"asha","role":"user","exp":4102444800}   <-- anyone can read this. NOT secret!
PyJWT accepts my hand-made token: {'sub': 'asha', 'role': 'user', 'exp': 4102444800}
forged token rejected: Signature verification failed
```

<table><thead><tr><th>Part</th><th>Holds</th><th>Protected?</th></tr></thead><tbody><tr><td>header</td><td>algorithm + type</td><td>no (readable)</td></tr><tr><td>payload (claims)</td><td>who, role, expiry...</td><td><b>no: only base64, anyone can decode it</b></td></tr><tr><td>signature</td><td>HMAC of header+payload with the secret key</td><td>proves nobody changed it</td></tr></tbody></table>

> **Say This:** **The most important sentence of this whole topic:** a JWT is **signed, not encrypted**. Anyone can read the payload. The signature only guarantees it was not changed. So never put passwords or secrets inside.

> **Practice:** **Tasks (20 min):** (1) Run it. (2) Paste the token into any JWT decoder website **only the practice token** and see the payload. (3) Change the role to `admin` in the payload but keep the signature (the script does this) and see the rejection. (4) Change one letter of the secret in `verify` and see failure. (5) Explain: why can the server trust the payload without a database lookup?

> **Key idea:** JWT = header.payload.signature. Signed, NOT encrypted. Change one byte → signature fails.

> **Teach It Back:** Explain to a shopkeeper why a signed note can be read by anyone yet cannot be edited without detection.

## Level 2: claims and every way verification fails (`j02_pyjwt.py`)

<table><thead><tr><th>Claim</th><th>Meaning</th></tr></thead><tbody><tr><td><code>sub</code></td><td>subject: who the token is about</td></tr><tr><td><code>exp</code> / <code>iat</code></td><td>expires at / issued at (Unix time)</td></tr><tr><td><code>iss</code></td><td>issuer: who made it</td></tr><tr><td><code>aud</code></td><td>audience: which API it is meant for</td></tr><tr><td><code>jti</code></td><td>unique token id (used for revocation, Level 4)</td></tr></tbody></table>

```
jwt.decode(token, SECRET, algorithms=["HS256"],      # ALWAYS pin the algorithm
           issuer=ISSUER, audience=AUDIENCE,
           options={"require": ["exp", "sub"]})
```

```bash
python j02_pyjwt.py
```

**Real results:**

<table><thead><tr><th>Case</th><th>Exception</th></tr></thead><tbody><tr><td>expired</td><td><code>ExpiredSignatureError</code></td></tr><tr><td>wrong secret / tampered</td><td><code>InvalidSignatureError</code></td></tr><tr><td>garbage text</td><td><code>DecodeError</code></td></tr><tr><td>token for another API</td><td><code>InvalidAudienceError</code></td></tr><tr><td>unsigned token ( <code>alg: none</code> )</td><td><code>InvalidAlgorithmError</code> (because we pinned HS256)</td></tr></tbody></table>

> **Careful:** **Classic attack:** an attacker sends a token whose header says `alg: none` (no signature) hoping the server believes it. Pinning `algorithms=[...]` is what stops it. Never read the algorithm from the token itself.

> **Practice:** **Tasks (25 min):** (1) Run it and match each line to the table. (2) Make a token with `minutes=0.05` (3 seconds), sleep 4 s, verify: see expiry. (3) Remove `audience=` from verify and see the audience error change (a token with `aud` but no audience check is rejected). (4) Add a custom claim `"plan":"pro"` and read it after decode. (5) Why is a long secret important? (answer: short secrets can be guessed offline; PyJWT warns under 32 bytes for HS256).

> **Teach It Back:** Name 4 ways a token can be rejected and what each protects against.

## Level 3: a real login API with roles (`j03_login_api.py`)

Scenario: Gravrel dashboard. Users log in, get a token, call protected routes. Admins get extra routes.

<table><thead><tr><th>Piece</th><th>Code idea</th></tr></thead><tbody><tr><td>store passwords safely</td><td>never plain text; salted slow hash ( <code>hashlib.scrypt</code> here; many teams use argon2/bcrypt libraries [general]).</td></tr><tr><td>login</td><td><code>POST /token</code> with form fields username + password → <code>{&quot;access_token&quot;: ...,</code> <code>&quot;token_type&quot;: &quot;bearer&quot;}</code></td></tr><tr><td>protect a route</td><td><code>Depends(current_user)</code> decodes and checks the token</td></tr><tr><td>roles</td><td><code>Depends(require_role(&quot;admin&quot;))</code></td></tr></tbody></table>

```python
def current_user(token: str = Depends(oauth2)):
    try: data = jwt.decode(token, SECRET, algorithms=["HS256"], options={"require": ["exp","sub"]})
    except jwt.ExpiredSignatureError: raise HTTPException(401, "Token expired", headers={"WWW-
Authenticate": "Bearer"})
    except jwt.InvalidTokenError:     raise HTTPException(401, "Invalid token", headers={"WWW-
Authenticate": "Bearer"})
```

```powershell
uvicorn j03_login_api:app --reload
# browser: http://127.0.0.1:8000/docs  -> Authorize (asha / asha-pass)
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/token -Body
@{username="asha";password="asha-pass"}
Invoke-RestMethod http://127.0.0.1:8000/me -Headers @{Authorization="Bearer $($r.access_token)"}
```

**Real results from a live server:** login → 200, `token_type bearer`; `/me` → `{'username':'asha','role':'user'}`; `/admin/stats` as asha → **403** `Not enough permissions`; `/me` with no token → **401** `Not authenticated`; wrong password → `Incorrect username or password` (same message whether the user exists or not, so attackers learn nothing).

> **Say This:** **401 vs 403:** 401 = "I don't know who you are" (no or bad token). 403 = "I know you, but you may not do this" (wrong role).

> **Careful:** FastAPI calls this helper `OAuth2PasswordBearer` because it follows the OAuth2 "password" style. That style (app sees the password) is fine for **your own first-party login**, but must not be used for third-party apps; that is what the real OAuth flow in Level 5 is for \[general knowledge: newer OAuth guidance drops it\].

> **Practice:** **Tasks (30 min):** (1) Log in as asha and admin; call `/me` and `/admin/stats` with each. (2) Set `ACCESS_MINUTES = 0.1`, log in, wait, call `/me`: "Token expired". (3) Add a route `/tickets` only for role `user` or `admin`. (4) Add a third user with a role `support` and a route only for them. (5) Move the secret to the env var: `$env:GRAVREL_JWT_SECRET = "a-long-random-secret-of-32-plus-chars"` and restart; old tokens now fail. Why?

> **Teach It Back:** Explain 401 vs 403 with a security guard at an office gate.

## Level 4: access + refresh tokens, rotation, logout (`j04_refresh.py`)

**Problem:** a JWT cannot be cancelled before it expires. A long life is dangerous if stolen; a short life forces constant logins. **Answer: two tokens.**

<table><thead><tr><th>Token</th><th>Life</th><th>Sent to</th><th>Job</th></tr></thead><tbody><tr><td><b>access</b></td><td>minutes (5)</td><td>every API call</td><td>proves who you are right now</td></tr><tr><td><b>refresh</b></td><td>days (7)</td><td>only the <code>/refresh</code> route</td><td>gets a new access token</td></tr></tbody></table>

**Rotation:** every time you use a refresh token it is **revoked** and a new pair is issued. If an attacker replays an old refresh token, it fails. Logout = revoke the refresh token's `jti`. The `type` claim stops a refresh token being used as an access token. All of this is tested (reuse → 401, wrong type → 401, after logout → 401).

```yaml
REVOKED: set[str] = set()      # jti values; real apps use Redis or a DB table with expiry
d = decode(refresh_token, "refresh"); REVOKED.add(d["jti"]); return issue_pair(d["sub"])
```

```bash
uvicorn j04_refresh:app --reload     # use /docs; login with username asha, password pass-asha (FAKE
check)
```

> **Practice:** **Tasks (30 min):** (1) Login, call `/me` with the access token. (2) Try the refresh token as a bearer on `/me`: "Wrong token type". (3) Call `/refresh` twice with the same refresh token: second fails. (4) Logout, then refresh: fails. (5) Restart the server: revoked tokens are forgotten (it is an in-memory set). Why is this a real problem? (answer: revoked tokens become valid again; use a database).

> **Careful:** **Where does the browser keep tokens? \[general knowledge, not tested here\]:** localStorage is readable by any script on the page (XSS risk); an `HttpOnly` cookie is not readable by scripts but needs CSRF protection. Many teams keep the refresh token in an HttpOnly cookie. Decide per app and learn the trade-off.

> **Teach It Back:** Explain why two tokens are safer than one long-lived token, using a hotel day-pass and a master voucher.

## Level 5: OAuth 2.0 Authorization Code flow with PKCE (`j05_oauth_pkce.py`)

Scenario: **Gravrel Web** (a client app) wants to read **your profile** at a login provider, without ever seeing your password. This is "Sign in with ..." and "connect your account".

<table><thead><tr><th>Actor</th><th>Role</th><th>In my lab</th></tr></thead><tbody><tr><td>Resource owner</td><td>you, the user</td><td>simulated by <code>?user=asha</code></td></tr><tr><td>Client</td><td>the app that wants access</td><td><code>run_flow()</code></td></tr><tr><td>Authorization server</td><td>login + consent, issues tokens</td><td><code>auth_app</code></td></tr><tr><td>Resource server</td><td>the API holding your data</td><td><code>resource_app</code></td></tr></tbody></table>

```diagram steps
plain: Client app
blue: Authorization server
green: Resource API
```

1 send user to /authorize (state + code\_challenge)

token

### The three safety devices

<table><thead><tr><th>Device</th><th>Stops</th><th>How</th></tr></thead><tbody><tr><td><b>state</b></td><td>CSRF (someone tricks you into finishing THEIR login)</td><td>client makes a random value, checks it comes back unchanged</td></tr><tr><td><b>PKCE</b></td><td>a stolen <code>code</code> being used by an attacker</td><td>client keeps a secret <b>verifier</b>; sends only its SHA-256 <b>challenge</b> first; the server checks the verifier at the end</td></tr><tr><td><b>one-time</b><br><b>short code</b></td><td>replay</td><td>code is deleted on first use and expires in 60 s</td></tr></tbody></table>

```bash
python j05_oauth_pkce.py
```

**Real output:** steps 1-5 print, ending with `{'user': 'asha', 'scope': 'profile'}`. Then the three attacks: `tamper_state` → "state mismatch: possible CSRF, abort"; `wrong_verifier` → "invalid\_grant: PKCE verifier mismatch"; `reuse_code` → "invalid\_grant".

> **Say This:** **Scope:** the token says what the app may do (`profile`), not just who you are. Ask for the least permission needed.

> **Practice:** **Tasks (35 min):** (1) Run it, match each printed step to the diagram. (2) In `make_pkce` print verifier and challenge; confirm the challenge is the SHA-256 of the verifier (the server recomputes it). (3) Make the code expire: set 60 to 0 in `/authorize` and see the failure. (4) Change the client's `redirect_uri` by one letter and see the 400. (5) Add a second scope `email` and make `/api/profile` return it only when the token has it. (6) Say aloud why a thief who steals only the `code` still cannot get a token.

> **Key idea:** Code + PKCE verifier → token. state stops CSRF. Code is one-time. The app never sees your password.

> **Teach It Back:** Explain OAuth to a non-technical friend: "valet key" for a car that opens the door and starts the engine but not the boot.

## Going real, checklist, mini-project, plan

### Using a real provider (Google / GitHub) [general guidance, NOT tested by me]

1. Register your app in the provider's developer console; note the client id (and secret if it gives one).
2. Register the exact redirect URI (for local practice, an http://localhost address).
3. Use a maintained library (for example **Authlib**) instead of hand-writing the flow; the flow you practised is what it does for you.
4. Keep client secrets in environment variables, never in Git.

> **Careful:** Provider screens and names change. Read the provider's current docs; if a step differs from what I wrote, trust the docs and tell me.

### Security checklist (production)

<table><thead><tr><th>Do</th><th>Because</th></tr></thead><tbody><tr><td>HTTPS only</td><td>tokens in the clear can be stolen</td></tr><tr><td>short access tokens (minutes)</td><td>stolen token dies soon</td></tr><tr><td>pin algorithms, check <code>exp</code> , <code>iss</code> , <code>aud</code></td><td>stops forged and misrouted tokens</td></tr><tr><td>long random secret from env, rotate it</td><td>secret leak = anyone can mint tokens</td></tr><tr><td>no secrets in the payload</td><td>payload is readable</td></tr><tr><td>rate-limit login</td><td>stops password guessing</td></tr><tr><td>for several services, consider asymmetric keys (RS256/ES256)</td><td>services can verify with a public key and cannot mint tokens [general]</td></tr></tbody></table>

### Common errors

<table><thead><tr><th>You see</th><th>Cause</th></tr></thead><tbody><tr><td>401 &quot;Not authenticated&quot;</td><td>missing <code>Authorization: Bearer ...</code> header</td></tr><tr><td>ExpiredSignatureError</td><td>token lifetime over; refresh or log in again</td></tr><tr><td>InvalidSignatureError</td><td>different secret between issuer and verifier, or tampering</td></tr><tr><td>InvalidAudienceError</td><td>token meant for another API</td></tr><tr><td>422 on <code>/token</code></td><td>login must be form data, not JSON (needs <code>python-multipart</code> )</td></tr></tbody></table>

### Cheat sheet

```
jwt.encode(claims, SECRET, algorithm="HS256")
jwt.decode(tok, SECRET, algorithms=["HS256"], issuer=, audience=, options={"require": [...]})
Authorization: Bearer <token>     401 = who are you?   403 = not allowed
access (minutes) + refresh (days, rotate, revoke by jti)
OAuth code flow: /authorize(state, challenge) -> code -> /token(code, verifier) -> access token
```

### Final mini-project (2 hours, blank file)

> **Practice:** **"Gravrel Vault API":** users `register` (hashed passwords), `login` (access 5 min + refresh), `refresh` with rotation, `logout`. Routes: `/notes` (any user, only their own notes), `/admin/users` (admin role). Add tests for: no token (401), wrong role (403), expired token, replayed refresh token, and one user reading another's note (must fail: 404 or 403). Then explain the full flow in 2 minutes without notes.

### 7-day plan (25-30 min a day)

<table><thead><tr><th>Day</th><th>Do</th></tr></thead><tbody><tr><td>1</td><td>Parts 0-1</td></tr><tr><td>2</td><td>Level 1 anatomy</td></tr><tr><td>3</td><td>Level 2 failures</td></tr><tr><td>4</td><td>Level 3 login API</td></tr><tr><td>5</td><td>Level 4 refresh</td></tr><tr><td>6</td><td>Level 5 OAuth + PKCE</td></tr><tr><td>7</td><td>Mini-project and teach-back</td></tr></tbody></table>

### Flashcards

<table><thead><tr><th>Q</th><th>A</th></tr></thead><tbody><tr><td>JWT vs OAuth?</td><td>token format vs permission-granting process</td></tr><tr><td>Is a JWT encrypted?</td><td>No, signed; payload is readable</td></tr><tr><td>Three parts?</td><td>header.payload.signature</td></tr><tr><td>Why pin algorithms?</td><td>stops <code>alg: none</code> and algorithm-swap attacks</td></tr><tr><td>401 vs 403?</td><td>unknown identity vs not allowed</td></tr><tr><td>Why refresh tokens?</td><td>short access life without constant logins</td></tr><tr><td>What does PKCE protect?</td><td>a stolen authorization code</td></tr><tr><td>What does state protect?</td><td>CSRF in the redirect</td></tr></tbody></table>

### Your 60-second script

> **Say This:** "A JWT is a signed JSON token with a header, payload and signature. It is signed, not encrypted, so anyone can read it but nobody can change it without breaking the signature. After login the server gives the client a short-lived access token that it sends as a Bearer header; I verify the signature, expiry, issuer and audience, pinning the algorithm, and use 401 for unknown users and 403 for missing roles. A longer refresh token gets new access tokens and is rotated and revocable. OAuth is a different thing: a process where an app gets permission from a provider without seeing my password. In the authorization code flow with PKCE the app redirects me to the provider, receives a one-time code, and swaps it plus its secret verifier for an access token, with a state value to stop CSRF."

**Verified by running:** all 5 tests; live login server with real requests (200, 401, 403 and messages above); hand-built token accepted by PyJWT; OAuth+PKCE flow and three blocked attacks (PyJWT 2.14.0, FastAPI 0.143.3, Python 3.13). **Not verified:** real Google/GitHub flows, browser token storage advice, argon2/bcrypt and RS256 advice (general knowledge), PowerShell on your PC. Security guidance changes: check current OWASP and provider docs before shipping.
