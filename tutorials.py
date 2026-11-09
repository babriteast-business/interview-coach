"""Tutorials: written lessons (Markdown) stored in the database so they survive Render redeploys.

The lessons that ship with the app live in tutorials/*.md (made from your study PDFs by pdf2md.py).
On start-up they are copied into the database; edit a .md file and redeploy to update it.
New lessons can be uploaded from the app as a PDF (converted to a written lesson) or as Markdown."""
import hashlib
import json
import os
import re
import time

import db

HERE = os.path.dirname(os.path.abspath(__file__))
SEED_DIR = os.path.join(HERE, "tutorials")
GROUPS = ["System design", "RAG & evals", "Models & training", "Agents & tools", "APIs & backend", "Other"]
MAX_MB = 25


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or f"tutorial-{int(time.time())}"


def outline(md):
    """Section titles the reader shows in its contents list: ## headings, or ### when there are few ##."""
    body = re.sub(r"```.*?```", "", md, flags=re.S)
    h2 = [m.group(1).strip() for m in re.finditer(r"^## (.+)$", body, re.M)]
    h3 = [m.group(1).strip() for m in re.finditer(r"^### (.+)$", body, re.M)]
    secs = h2 if len(h2) >= 3 else (h3 if len(h3) > len(h2) else h2)
    clean = lambda s: re.sub(r"^[A-Z]?\d{1,2}[.)]\s+", "", re.sub(r"[`*\\]", "", s).strip())  # noqa: E731
    return [clean(s) for s in secs]


def _words(md):
    return len(re.sub(r"<[^>]+>", " ", md).split())


def parse_md(text):
    from pdf2md import parse_front_matter
    return parse_front_matter(text)


def from_pdf(data):
    import pdf2md
    r = pdf2md.convert(data)
    return {"tagline": r["cover"].get("tagline", ""), "about": " ".join(r["cover"].get("notes", [])),
            "title": r["cover"].get("title", "")}, r["markdown"]


# ---------------- storage ----------------
def save(tid, title, group, blurb, md, tagline="", about="", sort=None, src="upload", digest=""):
    secs = outline(md)
    with db.conn() as c:
        old = c.execute("SELECT sort FROM tutorials WHERE id=?", (tid,)).fetchone()
        if sort is None:
            if old:
                sort = old["sort"]
            else:
                row = c.execute("SELECT COALESCE(MAX(sort),0) AS m FROM tutorials").fetchone()
                sort = (row["m"] or 0) + 1
        c.execute("DELETE FROM tutorials WHERE id=?", (tid,))
        c.execute("INSERT INTO tutorials(id,title,grp,blurb,pages,toc,sort,size,added,content,tagline,about,words,src,hash) "
                  "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (tid, title, group, blurb, len(secs), json.dumps(secs), sort, len(md), time.time(), md,
                   tagline, about, _words(md), src, digest))
    return {"id": tid, "sections": len(secs), "words": _words(md)}


def seed():
    """Copy the lessons in tutorials/*.md into the database; update them when the file changes."""
    if not os.path.isdir(SEED_DIR):
        return 0
    hidden = set(json.loads(db.get_setting("tutorials_removed", "[]") or "[]"))
    with db.conn() as c:
        have = {r["id"]: r for r in c.execute("SELECT id, src, hash, content FROM tutorials")}
    n = 0
    for name in sorted(os.listdir(SEED_DIR)):
        if not name.endswith(".md") or name.lower() == "readme.md":
            continue
        tid = name[:-3]
        if tid in hidden:
            continue
        with open(os.path.join(SEED_DIR, name), encoding="utf-8") as f:
            text = f.read()
        digest = hashlib.sha1(text.encode()).hexdigest()
        cur = have.get(tid)
        if cur and cur.get("content") and (cur.get("src") == "upload" or cur.get("hash") == digest):
            continue
        meta, body = parse_md(text)
        try:
            order = int(meta["order"]) if meta.get("order") else None
        except ValueError:
            order = None
        save(tid, meta.get("title") or tid.replace("-", " ").title(), meta.get("group") or "Other",
             meta.get("blurb", ""), body, meta.get("tagline", ""), meta.get("about", ""), sort=order, src="seed", digest=digest)
        n += 1
    if n:
        print(f"  Loaded {n} tutorials into the database")
    return n


def remove(tid):
    with db.conn() as c:
        c.execute("DELETE FROM tutorials WHERE id=?", (tid,))
        c.execute("DELETE FROM tutorial_progress WHERE tid=?", (tid,))
    # remember deletions so a shipped lesson doesn't come back on the next deploy
    hidden = set(json.loads(db.get_setting("tutorials_removed", "[]") or "[]"))
    hidden.add(tid)
    db.set_setting("tutorials_removed", json.dumps(sorted(hidden)))


def listing(uid):
    with db.conn() as c:
        rows = c.execute("SELECT id,title,grp,blurb,toc,sort,added,tagline,words FROM tutorials "
                         "WHERE content IS NOT NULL ORDER BY sort, added").fetchall()
        prog = {r["tid"]: r for r in c.execute(
            "SELECT tid,page,max_page,done,updated FROM tutorial_progress WHERE user_id=?", (uid,))}
    out = []
    for r in rows:
        p = prog.get(r["id"]) or {}
        secs = json.loads(r["toc"] or "[]")
        page = p.get("page") or 0
        out.append({"id": r["id"], "title": r["title"], "group": r["grp"], "blurb": r["blurb"], "tagline": r["tagline"] or "",
                    "sections": len(secs), "outline": secs[:4], "minutes": max(1, round((r["words"] or 0) / 200)),
                    "page": page, "max_page": p.get("max_page") or 0, "section": secs[page - 1] if 0 < page <= len(secs) else "",
                    "done": bool(p.get("done")), "updated": p.get("updated") or 0})
    return out


def detail(tid, uid):
    with db.conn() as c:
        r = c.execute("SELECT id,title,grp,blurb,toc,tagline,about,words,content,sort FROM tutorials WHERE id=?", (tid,)).fetchone()
        if not r or r["content"] is None:
            return None
        p = c.execute("SELECT page,max_page,done FROM tutorial_progress WHERE user_id=? AND tid=?",
                      (uid, tid)).fetchone() or {}
        nxt = c.execute("SELECT id,title,grp FROM tutorials WHERE content IS NOT NULL AND sort>? ORDER BY sort LIMIT 1",
                        (r["sort"] or 0,)).fetchone()
    secs = json.loads(r["toc"] or "[]")
    return {"id": r["id"], "title": r["title"], "group": r["grp"], "blurb": r["blurb"], "tagline": r["tagline"] or "",
            "about": r["about"] or "", "minutes": max(1, round((r["words"] or 0) / 200)), "sections": len(secs),
            "content": r["content"], "page": p.get("page") or 0, "max_page": p.get("max_page") or 0,
            "done": bool(p.get("done")),
            "next": {"id": nxt["id"], "title": nxt["title"], "group": nxt["grp"]} if nxt else None}


def save_progress(uid, tid, page, done=None):
    with db.conn() as c:
        old = c.execute("SELECT max_page,done FROM tutorial_progress WHERE user_id=? AND tid=?", (uid, tid)).fetchone()
        mx = max(page, (old or {}).get("max_page") or 0)
        dn = int(done) if done is not None else int((old or {}).get("done") or 0)
        if old:
            c.execute("UPDATE tutorial_progress SET page=?, max_page=?, done=?, updated=? WHERE user_id=? AND tid=?",
                      (page, mx, dn, time.time(), uid, tid))
        else:
            c.execute("INSERT INTO tutorial_progress(user_id,tid,page,max_page,done,updated) VALUES(?,?,?,?,?,?)",
                      (uid, tid, page, mx, dn, time.time()))
    return {"page": page, "max_page": mx, "done": bool(dn)}
