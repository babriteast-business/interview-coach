"""Turn a study-notes PDF into a clean, structured Markdown tutorial.

The PDF is only a source of content. Its layout tells us what each piece of text is:
  big bold headings  -> ## section, smaller bold headings -> ### subsection
  monospace text in a shaded box -> fenced code block
  bordered grid -> table (written as HTML so cells can keep inline code)
  "SAY THIS:", "TIP:", "CAREFUL:" ... at the start of a paragraph -> a callout (blockquote)
  small boxes with short labels -> a ```flow``` diagram block the app draws as cards
Everything else becomes paragraphs and lists with **bold** and `inline code` kept.
"""
import html
import io
import re
import statistics

import pdfplumber

CALLOUTS = ["SAY THIS", "TIP", "CAREFUL", "PRACTICE", "TEACH IT BACK", "REMEMBER", "WARNING", "NOTE",
            "EXPECTED", "TRY IT", "TASK", "INTERVIEW", "WHY", "MY TAKE", "IMPORTANT", "CHECK"]
LIST_RE = re.compile(r"^(\d{1,2}[.)]|\(\d{1,2}\)|[•·▪◦‣–-])\s+")


# ---------------- helpers ----------------
def _font(w):
    return (w.get("fontname") or "").split("+")[-1]


def _kind(w):
    f, s = _font(w), w.get("size", 0)
    if "Mono" in f:
        return "mono"
    if "Caveat" in f and "Bold" in f:
        return "h2" if s >= 24 else "h3" if s >= 15.5 else "bold"
    if "Caveat" in f:
        return "hand"          # diagram labels or small handwritten sub-headings
    if "Bold" in f:
        return "bold"
    return "text"


def _num(c):
    return isinstance(c, (tuple, list)) and len(c) >= 3 and all(isinstance(x, (int, float)) for x in c[:3])


def _close(a, b, tol=0.006):
    return _num(a) and _num(b) and a is not None and b is not None and len(a) >= 3 and len(b) >= 3 and all(abs(x - y) <= tol for x, y in zip(a, b))


CODE_FILL = (0.9529, 0.9647, 0.9922)
PILL_FILL = (0.9333, 0.949, 0.9843)
PILL_STROKE = (0.8392, 0.8706, 0.9412)


def _inside(w, box, pad=1.5):
    cx, cy = (w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2
    return box[0] - pad <= cx <= box[2] + pad and box[1] - pad <= cy <= box[3] + pad


def _esc(t):
    t = t.replace("\\", "\\\\")
    t = re.sub(r"([*_`\[\]|])", r"\\\1", t)
    return t.replace("<", "&lt;").replace(">", "&gt;")


def _join_words(words, md=True):
    """Join words of one line, keeping real gaps only, and mark bold / code spans."""
    out, prev, style = [], None, None
    for w in words:
        k = w["_k"]
        st = "code" if k == "mono" else "bold" if k in ("bold", "h3", "h2") else "text"
        gap = (w["x0"] - prev["x1"]) if prev else 0
        # pdfplumber only splits words of the same font at a real space; across fonts trust the gap
        same = prev is not None and prev.get("fontname") == w.get("fontname") and abs(prev.get("size", 0) - w.get("size", 0)) < 0.2
        space = prev is not None and (gap > 0.12 * w.get("size", 10) or same or (
            gap > -0.5 and prev["text"][-1:].isalnum() and w["text"][:1].isalnum()))
        if not md:
            out.append((" " if space else "") + w["text"])
        else:
            if st != style:
                if style == "code":
                    out.append("`")
                elif style == "bold":
                    out.append("**")
                out.append(" " if space else "")
                if st == "code":
                    out.append("`")
                elif st == "bold":
                    out.append("**")
                style = st
            elif space:
                out.append(" ")
            out.append(w["text"] if st == "code" else _esc(w["text"]))
        prev = w
    if md:
        out.append("`" if style == "code" else "**" if style == "bold" else "")
    s = "".join(out)
    s = re.sub(r"(?<=\S)\*\*\*\*(?=\S)", "", s)       # two bold spans touching
    s = re.sub(r"(?<=\S)\*\* \*\*(?=\S)", " ", s)     # two bold spans with a space
    s = s.replace("``", "")
    return s.strip()


def _lines(words, tol=None):
    """Group words into visual lines. Bold words sit a few points lower than body text, so use centres."""
    ws = sorted(words, key=lambda w: (w["top"] + w["bottom"]) / 2)
    lines = []
    for w in ws:
        c = (w["top"] + w["bottom"]) / 2
        t = tol or max(4.0, 0.42 * w.get("size", 10))
        if lines and abs(lines[-1]["c"] - c) <= t:
            L = lines[-1]
            L["words"].append(w)
            L["c"] = (L["c"] * (len(L["words"]) - 1) + c) / len(L["words"])
        else:
            lines.append({"c": c, "words": [w]})
    for L in lines:
        L["words"].sort(key=lambda w: w["x0"])
        L["top"] = min(w["top"] for w in L["words"])
        L["bottom"] = max(w["bottom"] for w in L["words"])
        L["x0"] = min(w["x0"] for w in L["words"])
        L["x1"] = max(w["x1"] for w in L["words"])
        L["size"] = statistics.median(w.get("size", 10) for w in L["words"])
        kinds = [w["_k"] for w in L["words"]]
        L["kind"] = max(set(kinds), key=lambda k: sum(len(w["text"]) for w in L["words"] if w["_k"] == k))
    return lines


def _code_text(chars, box):
    chars = [c for c in chars if c["text"].strip() or c["text"] == " "]
    if not chars:
        return ""
    widths = [c["x1"] - c["x0"] for c in chars if c["text"].strip()]
    cw = statistics.median(widths) if widths else 5
    left = min(c["x0"] for c in chars if c["text"].strip())
    rows = {}
    for c in sorted(chars, key=lambda c: c["top"]):
        key = next((k for k in rows if abs(k - c["top"]) < 2.5), c["top"])
        rows.setdefault(key, []).append(c)
    out = []
    for k in sorted(rows):
        line = ""
        for c in sorted(rows[k], key=lambda c: c["x0"]):
            if not c["text"].strip():
                continue
            col = int(round((c["x0"] - left) / cw))
            if col > len(line):
                line += " " * (col - len(line))
            line += c["text"]
        out.append(line.rstrip())
    return "\n".join(out)


# ---------------- per page ----------------
def _page_blocks(page, content_left):
    W = page.width
    big = lambda o: (o["x1"] - o["x0"]) * (o["bottom"] - o["top"]) > 0.45 * W * page.height  # noqa: E731
    words = page.extract_words(extra_attrs=["fontname", "size"], keep_blank_chars=False, x_tolerance=1.6)
    for w in words:
        w["_k"] = _kind(w)
    shapes = [o for o in page.curves + page.rects if not big(o)]
    blocks = []
    used = set()

    # tables: ruled grids made of thin rectangles
    try:
        tpage = page.filter(lambda o: not (o.get("object_type") == "rect" and big(o)) and o.get("object_type") != "curve")
        tables = tpage.find_tables({"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 2})
    except Exception:
        tables = []
    tboxes = []
    for t in tables:
        rows = []
        for r in t.rows:
            cells = []
            for cb in r.cells:
                if cb is None:
                    continue
                cw = [w for w in words if id(w) not in used and _inside(w, cb, 0.5)]
                for w in cw:
                    used.add(id(w))
                lines = _lines(cw)
                parts, bold = [], bool(cw) and sum(len(w["text"]) for w in cw if w["_k"] == "bold") > 0.6 * sum(len(w["text"]) for w in cw)
                for i, L in enumerate(lines):
                    txt = _cell_html(L["words"])
                    if i and lines[i - 1]["x1"] < cb[2] - 0.3 * (cb[2] - cb[0]):
                        parts.append("<br>" + txt)
                    else:
                        parts.append((" " if i else "") + txt)
                cells.append({"html": "".join(parts).strip(), "bold": bold})
            if any(c["html"] for c in cells):
                rows.append(cells)
        if len(rows) >= 1 and max(len(r) for r in rows) >= 2:
            tboxes.append(t.bbox)
            width = max(len(r) for r in rows)
            keep, spill = [], []
            for r in rows:
                filled = [c for c in r if c["html"]]
                txt = re.sub(r"<[^>]+>", "", filled[0]["html"]) if len(filled) == 1 else ""
                if len(filled) == 1 and (len(r) < width or len(txt) > 160) and len(txt) > 120:
                    spill.append(filled[0]["html"])          # a framed paragraph that only looks like a table row
                elif not spill:
                    keep.append(r)
                else:
                    spill.append(None)
                    keep.append(r)
            if keep:
                blocks.append({"type": "table", "top": t.bbox[1], "rows": keep})
            for k, h in enumerate(x for x in spill if x):
                blocks.append({"type": "html_para", "top": t.bbox[3] + k * 0.01, "html": h})
    words = [w for w in words if id(w) not in used]

    # shaded code boxes, diagram boxes, callout frames. One drawn box is often two shapes (fill + outline).
    geo = []
    for s in sorted(shapes, key=lambda o: (o["top"], o["x0"])):
        box = (s["x0"], s["top"], s["x1"], s["bottom"])
        bw, bh = box[2] - box[0], box[3] - box[1]
        if bw < 14 or bh < 10 or any(_inside({"x0": box[0], "x1": box[2], "top": box[1], "bottom": box[3]}, tb, 2) for tb in tboxes):
            continue
        g = next((g for g in geo if all(abs(box[i] - g["box"][i]) < 3 for i in range(4))), None)
        if not g:
            g = {"box": box, "fills": [], "strokes": []}
            geo.append(g)
        if s.get("fill"):
            g["fills"].append(s.get("non_stroking_color"))
        if s.get("stroke") or not s.get("fill"):
            g["strokes"].append(s.get("stroking_color"))
    code_boxes, nodes, frames = [], [], []
    content_w = W - 2 * content_left
    for g in geo:
        box = g["box"]
        bw, bh = box[2] - box[0], box[3] - box[1]
        fill = next((f for f in g["fills"] if _num(f)), None)
        if any(_close(f, PILL_FILL) for f in g["fills"]) or any(_close(s, PILL_STROKE) for s in g["strokes"]):
            continue                       # inline code highlight
        inside = [w for w in words if _inside(w, box)]
        if not inside:
            continue
        mono_share = sum(len(w["text"]) for w in inside if w["_k"] == "mono") / max(1, sum(len(w["text"]) for w in inside))
        if not _close(fill, CODE_FILL) and ((mono_share == 1 and bw < 0.4 * content_w) or (mono_share >= 0.6 and bh < 22)):
            continue                       # a highlighted command inside a sentence (it may wrap onto the next line)
        # a marker highlight over part of a sentence: text runs straight through the box
        if bh < 26:
            cy0, cy1 = box[1], box[3]
            neighbours = [w for w in words if not _inside(w, box) and cy0 - 3 <= (w["top"] + w["bottom"]) / 2 <= cy1 + 3
                          and (0 <= box[0] - w["x1"] < 14 or 0 <= w["x0"] - box[2] < 14)]
            if neighbours:
                continue
        mono = sum(len(w["text"]) for w in inside if w["_k"] == "mono")
        total = sum(len(w["text"]) for w in inside)
        hand = sum(len(w["text"]) for w in inside if w["_k"] == "hand")
        if _close(fill, CODE_FILL) or (mono > 0.8 * total and bw > 0.4 * content_w):
            code_boxes.append(box)
        elif bw < 0.62 * content_w or hand > 0.6 * total:
            nodes.append({"box": box, "colors": [c for c in g["strokes"] if _num(c)] + [c for c in g["fills"] if _num(c)]})
        else:
            frames.append(box)

    # code blocks
    for box in code_boxes:
        chars = [c for c in page.chars if _inside(c, box)]
        txt = _code_text(chars, box)
        ws = [w for w in words if _inside(w, box)]
        for w in ws:
            used.add(id(w))
        if txt.strip():
            blocks.append({"type": "code", "top": box[1], "text": txt})
    words = [w for w in words if id(w) not in used]

    merged = nodes
    # smaller boxes win when one box sits inside another
    merged.sort(key=lambda m: (m["box"][2] - m["box"][0]) * (m["box"][3] - m["box"][1]))
    node_list = []
    for m in merged:
        ws = [w for w in words if id(w) not in used and _inside(w, m["box"]) and w["_k"] not in ("h2", "h3")]
        if not ws:
            continue
        for w in ws:
            used.add(id(w))
        lines = _lines(ws)
        lines.sort(key=lambda L: L["top"])
        sizes = [L["size"] for L in lines]
        tmax = max(sizes)
        title = [L for L in lines if L["size"] >= tmax - 0.6]
        rest = [L for L in lines if L["size"] < tmax - 0.6]
        if not rest and len(title) > 1:
            title, rest = title[:1], title[1:]
        node_list.append({"box": m["box"], "title": " ".join(_join_words(L["words"], md=False) for L in title),
                          "detail": " · ".join(_join_words(L["words"], md=False) for L in rest),
                          "tone": _tone(m["colors"])})
    words = [w for w in words if id(w) not in used]
    if node_list:
        blocks.extend(_diagrams(node_list, words, page, used))
        words = [w for w in words if id(w) not in used]

    # remaining text -> lines; text laid out in aligned columns over several lines becomes a table
    lines = _lines(words)
    i = 0
    while i < len(lines):
        run = _column_run(lines, i)
        if run:
            rows = [[{"html": _cell_html(ch), "bold": all(w["_k"] == "bold" for w in ch)} for ch in _chunks(L)] for L in lines[i:i + run]]
            blocks.append({"type": "table", "top": lines[i]["top"], "rows": rows, "loose": True})
            i += run
            continue
        L = lines[i]
        L["type"] = "line"
        L["frame"] = any(_inside({"x0": L["x0"], "x1": L["x0"] + 2, "top": L["top"], "bottom": L["bottom"]}, f, 3) for f in frames)
        blocks.append(L)
        i += 1
    blocks.sort(key=lambda b: b["top"])
    return blocks


def _chunks(L):
    """Split a line where there is a wide gap (text sitting in separate columns)."""
    out, cur = [], []
    for w in L["words"]:
        if cur and w["x0"] - cur[-1]["x1"] > 2.2 * w.get("size", 10):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def _column_run(lines, i):
    """How many lines from i form a grid of 3+ aligned columns (0 if none)."""
    def sig(L):
        ch = _chunks(L)
        return [((c[0]["x0"] + c[-1]["x1"]) / 2) for c in ch]
    first = sig(lines[i])
    if len(first) < 3:
        return 0
    n = 1
    while i + n < len(lines):
        s = sig(lines[i + n])
        gap = lines[i + n]["top"] - lines[i + n - 1]["bottom"]
        if len(s) != len(first) or gap > 1.8 * lines[i + n]["size"] or any(abs(a - b) > 28 for a, b in zip(s, first)):
            break
        n += 1
    return n if n >= 2 else 0


def _cell_html(words):
    out, prev = [], None
    for w in words:
        gap = (w["x0"] - prev["x1"]) if prev else 0
        sp = " " if prev is not None and gap > 0.12 * w.get("size", 10) else ""
        t = html.escape(w["text"])
        if w["_k"] == "mono":
            t = f"<code>{t}</code>"
        elif w["_k"] in ("bold",):
            t = f"<b>{t}</b>"
        out.append(sp + t)
        prev = w
    s = "".join(out)
    s = re.sub(r"</code>(\s?)<code>", r"\1", s)
    s = re.sub(r"</b>(\s?)<b>", r"\1", s)
    return s


def _tone(colors):
    for c in colors:
        if not _num(c):
            continue
        r, g, b = c[:3]
        if r > 0.6 and g < 0.4:
            return "red"
        if g > 0.4 and r < 0.3 and b < 0.45:
            return "green"
        if b > 0.55 and r < 0.3:
            return "blue"
        if r > 0.95 and g > 0.9 and b < 0.8:
            return "yellow"
        if r > 0.95 and g < 0.8 and b < 0.6:
            return "orange"
    return "plain"


def _diagrams(nodes, words, page, used):
    """Group nearby boxes into diagrams. One row of boxes becomes a flow; anything else a grid."""
    nodes.sort(key=lambda n: n["box"][1])
    groups = []
    for n in nodes:
        if groups and n["box"][1] <= max(m["box"][3] for m in groups[-1]) + 46:
            groups[-1].append(n)
        else:
            groups.append([n])
    out = []
    arrows = [c for c in page.curves if (c["x1"] - c["x0"]) < 18 and (c["bottom"] - c["top"]) < 18 and c.get("fill")]
    arrows += [c for c in page.chars if c["text"] in "→⟶➜"]
    for g in groups:
        top, bottom = min(n["box"][1] for n in g), max(n["box"][3] for n in g)
        # loose handwritten labels inside the diagram area, e.g. "Observability: ...", "tiny!"
        loose = [w for w in words if id(w) not in used and w["_k"] in ("hand",) and top - 6 <= w["top"] <= bottom + 44]
        for L in _lines(loose):
            txt = _join_words(L["words"], md=False)
            for w in L["words"]:
                used.add(id(w))
            if len(re.sub(r"[^A-Za-z0-9]", "", txt)) >= 3:
                g.append({"box": (L["x0"], L["top"], L["x1"], L["bottom"]), "title": txt, "detail": "", "tone": "note"})
        centers = [((n["box"][1] + n["box"][3]) / 2) for n in g if n["tone"] != "note"]
        one_row = len(centers) >= 2 and max(centers) - min(centers) < 22 and all(n["tone"] != "note" for n in g)
        g.sort(key=lambda n: (round(((n["box"][1] + n["box"][3]) / 2) / 30), n["box"][0]))
        has_arrows = any(top - 4 <= a["top"] <= bottom + 4 for a in arrows)
        kind = "flow" if one_row and has_arrows else "steps" if one_row else "grid"
        out.append({"type": "diagram", "top": top, "kind": kind, "nodes": g})
    return out


# ---------------- whole document ----------------
def _cover(page):
    chars = [c for c in page.chars if c["text"].strip()]
    rows = {}
    for c in chars:
        key = next((k for k in rows if abs(k - c["top"]) < 0.45 * c["size"]), c["top"])
        rows.setdefault(key, []).append(c)
    lines = []
    for k in sorted(rows):
        cs = sorted(rows[k], key=lambda c: c["x0"])
        s, prev = "", None
        for c in cs:
            if prev is not None and c["x0"] - prev["x1"] > 0.22 * c["size"]:
                s += " "
            s += c["text"]
            prev = c
        lines.append({"text": s.strip(), "size": statistics.median(c["size"] for c in cs), "font": cs[0]["fontname"].split("+")[-1]})
    big = [L for L in lines if L["size"] >= 36]
    title = " ".join(L["text"] for L in big)
    tag = [L["text"] for L in lines if 20 <= L["size"] < 36 and "Caveat" in L["font"]]
    notes = [L["text"] for L in lines if L["size"] < 20 and "Caveat" not in L["font"]]
    merged = []
    for n in notes:                      # a note that wrapped onto a second line
        if merged and n[:1].islower():
            merged[-1] += " " + n
        else:
            merged.append(n)
    notes = [re.sub(r"^Babrit['’]s hand-notes\s*[—-]\s*", "", n) for n in merged]
    notes = [re.sub(r"^Babrit['’]s hand-notes\s+for\s+", "For ", n) for n in notes]
    notes = [n[0].upper() + n[1:] for n in notes if n]
    return {"title": title, "tagline": " ".join(tag), "notes": [n for n in notes if n]}


def convert(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        cover = _cover(pdf.pages[0])
        blocks = []
        for i, page in enumerate(pdf.pages[1:], start=2):
            pb = _page_blocks(page, 45)
            for b in pb:
                b["page"] = i
            if pb:
                pb[0]["page_start"] = True
            blocks.extend(pb)
    md = _to_markdown(blocks)
    return {"cover": cover, "markdown": md, "pages": len(blocks)}


def _callout(text):
    m = re.match(r"^\*\*([A-Z][A-Z \-']{1,24}?):\s*(.*?)\*\*\s*", text)
    if not m:
        return None
    label = m.group(1).strip()
    if label.upper() not in CALLOUTS and not (label.isupper() and len(label) <= 18):
        return None
    title = m.group(2).strip()
    rest = text[m.end():]
    return label, (f"**{title}** " if title else "") + rest


def _to_markdown(blocks):
    out = []          # list of ("kind", text) chunks
    para = None       # current paragraph accumulator

    def flush():
        nonlocal para
        if para:
            text = " ".join(para["parts"]).strip()
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"(?<=\S)\*\* \*\*(?=\S)", " ", text)      # bold that wrapped onto the next line
            text = re.sub(r"(?<=\S)` `(?=\S)", " ", text)
            text = re.sub(r"(?<=[a-z])- (?=[a-z])", "-", text)                # "fine- tuning" split by a line wrap
            text = re.sub(r"(`|\*\*) ([.,;:!?)])", r"\1\2", text)              # no gap before punctuation
            text = re.sub(r"\( (`|\*\*)", r"(\1", text)
            if para["list"]:
                out.append(("li", para["marker"] + " " + text, para.get("ordered")))
            else:
                c = _callout(text)
                if c:
                    out.append(("callout", c))
                else:
                    out.append(("p", text))
        para = None

    prev = None
    for b in blocks:
        t = b["type"]
        if t == "line":
            kind = b["kind"]
            txt = _join_words(b["words"])
            plain = _join_words(b["words"], md=False)
            if not plain.strip():
                continue
            hk = next((w["_k"] for w in b["words"] if w["_k"] in ("h2", "h3")), None)
            if hk and all(w["_k"] in (hk, "mono") for w in b["words"]):
                kind = b["kind"] = hk
                plain = txt.replace("**", "").replace("\\", "")
                flush()
                if out and out[-1][0] == kind and prev is not None and prev.get("type") == "line" and prev.get("kind") == kind \
                        and b["top"] - prev["bottom"] < 0.6 * b["size"]:
                    out[-1] = (kind, out[-1][1] + " " + plain)        # wrapped heading
                else:
                    out.append((kind, plain))
                prev = b
                continue
            if kind == "hand" and b["size"] >= 15 and all(w["_k"] == "hand" for w in b["words"]):
                flush()
                out.append(("h4", plain))
                prev = b
                continue
            m = LIST_RE.match(plain)
            gap = (b["top"] - prev["bottom"]) if (prev is not None and prev.get("type") == "line") else 99
            new_para = (para is None or gap > 0.62 * b["size"] or b.get("page_start") and para is None
                        or (m and not para.get("frame_cont")))
            if b.get("page_start") and para is not None and not m:
                new_para = bool(re.search(r"[.:!?)]$", para["parts"][-1]))   # paragraph running onto the next page
            if m and para is not None and not para["list"] and gap <= 0.62 * b["size"] and len(m.group(1)) == 1 and m.group(1) in "-–":
                m = None                                                   # a hyphen at a wrapped line start
            if new_para or m:
                flush()
                if m:
                    marker = m.group(1)
                    ordered = marker[0].isdigit() or marker.startswith("(")
                    body = txt[len(_esc(marker)):].lstrip() if txt.startswith(_esc(marker)) else LIST_RE.sub("", txt, 1)
                    para = {"parts": [body], "list": True, "marker": (re.sub(r"\D", "", marker) + "." if ordered else "-"),
                            "ordered": ordered, "x0": b["x0"]}
                else:
                    para = {"parts": [txt], "list": False, "x0": b["x0"]}
            else:
                para["parts"].append(txt)
            prev = b
            continue
        flush()
        if t == "html_para":
            h = b["html"]
            h = re.sub(r"<br>", "\n", h)
            h = re.sub(r"</?b>", "**", h)
            h = re.sub(r"<code>(.*?)</code>", r"`\1`", h)
            h = html.unescape(re.sub(r"<[^>]+>", "", h))
            for part in [x.strip() for x in h.split("\n") if x.strip()]:
                c = _callout(part)
                out.append(("callout", c) if c else ("p", part))
            prev = None
            continue
        if t == "code":
            if out and out[-1][0] == "code" and b.get("page_start"):
                out[-1] = ("code", out[-1][1] + "\n" + b["text"])       # code continued on the next page
            else:
                out.append(("code", b["text"]))
        elif t == "table":
            if out and out[-1][0] == "table" and b.get("page_start") and len(b["rows"][0]) == len(out[-1][1][0]) \
                    and not all(c["bold"] for c in b["rows"][0]):
                out[-1] = ("table", out[-1][1] + b["rows"])
            else:
                out.append(("table", b["rows"]))
        elif t == "diagram":
            out.append(("diagram", b))
        prev = b
    flush()
    return _render(out)


def _lang(code):
    s = code.lower()
    if re.search(r"^\s*(def |class |import |from \w+ import|async def |@\w+)", code, re.M):
        return "python"
    if re.search(r"invoke-restmethod|\$env:|set-executionpolicy|expand-archive|new-item|get-content|\.ps1\b", s):
        return "powershell"
    if re.search(r"^\s*[{\[]", code) and re.search(r'"\s*:', code):
        return "json"
    lines = [ln for ln in code.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    keys = [ln for ln in lines if re.match(r"^\s*-?\s*[\w.-]+:(\s|$)", ln)]
    if lines and len(keys) >= 0.4 * len(lines) and not re.search(r"^\s*(def |import |\$|PS>)", code, re.M):
        return "yaml"
    if re.search(r"^\s*(pip|uv|npm|npx|docker|git|curl|cd|python|uvicorn|pytest|ollama|claude|cursor|codex|n8n|crewai|openclaw)\b", s, re.M):
        return "bash"
    return ""


SHOUTY = {"LEVEL", "EXAMPLE", "WORKFLOW", "PART", "STEP", "LAB", "CURSOR", "CODEX", "OPENAI", "PROJECT", "BONUS", "APPENDIX"}


RENAME = {"my thoughts on your approach, and how to use these notes": "How to use this tutorial",
          "how to use these notes": "How to use this tutorial"}


def _heading(s):
    """'LEVEL 1 - Error analysis' -> 'Level 1 - Error analysis' (keeps real acronyms like RAG, API)."""
    s = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", s))
    s = re.sub(r"\s+([,.:;])", r"\1", s)
    key = re.sub(r"^[A-Z]?\d{1,2}[.)]\s+", "", s.strip()).lower()
    if key in RENAME:
        return RENAME[key]
    return re.sub(r"\b[A-Z]{4,}\b", lambda m: m.group(0).title() if m.group(0) in SHOUTY else m.group(0), s.strip())


def _render(chunks):
    md, prev = [], None
    for c in chunks:
        k = c[0]
        if k == "h2":
            title = re.sub(r"^PART\s+\w+\s*[-:–]\s*", "", c[1]).strip()
            if title.isupper() and len(title) > 4:
                title = title.title().replace("Openai", "OpenAI").replace("Llm", "LLM").replace("Ai ", "AI ")
            md.append(f"\n## {_heading(title)}\n")
        elif k == "h3":
            md.append(f"\n### {_heading(c[1])}\n")
        elif k == "h4":
            md.append(f"\n#### {c[1].strip()}\n")
        elif k == "p":
            md.append(c[1] + "\n")
        elif k == "li":
            if prev != "li":
                md.append("")
            md.append(c[1])
        elif k == "callout":
            label, body = c[1]
            md.append(f"> **{label.title() if label.isupper() else label}:** {body}\n")
        elif k == "code":
            md.append(f"\n```{_lang(c[1])}\n{c[1]}\n```\n")
        elif k == "table":
            rows = c[1]
            head = rows[0] if all(x["bold"] for x in rows[0] if x["html"]) else None
            body = rows[1:] if head else rows
            h = ["<table>"]
            if head:
                h.append("<thead><tr>" + "".join(f"<th>{re.sub(r'</?b>', '', x['html'])}</th>" for x in head) + "</tr></thead>")
            h.append("<tbody>" + "".join("<tr>" + "".join(f"<td>{x['html']}</td>" for x in r) + "</tr>" for r in body) + "</tbody>")
            h.append("</table>")
            md.append("\n" + "".join(h) + "\n")
        elif k == "diagram" and len(c[1]["nodes"]) == 1:
            n = c[1]["nodes"][0]                     # a lone sticky note in the margin = the key idea of the part
            body = (n["title"] + (f" {n['detail']}" if n["detail"] else "")).strip()
            body = re.sub(r"^REMEMBER:\s*", "", body)
            if len(re.sub(r"[^A-Za-z0-9]", "", body)) >= 8:
                md.append(f"> **Key idea:** {_esc(body)}\n")
        elif k == "diagram":
            d = c[1]
            lines = [f"```diagram {d['kind']}"]
            for n in d["nodes"]:
                detail = f" | {n['detail']}" if n["detail"] else ""
                lines.append(f"{n['tone']}: {n['title']}{detail}")
            lines.append("```")
            md.append("\n" + "\n".join(lines) + "\n")
        if k == "li":
            prev = "li"
        else:
            if prev == "li":
                md.insert(len(md) - 1, "")
            prev = k
    text = "\n".join(md)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def front_matter(meta):
    lines = ["---"]
    for k in ("title", "group", "order", "blurb", "tagline", "about"):
        v = meta.get(k)
        if v not in (None, ""):
            lines.append(f"{k}: {str(v).replace(chr(10), ' ').strip()}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def parse_front_matter(text):
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        body = text[m.end():]
    return meta, body


if __name__ == "__main__":
    import sys
    data = open(sys.argv[1], "rb").read()
    r = convert(data)
    print(r["cover"])
    print(r["markdown"])
