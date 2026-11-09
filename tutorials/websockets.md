---
title: WebSockets
group: APIs & backend
order: 18
blurb: A phone call between browser and server, not a letter
tagline: a phone call between browser and server, not a letter
about: Echo, chat room, FastAPI rooms, live sensor feed, reconnecting clients two PowerShell windows, one level at a time — all code was run by me
---

## How to use this tutorial

**WebSockets are hard to read about and easy to learn by watching two windows talk,** so practice-first is exactly right. Four tweaks:

1. **Phone call vs letter.** HTTP is a letter: ask, wait, one reply, done. A WebSocket is a phone call: the line stays open and either side can speak any time. Every level adds one feature to the call.
2. **Two windows, always.** Server in window 1, client in window 2. You see messages cross live.
3. **Your own projects as scenarios:** a chat room (like Gravrel Room) and a live server-room temperature feed (like your NodeMCU monitor), plus the part beginners skip: disconnects, reconnects and keepalives.
4. **Two stacks:** the plain `websockets` library (to understand the protocol) and FastAPI WebSockets (what you will use at work).

> **Careful:** **What is tested, honestly.** 5 pytest tests pass (live servers on real sockets). I also ran real server + client processes and copied their output into these notes. Versions: websockets 17.3, FastAPI 0.143.3, Python 3.13. **Not tested:** the browser page `index.html` in a real browser, your Windows PowerShell session, and any deployment behind a proxy. The `websockets` library changed its API over time (new code uses `websockets.asyncio.server/client`); old tutorials may use the old style.

### Setup (PowerShell, 3 min)

```powershell
cd C:\Users\god
Expand-Archive WebSockets_Practice_Lab.zip -DestinationPath ws
cd ws\lab
python -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
pytest -q test_all.py           # expect: 5 passed
```

> **Tip:** **Cycle per level (20-30 min):** read → run server + client in two windows → do the TASK box → close the page and explain aloud. For "window 2" open a new PowerShell and run `cd C:\Users\god\ws\lab ; .venv\Scripts\Activate.ps1`.

## The big picture

HTTP = letters WebSocket = phone call ask

```diagram flow
plain: client
plain: server
plain: client
plain: server
```

answer, then the line is closed open line: anyone speaks any time

1. client sends a normal HTTP request with "Upgrade: websocket"
2. server answers 101 Switching Protocols (the handshake)
3. same TCP connection now carries small "frames" both ways until someone closes it

<table><thead><tr><th>Need</th><th>Use</th><th>Gravrel example</th></tr></thead><tbody><tr><td>get data once</td><td>normal HTTP / REST</td><td>list my tickets</td></tr><tr><td>server must tell you the moment something happens</td><td><b>WebSocket</b></td><td>live temperature alert, new chat message</td></tr><tr><td>both sides talk often, low delay</td><td><b>WebSocket</b></td><td>chat, multiplayer, live cursors</td></tr><tr><td>only server → browser stream, simple</td><td>Server-Sent Events (alternative) [ME]</td><td>progress bar, news feed</td></tr></tbody></table>

### Words to remember

<table><thead><tr><th>Word</th><th>Meaning</th></tr></thead><tbody><tr><td><code>ws://</code> / <code>wss://</code></td><td>like http / https; use <b>wss</b> (encrypted) on the internet</td></tr><tr><td>frame / message</td><td>one unit sent (text or binary)</td></tr><tr><td>ping / pong</td><td>keepalive frames to prove the line is alive</td></tr><tr><td>close code</td><td>reason number when ending: 1000 normal, 1001 going away, 1008 policy violation, 1011 server error</td></tr><tr><td>asyncio / <code>async</code> <code>for</code></td><td>Python&#x27;s way to wait for many connections at once without threads</td></tr></tbody></table>

> **Teach It Back:** **(30 s)** Explain letter vs phone call with a real example from your own life, then say why a chat app needs the phone call.

## Level 1: echo server and client (`w01_echo_server.py`, `w01_client.py`)

```python
async def handler(ws):                 # runs once per connected client
    async for msg in ws:               # loop ends when the client disconnects
        print("got:", msg)
        await ws.send(f"echo: {msg}")
async with serve(handler, "localhost", 8765) as server:
    await server.serve_forever()
```

Read: `serve` starts listening. For every client it starts `handler`. `async for msg in ws` means "wait for the next message, again and again". `await ws.send` sends. `await` = "wait here, but let others run".

### Run (two windows)

```bash
# window 1
python w01_echo_server.py          # echo server on ws://localhost:8765
# window 2
python w01_client.py hello gravrel
```

**Real output:** window 2 prints `echo: hello` and `echo: gravrel`; window 1 prints `got: hello` and `got: gravrel`.

> **Practice:** **Tasks (20 min):** (1) Run both windows as above. (2) Change the reply to upper case: `msg.upper()`; restart the server and test. (3) Start the client with no server running: read the error ("connection refused"-style). (4) Make the server refuse messages longer than 20 characters by replying "too long". (5) Run two clients at the same time: does each get only its own echo?

> **Key idea:** serve(handler) + async for msg in ws + await ws.send(). One handler call per client.

> **Teach It Back:** Explain what `await` does using a waiter who serves many tables.

## Level 2: chat room with broadcast (`w02_chat_server.py`, `w02_chat_client.py`)

Scenario: like Gravrel Room. Many people, one room, everyone sees every message.

```python
CONNECTED = set()                         # everyone in the room
async def handler(ws):
    name = (await ws.recv()).strip()      # first message = the name
    CONNECTED.add(ws)
    broadcast(CONNECTED, f"* {name} joined ({len(CONNECTED)} online)")
    try:
        async for text in ws: broadcast(CONNECTED, f"{name}: {text}")
    finally:
        CONNECTED.discard(ws)             # ALWAYS clean up
        broadcast(CONNECTED, f"* {name} left ({len(CONNECTED)} online)")
```

Key idea: the server keeps a **set of open connections** and loops over it to send to all. `finally` guarantees removal even when the client crashes. Test confirmed: join → "\* Asha joined (1 online)", second user → "(2 online)", message reaches both, leaving → "\* Ravi left (1 online)".

```bash
# window 1
python w02_chat_server.py
# windows 2 and 3
python w02_chat_client.py Asha
python w02_chat_client.py Ravi        # type a line + Enter; Ctrl+C to leave
```

> **Practice:** **Tasks (25 min):** (1) Chat between two windows. (2) Close one with Ctrl+C and watch the "left" message in the other. (3) Add a command: if text is `/who`, send the list of names only to the sender (store names in a dict `ws -> name`). (4) Add a 200-character limit. (5) Kill the server (Ctrl+C) while clients are open and read what the clients show.

> **Careful:** A bug beginners make: forgetting to remove closed connections from the set. Then the server keeps sending to dead sockets and memory grows. Always use `try/finally`.

> **Teach It Back:** Draw the set CONNECTED on paper with 3 users, then show what changes when one leaves.

## Level 3: FastAPI WebSockets with rooms and a token (`w03_fastapi_rooms.py`, `index.html`)

Same idea, but now inside FastAPI: multiple named rooms, JSON messages, a token check, and a normal HTTP route that reads WebSocket state.

```python
@app.websocket("/ws/{room}")
async def ws_room(ws: WebSocket, room: str, name: str = "anon", token: str = ""):
    if token != TOKEN:
        await ws.close(code=1008); return        # reject before accepting
    await mgr.join(room, ws)                     # does ws.accept() inside
    try:
        while True:
            data = await ws.receive_json()       # {"text": "..."}
            await mgr.send_room(room, {"type":"msg","name":name,"text":data["text"]})
    except WebSocketDisconnect:
        mgr.leave(room, ws)
```

```powershell
# window 1
uvicorn w03_fastapi_rooms:app --reload
# browser: open index.html (double-click), click Connect in two tabs
# check state over HTTP:
Invoke-RestMethod http://127.0.0.1:8000/rooms/lobby/online
```

**Real results (Python client against the live server):** good token → `{"type":"join","name":"Asha","online":1}` then my message came back as `{"type":"msg","name":"Asha","text":"hello"}`. Bad token → `server rejected WebSocket connection: HTTP 403` (closing before accept shows up as a rejected handshake).

<table><thead><tr><th>Choice</th><th>Why</th></tr></thead><tbody><tr><td>JSON messages with a <code>type</code> field</td><td>one connection can carry many kinds of events (msg, join, leave)</td></tr><tr><td>token in the query string</td><td>browsers cannot set custom headers on a WebSocket; but URLs can end up in logs, so real apps use short-lived tokens [ME]</td></tr><tr><td>manager class</td><td>one place that knows rooms and members</td></tr></tbody></table>

> **Careful:** **Untested by me:** the browser page. If a tab shows "\[closed code 1006\]" the server was not reachable; check uvicorn is running on port 8000.

> **Practice:** **Tasks (30 min):** (1) Open two browser tabs in room "lobby" and one in room "dev": messages stay inside rooms. (2) Open the online URL before and after closing a tab. (3) Change the token in `index.html` and see the closed code. (4) Add a `"type":"typing"` message the client can send and the server forwards. (5) Escape HTML in `index.html` output (use `textContent`): why would raw `innerHTML` be a security hole? \[answer: someone can send a script tag in a chat message\].

> **Teach It Back:** Why do we use a `type` field in every JSON message?

## Level 4: server push, the live sensor feed (`w04_monitor_push.py`)

Scenario: your server-room monitor. The client does not ask. The server **pushes** a reading every second. This is what a polling HTTP page cannot do cleanly.

```python
async def sensor_handler(ws, interval=1.0, seed=7):
    temp = 27.0
    try:
        while True:
            temp += rnd.uniform(-0.5, 1.2)
            await ws.send(json.dumps({"room":"rack-1","temp_c":round(temp,1)}))
            await asyncio.sleep(interval)        # NON-blocking wait
    except ConnectionClosed: pass                # client left: stop quietly
```

```bash
# window 1                         # window 2
python w04_monitor_push.py         python w04_monitor_push.py client
```

**Real output (window 2):** `temp 27.1 C`, `temp 26.8 C`, `temp 27.4 C`... ten lines, one per second. The client prints `<-- ALERT` when a reading exceeds the limit (default 27.3 in my file).

> **Say This:** **Important:** use `await asyncio.sleep()`, never `time.sleep()`. `time.sleep` freezes the whole server so every other client stops getting data.

> **Practice:** **Tasks (25 min):** (1) Run it and spot the ALERT lines. (2) Change the limit to 30 and see no alerts.

3. Make the interval 0.2 s. (4) Open two clients: does each get its own stream? (5) Make the server send `{"alert": true}` itself when temp is above 28 (decide: should the server or the client decide? write one reason). (6) Replace the random temperature with a real reading from a file or your NodeMCU later.

> **Key idea:** Server push = server sends on its own schedule inside a loop with await asyncio.sleep().

> **Teach It Back:** Why is a WebSocket better than refreshing a page every second for a temperature display?

## Level 5: real networks drop, so reconnect (`w05_resilient_client.py`)

Wi-Fi blips, servers restart, phones sleep. A beginner client works until the first drop, then stays dead. A real client reconnects and keeps the line alive.

```
async for ws in connect(uri, ping_interval=20, ping_timeout=20):   # new connection each loop
    try:
        async for msg in ws: handle(msg)
    except ConnectionClosed:
        continue                       # library waits (backoff), then reconnects
```

<table><thead><tr><th>Piece</th><th>Meaning</th></tr></thead><tbody><tr><td><code>async for ws in connect()</code></td><td>the library reconnects automatically and waits longer after repeated failures</td></tr><tr><td><code>ping_interval / ping_timeout</code></td><td>send a ping every N seconds; if no pong, treat the line as dead</td></tr><tr><td>backoff</td><td>wait 1 s, 2 s, 4 s... so a down server is not hammered</td></tr></tbody></table>

**Tested:** my test server dropped the first connection on purpose; the client reconnected (attempt 2) and received m0, m1, m2.

```bash
# window 1: start the sensor feed        # window 2: the resilient client
python w04_monitor_push.py              python w05_resilient_client.py
# now press Ctrl+C in window 1, wait 5 s, start it again: the client continues
```

> **Say This:** **Tested by me:** I started the feed, started this client, stopped the server after 4 readings, restarted it 3 s later: the client printed `connected, attempt 2` and continued with new readings, without any action from me. (The feed restarts its random series, so numbers repeat.)

> **Practice:** **Tasks (25 min):** (1) Do the stop/restart experiment above. (2) Find the `connected, attempt N` print in the file (turn `verbose` off and on). (3) In the chat client (Level 2) add the same reconnect idea and re-send the name after reconnecting (the server forgot you, so say who you are again). (4) Write down: what should a client do with messages it missed while offline? (answer: ask the server for history via HTTP after reconnecting \[ME\]).

> **Teach It Back:** Explain heartbeat and reconnect with the example of a phone call that drops in a tunnel.

## Level 6: production thinking, cheat sheet, mini-project

### Things that bite in production [ME, standard practice, not tested here]

<table><thead><tr><th>Problem</th><th>What to do</th></tr></thead><tbody><tr><td>Behind Nginx/Caddy</td><td>the proxy must pass the Upgrade headers, and long timeouts need setting; use <b>wss</b></td></tr><tr><td>More than one server process</td><td>a message arrives at process A but user is on B. Use a shared channel (for example Redis pub/sub) to fan out</td></tr><tr><td>Thousands of connections</td><td>each is memory; set limits, drop idle ones</td></tr><tr><td>Auth</td><td>check the token at connect time; expire it; never trust the <code>name</code> sent by the client</td></tr><tr><td>Slow client</td><td>one slow receiver must not block everyone: drop or disconnect it</td></tr><tr><td>Message size</td><td>limit it (the library has a default max size; tune it)</td></tr></tbody></table>

### Cheat sheet

```yaml
server:  async with serve(handler, host, port) as s: await s.serve_forever()
handler: async for msg in ws: await ws.send(x)       ws.recv()   ws.close()
client:  async with connect("ws://...") as ws: await ws.send(x); await ws.recv()
auto-reconnect: async for ws in connect(uri): ...
broadcast: keep a set of connections; broadcast(set, text)   (or loop and send)
FastAPI: @app.websocket("/ws")  await ws.accept()  receive_text/json  send_text/json
         except WebSocketDisconnect: cleanup
rules: always cleanup in finally | asyncio.sleep not time.sleep | JSON with "type" | wss in prod
```

### Common errors

<table><thead><tr><th>You see</th><th>Cause</th><th>Fix</th></tr></thead><tbody><tr><td>connection refused</td><td>server not running / wrong port</td><td>start the server first, check port</td></tr><tr><td>HTTP 403 on connect</td><td>server closed before accept (bad token)</td><td>check token and URL</td></tr><tr><td>ConnectionClosed</td><td>other side left</td><td>catch it, clean up, maybe reconnect</td></tr><tr><td>server freezes for everyone</td><td>blocking call ( <code>time.sleep</code> , slow DB) in async code</td><td>use await or a thread executor</td></tr><tr><td>closed code 1006 (browser)</td><td>abnormal drop, often no server</td><td>check server and URL</td></tr></tbody></table>

### Final mini-project (2 hours, from a blank file)

> **Practice:** **"Gravrel Status Board":** a FastAPI app where (a) a `POST /alerts` HTTP route (with an API key) accepts an alert like `{"server":"web1","level":"high"}` and (b) every browser connected to `/ws/board` instantly receives it as JSON and shows it in a list. Add: online-viewer count, a heartbeat message every 15 s, a reconnect in the browser JS (`onclose` → try again after 2 s), and 3 pytest tests with `TestClient.websocket_connect`. Explain the data flow for 2 minutes without notes. (Hint: the HTTP route calls the manager's `send_room`.)

### 7-day plan (25-30 min a day)

<table><thead><tr><th>Day</th><th>Do</th></tr></thead><tbody><tr><td>1</td><td>Parts 0-1 + Level 1</td></tr><tr><td>2</td><td>Level 2 chat</td></tr><tr><td>3</td><td>Level 3 FastAPI rooms</td></tr><tr><td>4</td><td>Level 4 server push</td></tr><tr><td>5</td><td>Level 5 reconnect</td></tr><tr><td>6</td><td>Part 7, start mini-project</td></tr><tr><td>7</td><td>Finish mini-project, teach it back</td></tr></tbody></table>

<table><tbody><tr><td>Flashcards</td></tr><tr><td><b>Q</b></td><td><b>A</b></td></tr><tr><td>HTTP vs WebSocket?</td><td>one request-reply then close vs an open two-way line</td></tr><tr><td>How does it start?</td><td>HTTP request with Upgrade, server answers 101, same connection continues</td></tr><tr><td>How to broadcast?</td><td>keep a set of open connections, send to each</td></tr><tr><td>Why try/finally?</td><td>remove the connection even when the client crashes</td></tr><tr><td>sleep inside async code?</td><td><code>await asyncio.sleep</code> , never <code>time.sleep</code></td></tr><tr><td>Purpose of ping/pong?</td><td>detect dead connections</td></tr><tr><td>Why a shared channel (Redis) at scale?</td><td>users sit on different server processes</td></tr></tbody></table>

Your 60-second script

> **Say This:** "HTTP is like sending letters: ask, get one answer, done. A WebSocket is a phone call: after a one-time upgrade handshake the connection stays open and either side can send at any moment. In Python I run a server with the websockets library or FastAPI, keep a set of connected clients, and loop over it to broadcast, always cleaning up in a finally block. For live data the server pushes on its own schedule with asyncio sleep. Real clients send heartbeats and reconnect with backoff, and in production I use wss behind a proxy and a shared channel like Redis when I run more than one process."

**Verified by running:** 5 tests (echo, chat join/broadcast/leave, FastAPI rooms with bad-token rejection and cleanup, sensor push, reconnect), plus real server/client processes for echo, sensor feed, stop/restart reconnect and FastAPI over the network (websockets 17.3, FastAPI 0.143.3, Python 3.13). **Not verified:** the browser page, PowerShell on your PC, anything under Production thinking (standard practice, from general knowledge). Library APIs change: check the websockets and FastAPI docs for your installed version.
