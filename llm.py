"""OpenRouter client with automatic fallback across free models.

Config (.env):
  OPENROUTER_API_KEY   your key (never commit it)
  OPENROUTER_BASE_URL  https://openrouter.ai/api/v1
  MODELS               comma list, tried in order. "auto" = discover current :free models.
  MOCK_LLM=1           offline demo / testing mode (no API calls)

Switch to Claude later: point OPENROUTER_BASE_URL/MODELS at a Claude model on OpenRouter
(e.g. MODELS=anthropic/claude-sonnet-4.5) - nothing else changes.
"""
import json
import os
import re
import time

import httpx

BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MOCK = os.getenv("MOCK_LLM", "0") == "1"

_free_cache = {"at": 0, "ids": []}
last_model_used = {"id": None}


def _discover_free_models():
    """Ask OpenRouter which :free models exist right now (the list rotates often)."""
    if time.time() - _free_cache["at"] < 3600 and _free_cache["ids"]:
        return _free_cache["ids"]
    ids = []
    try:
        r = httpx.get(f"{BASE_URL}/models", timeout=20)
        data = r.json().get("data", [])
        free = [m for m in data if str(m.get("id", "")).endswith(":free")]
        # prefer big-context instruct models
        free.sort(key=lambda m: m.get("context_length") or 0, reverse=True)
        ids = [m["id"] for m in free[:6]]
    except Exception:
        pass
    _free_cache.update(at=time.time(), ids=ids)
    return ids


def model_list():
    raw = os.getenv("MODELS", "openrouter/free,auto").strip()
    out = []
    for m in [x.strip() for x in raw.split(",") if x.strip()]:
        if m == "auto":
            out.extend(_discover_free_models())
        else:
            out.append(m)
    seen, uniq = set(), []
    for m in out:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq or ["openrouter/free"]


class LLMError(Exception):
    pass


def chat(messages, temperature=0.4, max_tokens=1800):
    """Send chat messages; try each model until one answers."""
    if MOCK:
        return _mock(messages)
    if not API_KEY:
        raise LLMError("OPENROUTER_API_KEY is missing in .env")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Interview Coach",
    }
    errors = []
    for model in model_list():
        try:
            r = httpx.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json={"model": model, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
                timeout=120,
            )
            if r.status_code != 200:
                errors.append(f"{model}: HTTP {r.status_code} {r.text[:160]}")
                continue
            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            if not text.strip():
                errors.append(f"{model}: empty reply")
                continue
            last_model_used["id"] = data.get("model", model)
            return text.strip()
        except Exception as e:
            errors.append(f"{model}: {e}")
    hint = ""
    if any("429" in e for e in errors):
        hint = (" (Free-model limit hit: 20/min, 50/day on an unfunded OpenRouter account. "
                "Wait a minute, or try again tomorrow.)")
    raise LLMError("All models failed" + hint + " | " + " || ".join(errors[-3:]))


def chat_json(messages, **kw):
    """Ask for JSON; tolerate models that wrap it in prose or code fences."""
    text = chat(messages, **kw)
    obj = extract_json(text)
    if obj is None:
        # one repair attempt
        text2 = chat(messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": "Return ONLY the valid JSON object, nothing else."},
        ], **kw)
        obj = extract_json(text2)
    if obj is None:
        raise LLMError("Model did not return valid JSON")
    return obj


def extract_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
        start = text.find("{", start + 1)
    return None


def _mock(messages):
    last = messages[-1]["content"]
    sysmsg = messages[0]["content"] if messages else ""
    last_model_used["id"] = "mock"
    if "GRADE" in sysmsg:
        return json.dumps({
            "score": 6, "verdict": "Borderline hire",
            "strengths": ["Clear structure", "Mentioned trade-offs"],
            "mistakes": [{"said": "Bagging reduces bias", "correct": "Bagging mainly reduces variance; boosting reduces bias."}],
            "corrected_answer": "MOCK corrected: Bagging trains models in parallel on bootstrap samples and averages them, which mainly cuts variance.",
            "explanation": "MOCK explanation:\n- **Bagging** = parallel, averages away noise\n- **Boosting** = sequential, fixes errors",
            "gaps": ["No production metrics", "Missed evaluation strategy"],
            "model_answer": "MOCK model answer: define, explain mechanism, trade-offs, a real example, how you measured it.",
            "delivery_tips": "Lead with the one-line answer, then go deeper.",
            "follow_up": "MOCK follow-up: How would you measure that in production?"})
    if "GENERATE_QUESTION" in sysmsg:
        return json.dumps({"question": "MOCK: How do you reduce hallucinations in a RAG system?",
                           "key_points": ["grounding", "citations", "evals"]})
    if "SESSION_REPORT" in sysmsg:
        return json.dumps({"overall": "MOCK report", "top_fixes": ["Add metrics"], "ready_for": "Mid-level"})
    return "MOCK coach reply to: " + last[:200]
