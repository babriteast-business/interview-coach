"""Turn a question PDF (or .md/.txt) you own into question-bank entries.

Understands the common "N  Level  Question? / Cover: key points" layout used by interview
question guides (levels Basic / Intermediate / Advanced, numbered category headers).
For any other layout it falls back to picking out every line that ends with a question mark.
Imported questions go into your private database only, never into the GitHub repo.
"""
import hashlib
import io
import re

LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "’": "'", "‘": "'",
             "“": '"', "”": '"'}
LEVELS = {"basic": "easy", "beginner": "easy", "easy": "easy", "intermediate": "medium", "medium": "medium",
          "advanced": "hard", "hard": "hard", "expert": "hard"}

# guide section names -> the app's topic names (keyword match on the section title)
CATEGORY_MAP = [
    (r"behavio|project|star", "Behavioural (STAR)"),
    (r"system design|design", "System design"),
    (r"production|cost|latency|scale", "Production & scale"),
    (r"safety|security|guardrail", "Safety & security"),
    (r"eval|observab", "Evals & LLM-as-judge"),
    (r"rag|memory|context|retriev", "RAG"),
    (r"mcp|integration", "Agents & MCP"),
    (r"multi-agent|agent pattern|agent loop|architecture|agent", "Agent loop & patterns"),
    (r"tool|function", "Tool calling"),
    (r"prompt|structured", "Prompting & structured outputs"),
    (r"fine-?tun|lora", "Fine-tuning"),
    (r"mlops|devops|deploy", "MLOps & DevSecOps"),
    (r"llm|fundamental|transformer", "LLM internals"),
    (r"machine learning|ml ", "ML fundamentals"),
]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def map_category(title):
    t = title.lower()
    for pat, cat in CATEGORY_MAP:
        if re.search(pat, t):
            return cat
    return title.strip().title()[:40] or "General"


def pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def clean(text):
    for k, v in LIGATURES.items():
        text = text.replace(k, v)
    return text


def split_points(cover):
    parts = [p.strip(" .;") for p in re.split(r"(?<=[.;?])\s+", cover) if p.strip(" .;")]
    return parts[:8] or [cover]


def scenario_blocks(lines):
    """Yield (question, interviewer-is-testing notes, section title) for guides that end each
    chapter with an 'INTERVIEW QUESTION' scenario."""
    section, i, n = "", 0, len(lines)
    while i < n:
        line = lines[i]
        if re.fullmatch(r"\d{2}", line) and i + 1 < n and lines[i + 1]:
            section = re.split(r"[:(]", lines[i + 1])[0].strip()[:40]
        if line.upper() == "INTERVIEW QUESTION":
            q, notes, j, mode = [], [], i + 1, "q"
            while j < n:
                l = lines[j]
                if not l or re.search(r"\|\s*Page \d+", l) or re.fullmatch(r"\d{2}", l) or l.upper() == "INTERVIEW QUESTION":
                    break
                m = re.match(r"what (they are|the interviewer is) testing:?\s*(.*)", l, re.I)
                if m:
                    mode = "notes"
                    notes.append(m.group(2))
                elif mode == "q":
                    q.append(l)
                else:
                    notes.append(l)
                j += 1
            qt = re.sub(r"\s+", " ", " ".join(q)).strip()
            if len(qt) > 20:
                yield qt, re.sub(r"\s+", " ", " ".join(notes)).strip(), section
            i = j
            continue
        i += 1


def parse(text, source="import"):
    text = clean(text)
    lines = [l.strip() for l in text.splitlines()]
    q_re = re.compile(r"^(\d{1,4})\s+(Basic|Beginner|Intermediate|Advanced|Expert|Easy|Medium|Hard)\s+(.+)$", re.I)
    sec_re = re.compile(r"^\d{1,2}\s+(.+?)\s+\d+\s+questions\b", re.I)
    out, cur, category, field = [], None, "General", None

    def flush():
        if cur and cur["q"].strip():
            q = re.sub(r"\s+", " ", cur["q"]).strip()
            cover = re.sub(r"\s+", " ", cur["cover"]).strip()
            out.append({"id": "imp-" + hashlib.md5(norm(q).encode()).hexdigest()[:10],
                        "category": cur["cat"], "difficulty": cur["diff"],
                        "tracks": ["engineer", "architect"], "recent": True, "q": q,
                        "key_points": split_points(cover) if cover else [], "source": source})

    for line in lines:
        if not line or re.match(r"^\d+\s*/\s*\d+", line) or line.startswith("# Level"):
            continue
        if re.match(r"^(where to study|made with)", line, re.I):
            break
        m = sec_re.match(line)
        if m:
            flush(); cur, field = None, None
            category = map_category(m.group(1))
            continue
        m = q_re.match(line)
        if m:
            flush()
            cur = {"q": m.group(3), "cover": "", "diff": LEVELS.get(m.group(2).lower(), "medium"), "cat": category}
            field = "q"
            continue
        if cur is None:
            continue
        if line.lower().startswith("cover:"):
            field = "cover"
            cur["cover"] += " " + line[6:]
        elif field == "q" and not cur["q"].rstrip().endswith(("?", ".")):
            cur["q"] += " " + line
        elif field == "cover":
            cur["cover"] += " " + line
    flush()

    # layout 2: "INTERVIEW QUESTION" scenario blocks followed by "What they are testing:" notes
    for q, notes, section in scenario_blocks(lines):
        out.append({"id": "imp-" + hashlib.md5(norm(q).encode()).hexdigest()[:10],
                    "category": "System design", "difficulty": "hard",
                    "tracks": ["engineer", "architect"], "recent": True, "q": q,
                    "key_points": split_points(notes) if notes else [],
                    "source": source + (f" ({section})" if section else "")})

    if not out:                           # unknown layout: every line that is a question
        out = []
        for line in lines:
            if line.endswith("?") and 20 <= len(line) <= 300:
                q = re.sub(r"^\s*([-*+]|\d+[.)])\s*", "", line)
                out.append({"id": "imp-" + hashlib.md5(norm(q).encode()).hexdigest()[:10], "category": map_category(q),
                            "difficulty": "medium", "tracks": ["engineer", "architect"], "recent": True,
                            "q": q, "key_points": [], "source": source})
    seen, uniq = set(), []
    for q in out:
        if q["id"] not in seen:
            seen.add(q["id"])
            uniq.append(q)
    return uniq
