"""Pull frequently-asked interview questions from the internet into the local bank.

  python refresh_questions.py              # fetch from public GitHub question lists (no API calls)
  python refresh_questions.py --trending 5 # ALSO ask the LLM for 5 current questions per category
                                           # (uses ~11 free OpenRouter requests)

Sources live in data/sources.json - add any raw markdown URL with questions in it.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

import httpx
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
DATA = os.path.join(BASE, "data")
BANK = os.path.join(DATA, "questions.json")

CATEGORY_RULES = [
    ("Agents & MCP", r"\bagent|mcp|tool call|function call|react\b|crew|autogen|langgraph|orchestrat|planning"),
    ("RAG", r"\brag\b|retriev|vector (db|database|store)|chunk|embedding search|rerank|hybrid search|knowledge base"),
    ("Fine-tuning", r"fine-?tun|lora|qlora|peft|rlhf|dpo|sft|instruction tun|distill|catastrophic"),
    ("Evals & LLM-as-judge", r"evaluat|benchmark|metric|judge|bleu|rouge|perplexity|hallucinat"),
    ("MLOps & DevSecOps", r"deploy|mlops|ci/cd|pipeline|kubernetes|docker|monitor|serving|gitops|devsecops|latency|throughput|scal"),
    ("System design", r"design a|architecture|system design|production|cost"),
    ("ML fundamentals", r"overfit|bias|variance|gradient|regulari|classif|regression|precision|recall|decision tree|boost|cross-valid"),
    ("LLM internals", r"transformer|attention|token|positional|kv cache|quantiz|decod|sampling|temperature|context window|llm|language model|moe|mixture"),
]


def categorize(q):
    ql = q.lower()
    for cat, pat in CATEGORY_RULES:
        if re.search(pat, ql):
            return cat
    return None


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def qid(prefix, q):
    return f"{prefix}-{hashlib.md5(norm(q).encode()).hexdigest()[:10]}"


def extract(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        cells = [c.strip() for c in line.strip("|").split("|")] if line.startswith("|") else [line]
        for c in cells:
            c = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", c)       # links -> text
            c = re.sub(r"[*_`#>]", "", c)
            c = re.sub(r"^\s*([-+]|\d+[.)]|Q\d+[:.)]?)\s*", "", c).strip()
            if c.endswith("?") and 25 <= len(c) <= 300 and "http" not in c:
                out.append(c)
    return out


def fetch_sources(bank):
    sources = json.load(open(os.path.join(DATA, "sources.json"), encoding="utf-8"))
    seen = {norm(q["q"]) for q in bank}
    added = 0
    for src in sources:
        try:
            r = httpx.get(src["url"], timeout=30, follow_redirects=True,
                          headers={"User-Agent": "interview-coach-refresh"})
            r.raise_for_status()
        except Exception as e:
            print(f"  ! {src['name']}: {e}")
            continue
        n = 0
        for q in extract(r.text):
            cat = categorize(q)
            if not cat or norm(q) in seen:
                continue
            seen.add(norm(q))
            bank.append({"id": qid("web", q), "category": cat, "difficulty": "medium",
                         "tracks": ["engineer", "architect"], "recent": False, "q": q,
                         "key_points": [], "source": src["name"]})
            n += 1
        print(f"  + {src['name']}: {n} new questions")
        added += n
    return added


def trending(bank, per_cat):
    sys.path.insert(0, BASE)
    import llm
    cats = sorted({q["category"] for q in bank if q["source"] == "curated"})
    seen = {norm(q["q"]) for q in bank}
    year = datetime.date.today().year
    added = 0
    for cat in cats:
        try:
            obj = llm.chat_json([
                {"role": "system", "content": "You are a hiring manager for remote AI Engineer / AI Architect roles."},
                {"role": "user", "content": f"List {per_cat} interview questions in the category '{cat}' that top "
                 f"companies are frequently asking in {year} (current tools, agents, MCP, evals, cost, production). "
                 'Return ONLY JSON: {"questions":[{"q":"...","difficulty":"easy|medium|hard",'
                 '"key_points":["4-6 points a strong answer covers"]}]}'}], temperature=0.7)
        except Exception as e:
            print(f"  ! {cat}: {e}")
            continue
        n = 0
        for item in obj.get("questions", []):
            q = str(item.get("q", "")).strip()
            if len(q) < 15 or norm(q) in seen:
                continue
            seen.add(norm(q))
            bank.append({"id": qid("trend", q), "category": cat,
                         "difficulty": item.get("difficulty", "medium"), "tracks": ["engineer", "architect"],
                         "recent": True, "q": q, "key_points": item.get("key_points", []),
                         "source": f"trending-{datetime.date.today().isoformat()}"})
            n += 1
        print(f"  + trending {cat}: {n}")
        added += n
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trending", type=int, default=0, help="LLM-generated current questions per category")
    a = ap.parse_args()
    bank = json.load(open(BANK, encoding="utf-8"))
    before = len(bank)
    print("Fetching question lists from the internet...")
    fetch_sources(bank)
    if a.trending:
        print("Asking the LLM for this year's trending questions...")
        trending(bank, a.trending)
    with open(BANK, "w", encoding="utf-8") as f:
        json.dump(bank, f, indent=1, ensure_ascii=False)
    meta = {"updated": datetime.datetime.now().isoformat(timespec="minutes"), "total": len(bank)}
    with open(os.path.join(DATA, "bank_meta.json"), "w") as f:
        json.dump(meta, f)
    print(f"Done. Bank: {before} -> {len(bank)} questions.")


if __name__ == "__main__":
    main()
