"""Interview Coach website.
Local:  python app.py  -> http://localhost:8000
Render: uvicorn app:app --host 0.0.0.0 --port $PORT  (see render.yaml)"""
import datetime
import json
import os
import random
import re
import threading
import time

from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))

import uvicorn  # noqa: E402
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, PlainTextResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import db  # noqa: E402
import llm  # noqa: E402
import prompts  # noqa: E402
import runner  # noqa: E402

DATA = os.path.join(BASE, "data")
COOKIE = "ic_session"
TRACKS = {"engineer": "AI Engineer", "architect": "AI Architect"}
ON_RENDER = bool(os.getenv("RENDER"))          # Render sets RENDER=true automatically
ADMIN_USER = os.getenv("ADMIN_USERNAME", "").strip()

app = FastAPI(title="Interview Coach")
db.init()
if not db.ensure_admin(ADMIN_USER, os.getenv("ADMIN_PASSWORD", "")):
    print("  WARNING: set ADMIN_USERNAME and ADMIN_PASSWORD to create the admin account.")


# ---------------- data files ----------------
def load_json(name, default):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


_bank_cache = {"at": 0, "items": []}


def questions():
    """Shipped bank (data/questions.json) + questions refreshed live into the database."""
    if time.time() - _bank_cache["at"] > 60:
        items = load_json("questions.json", [])
        seen = {q["id"] for q in items}
        try:
            with db.conn() as c:
                for r in c.execute("SELECT data FROM bank ORDER BY added"):
                    q = json.loads(r["data"])
                    if q["id"] not in seen:
                        seen.add(q["id"])
                        items.append(q)
        except Exception:
            pass
        _bank_cache.update(at=time.time(), items=items)
    return _bank_cache["items"]


def refresh_bank(trending_per_cat=0):
    """Pull new questions from the internet (+ optional AI trending set) into the database."""
    import refresh_questions as rq
    db.set_setting("refresh_status", "running")
    try:
        _bank_cache["at"] = 0
        base = list(questions())
        work = list(base)
        rq.fetch_sources(work)
        if trending_per_cat:
            rq.trending(work, trending_per_cat)
        new = work[len(base):]
        with db.conn() as c:
            for q in new:
                c.execute("INSERT INTO bank(id,data,added) VALUES(?,?,?) ON CONFLICT(id) DO NOTHING",
                          (q["id"], json.dumps(q, ensure_ascii=False), time.time()))
        db.set_setting("bank_refreshed", datetime.datetime.now().strftime("%d %b %Y, %H:%M"))
        db.set_setting("refresh_status", f"done: {len(new)} new questions")
    except Exception as e:
        db.set_setting("refresh_status", f"failed: {e}"[:300])
    finally:
        _bank_cache["at"] = 0


def _auto_refresh():
    """Once a week, on start-up, fetch the public question lists (free, no AI calls)."""
    try:
        last = float(db.get_setting("bank_refreshed_ts", "0"))
        if time.time() - last > 7 * 86400:
            db.set_setting("bank_refreshed_ts", str(time.time()))
            refresh_bank(0)
    except Exception:
        pass


threading.Thread(target=_auto_refresh, daemon=True).start()


def problems():
    return load_json("coding_problems.json", [])


def default_profile():
    p = os.path.join(DATA, "profile_template.md")
    with open(p, encoding="utf-8") as f:
        return f.read()


# ---------------- auth ----------------
def current_user(request: Request):
    u = db.session_user(request.cookies.get(COOKIE))
    if not u:
        raise HTTPException(401, "Please log in")
    return u


def admin_user(u=Depends(current_user)):
    if u["role"] != "admin":
        raise HTTPException(403, "Admin only")
    return u


def registration_open():
    return db.get_setting("registration_open", "1") == "1"


def ai_limit():
    return int(db.get_setting("ai_daily_limit", "15"))


def ai_guard(u):
    """Admin is unlimited. Other users get a daily AI-call allowance so they can't drain the free quota."""
    if u["role"] == "admin":
        db.add_usage(u["user_id"])
        return
    if db.usage_today(u["user_id"]) >= ai_limit():
        raise HTTPException(429, f"Daily AI limit reached ({ai_limit()} calls). Bank questions and coding tests still work.")
    db.add_usage(u["user_id"])


_fails = {}


def _throttle(request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0]
    now = time.time()
    hits = [t for t in _fails.get(ip, []) if now - t < 600]
    _fails[ip] = hits
    if len(hits) >= 8:
        raise HTTPException(429, "Too many failed attempts. Try again in 10 minutes.")
    return ip


def _set_cookie(response, uid):
    response.set_cookie(COOKIE, db.new_session(uid), httponly=True, samesite="lax",
                        secure=ON_RENDER, max_age=30 * 86400)


class Creds(BaseModel):
    username: str
    password: str


@app.get("/api/auth/status")
def auth_status(request: Request):
    u = db.session_user(request.cookies.get(COOKIE))
    return {"logged_in": bool(u), "username": u["username"] if u else None,
            "role": u["role"] if u else None, "can_register": registration_open()}


@app.post("/api/auth/register")
def register(c: Creds, request: Request):
    _throttle(request)
    if not registration_open():
        raise HTTPException(403, "Registration is closed right now.")
    name = c.username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", name) or len(c.password) < 8:
        raise HTTPException(400, "Username: 3-32 letters/numbers. Password: 8+ characters.")
    if name.lower() == ADMIN_USER.lower():
        raise HTTPException(400, "That username is taken")
    try:
        db.create_user(name, c.password, role="user", status="pending")
    except Exception:
        raise HTTPException(400, "That username is taken")
    return {"ok": True, "message": "Account created. The admin must approve it before you can log in."}


@app.post("/api/auth/login")
def login(c: Creds, request: Request, response: Response):
    ip = _throttle(request)
    row = db.get_user(c.username.strip())
    if not row or not db.check_password(row, c.password):
        _fails.setdefault(ip, []).append(time.time())
        raise HTTPException(401, "Wrong username or password")
    if row["status"] == "pending":
        raise HTTPException(403, "Your account is waiting for admin approval.")
    if row["status"] != "active":
        raise HTTPException(403, "This account is disabled.")
    _set_cookie(response, row["id"])
    return {"ok": True, "role": row["role"]}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    db.end_session(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE)
    return {"ok": True}


class PwIn(BaseModel):
    old: str
    new: str


@app.post("/api/auth/password")
def change_password(p: PwIn, u=Depends(current_user)):
    if u["role"] == "admin":
        raise HTTPException(400, "Admin password is set by ADMIN_PASSWORD on Render (Environment tab).")
    row = db.get_user(u["username"])
    if not db.check_password(row, p.old) or len(p.new) < 8:
        raise HTTPException(400, "Current password wrong, or new one under 8 characters")
    h, salt = db.hash_pw(p.new)
    with db.conn() as c:
        c.execute("UPDATE users SET pw_hash=?, salt=? WHERE id=?", (h, salt, u["user_id"]))
    return {"ok": True}


# ---------------- admin ----------------
@app.get("/api/admin/users")
def admin_users(a=Depends(admin_user)):
    day = time.strftime("%Y-%m-%d")
    with db.conn() as c:
        rows = c.execute(
            "SELECT u.id, u.username, u.role, u.status, u.trusted, u.created, "
            "(SELECT COUNT(*) FROM turns t WHERE t.user_id=u.id AND t.answered IS NOT NULL) AS answers, "
            "(SELECT n FROM ai_usage x WHERE x.user_id=u.id AND x.day=?) AS ai_today "
            "FROM users u ORDER BY u.id", (day,)).fetchall()
    return {"users": rows, "registration_open": registration_open(), "ai_daily_limit": ai_limit()}


class UserAction(BaseModel):
    action: str   # approve | disable | enable | trust | untrust | delete


@app.post("/api/admin/users/{uid}")
def admin_user_action(uid: int, body: UserAction, a=Depends(admin_user)):
    if uid == a["user_id"]:
        raise HTTPException(400, "You can't change the admin account here")
    with db.conn() as c:
        if body.action in ("approve", "enable"):
            c.execute("UPDATE users SET status='active' WHERE id=?", (uid,))
        elif body.action == "disable":
            c.execute("UPDATE users SET status='disabled' WHERE id=?", (uid,))
            c.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        elif body.action in ("trust", "untrust"):
            c.execute("UPDATE users SET trusted=? WHERE id=?", (1 if body.action == "trust" else 0, uid))
        elif body.action == "delete":
            for t in ("sessions", "profiles", "code_runs", "ai_usage", "turns", "interviews"):
                c.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
            for r in c.execute("SELECT id FROM threads WHERE user_id=?", (uid,)).fetchall():
                c.execute("DELETE FROM messages WHERE thread_id=?", (r["id"],))
            c.execute("DELETE FROM threads WHERE user_id=?", (uid,))
            c.execute("DELETE FROM users WHERE id=?", (uid,))
        else:
            raise HTTPException(400, "Unknown action")
    return {"ok": True}


class RefreshIn(BaseModel):
    trending: int = 4


@app.post("/api/admin/refresh")
def admin_refresh(r: RefreshIn, a=Depends(admin_user)):
    started = float(db.get_setting("bank_refreshed_ts", "0"))
    if db.get_setting("refresh_status") == "running" and time.time() - started < 600:
        return {"status": "running"}
    db.set_setting("bank_refreshed_ts", str(time.time()))
    threading.Thread(target=refresh_bank, args=(max(0, min(r.trending, 10)),), daemon=True).start()
    return {"status": "running"}


@app.get("/api/admin/refresh")
def admin_refresh_status(a=Depends(admin_user)):
    qs = questions()
    return {"status": db.get_setting("refresh_status", "never run"), "last": db.get_setting("bank_refreshed"),
            "total": len(qs), "trending": sum(1 for q in qs if q.get("recent"))}


@app.post("/api/admin/import")
async def admin_import(file: UploadFile = File(...), a=Depends(admin_user)):
    """Import questions from a PDF/markdown/text file you own into your private bank (database only)."""
    import importer
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "That file is over 15 MB.")
    name = (file.filename or "upload").rsplit("/", 1)[-1][:80]
    try:
        text = importer.pdf_text(data) if name.lower().endswith(".pdf") else data.decode("utf-8", "ignore")
    except Exception:
        raise HTTPException(400, "Couldn't read that file. Upload a text-based PDF, .md or .txt.")
    qs = importer.parse(text, source=f"import: {name}")
    if not qs:
        raise HTTPException(400, "No questions found in that file.")
    added = 0
    with db.conn() as c:
        for q in qs:
            if c.execute("SELECT 1 FROM bank WHERE id=?", (q["id"],)).fetchone():
                continue
            c.execute("INSERT INTO bank(id,data,added) VALUES(?,?,?)", (q["id"], json.dumps(q, ensure_ascii=False), time.time()))
            added += 1
    _bank_cache["at"] = 0
    cats = {}
    for q in qs:
        cats[q["category"]] = cats.get(q["category"], 0) + 1
    return {"found": len(qs), "added": added, "categories": cats}


class SettingsIn(BaseModel):
    registration_open: bool
    ai_daily_limit: int


@app.post("/api/admin/settings")
def admin_settings(s: SettingsIn, a=Depends(admin_user)):
    db.set_setting("registration_open", "1" if s.registration_open else "0")
    db.set_setting("ai_daily_limit", str(max(0, min(s.ai_daily_limit, 500))))
    return {"ok": True}


# ---------------- profile ----------------
def get_profile(uid):
    with db.conn() as c:
        row = c.execute("SELECT text FROM profiles WHERE user_id=?", (uid,)).fetchone()
    return row["text"] if row else default_profile()


class ProfileIn(BaseModel):
    text: str


@app.get("/api/profile")
def profile_get(u=Depends(current_user)):
    return {"text": get_profile(u["user_id"])}


@app.put("/api/profile")
def profile_put(p: ProfileIn, u=Depends(current_user)):
    with db.conn() as c:
        c.execute("INSERT INTO profiles(user_id,text,updated) VALUES(?,?,?) "
                  "ON CONFLICT(user_id) DO UPDATE SET text=excluded.text, updated=excluded.updated",
                  (u["user_id"], p.text, time.time()))
    return {"ok": True}


# ---------------- meta ----------------
@app.get("/api/meta")
def meta(u=Depends(current_user)):
    qs = questions()
    cats = {}
    for q in qs:
        cats[q["category"]] = cats.get(q["category"], 0) + 1
    used = db.usage_today(u["user_id"])
    return {"categories": cats, "total_questions": len(qs), "tracks": TRACKS,
            "role": u["role"], "trusted": bool(u["trusted"]) or u["role"] == "admin",
            "ai_used_today": used, "ai_limit": None if u["role"] == "admin" else ai_limit(),
            "mock": llm.MOCK, "key_set": bool(llm.API_KEY), "models": os.getenv("MODELS", "openrouter/free,auto"),
            "last_model": llm.last_model_used["id"],
            "bank_updated": db.get_setting("bank_refreshed") or load_json("bank_meta.json", {}).get("updated")}


# ---------------- interview ----------------
class StartIn(BaseModel):
    track: str = "engineer"
    category: str = "mixed"
    difficulty: str = "mixed"
    count: int = 8
    source: str = "mixed"   # bank | mixed | live


def _history(uid):
    with db.conn() as c:
        rows = c.execute("SELECT q_id, score, created FROM turns WHERE user_id=? AND q_id IS NOT NULL", (uid,)).fetchall()
    h = {}
    for r in rows:
        h.setdefault(r["q_id"], []).append((r["score"], r["created"]))
    return h


def _pick_bank(uid, track, category, difficulty, exclude):
    qs = [q for q in questions() if track in q.get("tracks", ["engineer", "architect"])]
    if category != "mixed":
        qs = [q for q in qs if q["category"] == category]
    if difficulty != "mixed":
        qs = [q for q in qs if q.get("difficulty") == difficulty] or qs
    qs = [q for q in qs if q["id"] not in exclude]
    if not qs:
        return None
    hist = _history(uid)

    def weight(q):
        h = hist.get(q["id"])
        w = 1.0
        if not h:
            w = 3.0                              # never asked: high priority
        else:
            last_score = h[-1][0]
            if last_score is None:
                w = 2.5
            elif last_score < 7:
                w = 2.5                          # weak: repeat
            elif time.time() - h[-1][1] < 7 * 86400:
                w = 0.2                          # mastered recently: rest
        if q.get("recent"):
            w *= 1.5                             # trending in current interviews
        return w

    return random.choices(qs, weights=[weight(q) for q in qs], k=1)[0]


def _generate_live(uid, track, category, difficulty, profile, asked):
    cats = sorted({q["category"] for q in questions()})
    cat = category if category != "mixed" else random.choice(cats)
    obj = llm.chat_json([
        {"role": "system", "content": prompts.GENERATE_QUESTION.format(
            track=TRACKS.get(track, track), profile=profile, category=cat,
            difficulty=difficulty if difficulty != "mixed" else "medium-hard",
            year=datetime.date.today().year, avoid="\n".join("- " + a for a in asked[-15:]) or "(none)")},
        {"role": "user", "content": "Ask the question now."}], temperature=0.8, max_tokens=600)
    return {"id": None, "category": cat, "q": obj["question"], "key_points": obj.get("key_points", [])}


def _next_question(uid, iv, profile, u=None):
    with db.conn() as c:
        asked = c.execute("SELECT q_id, question FROM turns WHERE interview_id=?", (iv["id"],)).fetchall()
    exclude = {r["q_id"] for r in asked if r["q_id"]}
    asked_text = [r["question"] for r in asked]
    src = json.loads(iv["report"] or "{}").get("source", "mixed") if iv["report"] else "mixed"
    want_live = src == "live" or (src == "mixed" and random.random() < 0.3)
    q = None
    if want_live and u is not None:
        try:
            ai_guard(u)
        except HTTPException:
            want_live = False          # out of AI calls: fall back to the bank
    if want_live and not llm.MOCK:
        try:
            q = _generate_live(uid, iv["track"], iv["category"], iv["difficulty"], profile, asked_text)
        except Exception:
            q = None
    if q is None:
        q = _pick_bank(uid, iv["track"], iv["category"], iv["difficulty"], exclude)
    if q is None:
        return None
    with db.conn() as c:
        cur = c.execute("INSERT INTO turns(interview_id,user_id,q_id,category,question,key_points,created) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (iv["id"], uid, q["id"], q["category"], q["q"], json.dumps(q.get("key_points", [])), time.time()))
        tid = cur.lastrowid
    return {"turn_id": tid, "question": q["q"], "category": q["category"], "is_followup": False,
            "live": q["id"] is None}


def _iv(uid, iid):
    with db.conn() as c:
        iv = c.execute("SELECT * FROM interviews WHERE id=? AND user_id=?", (iid, uid)).fetchone()
    if not iv:
        raise HTTPException(404, "Interview not found")
    return dict(iv)


def _progress(iid):
    with db.conn() as c:
        main = c.execute("SELECT COUNT(*) n FROM turns WHERE interview_id=? AND is_followup=0", (iid,)).fetchone()["n"]
    return main


@app.post("/api/interview/start")
def iv_start(s: StartIn, u=Depends(current_user)):
    uid = u["user_id"]
    count = max(1, min(s.count, 25))
    with db.conn() as c:
        cur = c.execute("INSERT INTO interviews(user_id,track,category,difficulty,total,created,report) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (uid, s.track, s.category, s.difficulty, count, time.time(), json.dumps({"source": s.source})))
        iid = cur.lastrowid
    iv = _iv(uid, iid)
    q = _next_question(uid, iv, get_profile(uid), u)
    if not q:
        raise HTTPException(400, "No questions match those filters")
    return {"interview_id": iid, "total": count, "index": 1, **q}


class AnswerIn(BaseModel):
    turn_id: int
    answer: str


@app.post("/api/interview/{iid}/answer")
def iv_answer(iid: int, a: AnswerIn, u=Depends(current_user)):
    uid = u["user_id"]
    iv = _iv(uid, iid)
    with db.conn() as c:
        t = c.execute("SELECT * FROM turns WHERE id=? AND interview_id=?", (a.turn_id, iid)).fetchone()
    if not t:
        raise HTTPException(404, "Question not found")
    if not a.answer.strip():
        raise HTTPException(400, "Type or speak an answer first (or press Skip).")
    with db.conn() as c:
        prev = c.execute("SELECT is_followup FROM turns WHERE interview_id=? AND id<? ORDER BY id DESC LIMIT 1",
                         (iid, a.turn_id)).fetchone()
    depth = (1 if t["is_followup"] else 0) + (1 if t["is_followup"] and prev and prev["is_followup"] else 0)
    ai_guard(u)
    try:
        fb = llm.chat_json([
            {"role": "system", "content": prompts.GRADE.format(
                track=TRACKS.get(iv["track"], iv["track"]), profile=get_profile(uid),
                difficulty=iv["difficulty"], category=t["category"], depth=depth,
                key_points="; ".join(json.loads(t["key_points"] or "[]")) or "(use your judgement)")},
            {"role": "user", "content": f"QUESTION: {t['question']}\n\nCANDIDATE ANSWER:\n{a.answer}"}],
            temperature=0.2)
    except llm.LLMError as e:
        raise HTTPException(503, str(e))
    try:
        score = max(0, min(10, int(round(float(fb.get("score", 0))))))
    except Exception:
        score = 0
    fb["score"] = score
    if depth >= 2:
        fb["follow_up"] = None          # real panels move on after two follow-ups
    fb["key_points"] = json.loads(t["key_points"] or "[]")
    fb["model_used"] = llm.last_model_used["id"]
    with db.conn() as c:
        c.execute("UPDATE turns SET answer=?, score=?, feedback=?, answered=? WHERE id=?",
                  (a.answer, score, json.dumps(fb), time.time(), a.turn_id))
    main_done = _progress(iid)
    return {"feedback": fb, "is_last": main_done >= iv["total"] and not fb.get("follow_up")}


class NextIn(BaseModel):
    followup: bool = False
    skip_turn_id: int | None = None


@app.post("/api/interview/{iid}/next")
def iv_next(iid: int, n: NextIn, u=Depends(current_user)):
    uid = u["user_id"]
    iv = _iv(uid, iid)
    if n.skip_turn_id:
        with db.conn() as c:
            c.execute("UPDATE turns SET answer='(skipped)', score=0, feedback=?, answered=? "
                      "WHERE id=? AND interview_id=? AND answered IS NULL",
                      (json.dumps({"score": 0, "verdict": "Skipped", "gaps": ["Skipped"]}), time.time(),
                       n.skip_turn_id, iid))
    if n.followup:
        with db.conn() as c:
            last = c.execute("SELECT * FROM turns WHERE interview_id=? AND answered IS NOT NULL "
                             "ORDER BY id DESC LIMIT 1", (iid,)).fetchone()
        fb = json.loads(last["feedback"] or "{}") if last else {}
        if fb.get("follow_up"):
            with db.conn() as c:
                cur = c.execute("INSERT INTO turns(interview_id,user_id,q_id,category,question,key_points,"
                                "is_followup,created) VALUES(?,?,?,?,?,?,1,?)",
                                (iid, uid, None, last["category"], fb["follow_up"],
                                 json.dumps(fb.get("gaps", [])), time.time()))
                tid = cur.lastrowid
            return {"turn_id": tid, "question": fb["follow_up"], "category": last["category"],
                    "is_followup": True, "index": _progress(iid), "total": iv["total"]}
    if _progress(iid) >= iv["total"]:
        return {"done": True}
    q = _next_question(uid, iv, get_profile(uid), u)
    if not q:
        return {"done": True}
    return {**q, "index": _progress(iid), "total": iv["total"]}


@app.post("/api/interview/{iid}/finish")
def iv_finish(iid: int, u=Depends(current_user)):
    uid = u["user_id"]
    iv = _iv(uid, iid)
    with db.conn() as c:
        turns = [dict(r) for r in c.execute("SELECT * FROM turns WHERE interview_id=? AND answered IS NOT NULL "
                                            "ORDER BY id", (iid,)).fetchall()]
    if not turns:
        raise HTTPException(400, "Answer at least one question first")
    scores = [t["score"] or 0 for t in turns]
    avg = round(sum(scores) / len(scores), 1)
    transcript = "\n".join(
        f"- [{t['category']}] Q: {t['question'][:200]} | score {t['score']} | gaps: "
        f"{'; '.join(json.loads(t['feedback'] or '{}').get('gaps', []))[:300]}" for t in turns)
    report = {"average": avg, "answered": len(turns)}
    try:
        report.update(llm.chat_json([
            {"role": "system", "content": prompts.SESSION_REPORT.format(
                track=TRACKS.get(iv["track"], iv["track"]), profile=get_profile(uid), transcript=transcript)},
            {"role": "user", "content": "Write the debrief."}], temperature=0.3))
    except Exception as e:
        report["overall"] = f"Average score {avg}/10 across {len(turns)} answers. (AI debrief unavailable: {e})"
    report["turns"] = [{"category": t["category"], "question": t["question"], "score": t["score"],
                        "is_followup": t["is_followup"]} for t in turns]
    with db.conn() as c:
        c.execute("UPDATE interviews SET finished=1, report=? WHERE id=?", (json.dumps(report), iid))
    return report


@app.get("/api/interview/history")
def iv_history(u=Depends(current_user)):
    with db.conn() as c:
        rows = c.execute("SELECT i.id, i.track, i.category, i.created, i.finished, i.total, "
                         "AVG(t.score) avg, COUNT(t.answered) answered FROM interviews i "
                         "LEFT JOIN turns t ON t.interview_id=i.id AND t.answered IS NOT NULL "
                         "WHERE i.user_id=? GROUP BY i.id ORDER BY i.id DESC LIMIT 30", (u["user_id"],)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/interview/{iid}/transcript")
def iv_transcript(iid: int, u=Depends(current_user)):
    iv = _iv(u["user_id"], iid)
    with db.conn() as c:
        turns = [dict(r) for r in c.execute("SELECT * FROM turns WHERE interview_id=? ORDER BY id", (iid,))]
    for t in turns:
        t["feedback"] = json.loads(t["feedback"] or "{}")
    rep = json.loads(iv["report"] or "{}")
    return {"interview": iv, "turns": turns, "report": rep if iv["finished"] else None}


@app.get("/api/interview/{iid}/export", response_class=PlainTextResponse)
def iv_export(iid: int, u=Depends(current_user)):
    data = iv_transcript(iid, u)
    lines = [f"# Mock interview #{iid} - {TRACKS.get(data['interview']['track'])}", ""]
    for i, t in enumerate(data["turns"], 1):
        fb = t["feedback"]
        lines += [f"## Q{i}{' (follow-up)' if t['is_followup'] else ''} [{t['category']}] - score {t['score']}/10",
                  f"**Question:** {t['question']}", "", f"**My answer:** {t['answer'] or ''}", ""]
        if fb.get("gaps"):
            lines += ["**Gaps:**"] + [f"- {g}" for g in fb["gaps"]] + [""]
        if fb.get("model_answer"):
            lines += ["**Model answer:**", fb["model_answer"], ""]
    return "\n".join(lines)


@app.get("/api/stats")
def stats(u=Depends(current_user)):
    uid = u["user_id"]
    with db.conn() as c:
        cats = [dict(r) for r in c.execute(
            "SELECT category, ROUND(AVG(score),1) avg, COUNT(*) n FROM turns WHERE user_id=? "
            "AND answered IS NOT NULL GROUP BY category ORDER BY avg", (uid,))]
        tot = c.execute("SELECT COUNT(*) n, ROUND(AVG(score),1) avg FROM turns WHERE user_id=? "
                        "AND answered IS NOT NULL", (uid,)).fetchone()
        last7 = c.execute("SELECT ROUND(AVG(score),1) avg FROM turns WHERE user_id=? AND answered > ?",
                          (uid, time.time() - 7 * 86400)).fetchone()
        code = c.execute("SELECT COUNT(DISTINCT problem_id) n FROM code_runs WHERE user_id=? AND passed=total",
                         (uid,)).fetchone()
    with db.conn() as c:
        times = [r["answered"] for r in c.execute(
            "SELECT answered FROM turns WHERE user_id=? AND answered IS NOT NULL AND answered > ?",
            (uid, time.time() - 400 * 86400))]
        best = c.execute("SELECT MAX(score) AS m FROM turns WHERE user_id=? AND answered IS NOT NULL",
                         (uid,)).fetchone()["m"]
    days = {datetime.date.fromtimestamp(t) for t in times}
    today = datetime.date.today()
    streak, d = 0, today if today in days else today - datetime.timedelta(days=1)
    while d in days:
        streak += 1
        d -= datetime.timedelta(days=1)
    today_n = sum(1 for t in times if datetime.date.fromtimestamp(t) == today)
    return {"by_category": cats, "answered": tot["n"], "average": tot["avg"], "avg_7d": last7["avg"],
            "streak": streak, "today": today_n, "daily_goal": 5, "best": best,
            "coding_solved": code["n"], "coding_total": len(problems())}


# ---------------- coding round ----------------
@app.get("/api/coding/problems")
def coding_list(u=Depends(current_user)):
    with db.conn() as c:
        solved = {r["problem_id"] for r in c.execute(
            "SELECT problem_id FROM code_runs WHERE user_id=? AND passed=total", (u["user_id"],))}
    return [{"id": p["id"], "title": p["title"], "difficulty": p["difficulty"], "kind": p.get("kind", "python"),
             "topic": p.get("topic", ""), "solved": p["id"] in solved} for p in problems()]


@app.get("/api/coding/problems/{pid}")
def coding_get(pid: str, u=Depends(current_user)):
    for p in problems():
        if p["id"] == pid:
            visible = [t for t in p["tests"]][:3]
            return {**{k: v for k, v in p.items() if k not in ("tests", "solution")},
                    "sample_tests": visible, "test_count": len(p["tests"])}
    raise HTTPException(404, "No such problem")


@app.get("/api/coding/problems/{pid}/solution")
def coding_solution(pid: str, u=Depends(current_user)):
    p = next((p for p in problems() if p["id"] == pid), None)
    if not p:
        raise HTTPException(404, "No such problem")
    return {"solution": p.get("solution", "")}


class CodeIn(BaseModel):
    code: str


@app.post("/api/coding/problems/{pid}/run")
def coding_run(pid: str, body: CodeIn, u=Depends(current_user)):
    p = next((p for p in problems() if p["id"] == pid), None)
    if not p:
        raise HTTPException(404, "No such problem")
    if not (u["role"] == "admin" or u["trusted"]):
        raise HTTPException(403, "Running code is enabled by the admin for trusted users only.")
    res = runner.run(p, body.code)
    with db.conn() as c:
        c.execute("INSERT INTO code_runs(user_id,problem_id,code,passed,total,created) VALUES(?,?,?,?,?,?)",
                  (u["user_id"], pid, body.code, res["passed"], res["total"], time.time()))
    return res


@app.post("/api/coding/problems/{pid}/review")
def coding_review(pid: str, body: CodeIn, u=Depends(current_user)):
    p = next((p for p in problems() if p["id"] == pid), None)
    if not p:
        raise HTTPException(404, "No such problem")
    ai_guard(u)
    try:
        text = llm.chat([
            {"role": "system", "content": "You are a senior Python interviewer. Review the candidate's solution: "
             "correctness, time/space complexity (Big-O), edge cases, readability, and what an interviewer would "
             "ask next. Then give a clean optimal solution and a 4-sentence way to explain it out loud. Markdown."},
            {"role": "user", "content": f"PROBLEM:\n{p['prompt']}\n\nCANDIDATE CODE:\n```\n{body.code}\n```"}],
            temperature=0.2)
    except llm.LLMError as e:
        raise HTTPException(503, str(e))
    return {"review": text}


# ---------------- coach ----------------
class CoachIn(BaseModel):
    thread_id: int | None = None
    message: str
    track: str = "engineer"


@app.get("/api/coach/threads")
def coach_threads(u=Depends(current_user)):
    with db.conn() as c:
        return [dict(r) for r in c.execute("SELECT id,title,created FROM threads WHERE user_id=? ORDER BY id DESC",
                                           (u["user_id"],))]


@app.get("/api/coach/threads/{tid}")
def coach_thread(tid: int, u=Depends(current_user)):
    with db.conn() as c:
        t = c.execute("SELECT * FROM threads WHERE id=? AND user_id=?", (tid, u["user_id"])).fetchone()
        if not t:
            raise HTTPException(404, "Not found")
        msgs = [dict(r) for r in c.execute("SELECT role,content,created FROM messages WHERE thread_id=? ORDER BY id",
                                           (tid,))]
    return {"thread": dict(t), "messages": msgs}


@app.delete("/api/coach/threads/{tid}")
def coach_delete(tid: int, u=Depends(current_user)):
    with db.conn() as c:
        if c.execute("DELETE FROM threads WHERE id=? AND user_id=?", (tid, u["user_id"])).rowcount:
            c.execute("DELETE FROM messages WHERE thread_id=?", (tid,))
    return {"ok": True}


@app.post("/api/coach/send")
def coach_send(m: CoachIn, u=Depends(current_user)):
    uid = u["user_id"]
    if not m.message.strip():
        raise HTTPException(400, "Empty message")
    with db.conn() as c:
        if m.thread_id:
            if not c.execute("SELECT 1 FROM threads WHERE id=? AND user_id=?", (m.thread_id, uid)).fetchone():
                raise HTTPException(404, "Not found")
            tid = m.thread_id
        else:
            title = m.message.strip().split("\n")[0][:70]
            tid = c.execute("INSERT INTO threads(user_id,title,created) VALUES(?,?,?)",
                            (uid, title, time.time())).lastrowid
        history = [dict(r) for r in c.execute(
            "SELECT role,content FROM messages WHERE thread_id=? ORDER BY id DESC LIMIT 16", (tid,))][::-1]
    msgs = [{"role": "system", "content": prompts.COACH.format(
        track=TRACKS.get(m.track, m.track), profile=get_profile(uid))}] + history + \
        [{"role": "user", "content": m.message}]
    ai_guard(u)
    try:
        reply = llm.chat(msgs, temperature=0.5, max_tokens=3500)
    except llm.LLMError as e:
        raise HTTPException(503, str(e))
    with db.conn() as c:
        c.execute("INSERT INTO messages(thread_id,role,content,created) VALUES(?,?,?,?)",
                  (tid, "user", m.message, time.time()))
        c.execute("INSERT INTO messages(thread_id,role,content,created) VALUES(?,?,?,?)",
                  (tid, "assistant", reply, time.time()))
    return {"thread_id": tid, "reply": reply, "model_used": llm.last_model_used["id"]}


@app.get("/api/coach/threads/{tid}/export", response_class=PlainTextResponse)
def coach_export(tid: int, u=Depends(current_user)):
    d = coach_thread(tid, u)
    out = [f"# {d['thread']['title']}", ""]
    for msg in d["messages"]:
        out += [("## Me" if msg["role"] == "user" else "## Coach"), msg["content"], ""]
    return "\n".join(out)


# ---------------- website ----------------
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE, "static", "index.html"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  Interview Coach running ->  http://localhost:{port}\n  (Ctrl+C to stop)\n")
    if os.getenv("NO_BROWSER", "0") != "1":
        import threading
        import webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run(app, host="0.0.0.0" if ON_RENDER else "127.0.0.1", port=port, log_level="warning")
