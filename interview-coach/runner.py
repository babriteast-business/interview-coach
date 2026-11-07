"""Runs candidate code in a separate Python process against the problem's tests.
Grading here does not depend on the LLM at all - pass/fail is real."""
import json
import os
import subprocess
import sys
import tempfile

HARNESS = r'''
import io, json, sys, contextlib, sqlite3, traceback
code = open(sys.argv[1], encoding="utf-8").read()
spec = json.load(open(sys.argv[2], encoding="utf-8"))
out = io.StringIO()
results = []
if spec["kind"] == "sql":
    for t in spec["tests"]:
        db = sqlite3.connect(":memory:")
        try:
            db.executescript(t["setup"])
            rows = [list(r) for r in db.execute(code).fetchall()]
            exp = t["expected"]
            ok = rows == exp if t.get("ordered", True) else sorted(map(str, rows)) == sorted(map(str, exp))
            results.append({"name": t["name"], "ok": ok, "got": rows[:20], "expected": exp})
        except Exception as e:
            results.append({"name": t["name"], "ok": False, "error": str(e)})
else:
    ns = {}
    try:
        with contextlib.redirect_stdout(out):
            exec(compile(code, "solution.py", "exec"), ns)
    except Exception:
        print("@@RESULT@@" + json.dumps({"compile_error": traceback.format_exc(limit=3),
                                          "stdout": out.getvalue()[-2000:]}))
        sys.exit(0)
    for t in spec["tests"]:
        try:
            with contextlib.redirect_stdout(out):
                got = eval(t["expr"], ns)
            exp = t["expected"]
            try:
                got = json.loads(json.dumps(got))   # tuples -> lists, same shape as JSON tests
            except Exception:
                pass
            ok = got == exp
            if not ok and isinstance(got, (list, tuple)) and t.get("unordered"):
                ok = sorted(map(repr, got)) == sorted(map(repr, exp))
            if not ok and isinstance(got, float) and isinstance(exp, (int, float)):
                ok = abs(got - exp) < 1e-6
            results.append({"name": t["expr"], "ok": bool(ok), "got": repr(got)[:300], "expected": repr(exp)[:300]})
        except Exception as e:
            results.append({"name": t["expr"], "ok": False, "error": f"{type(e).__name__}: {e}"})
print("@@RESULT@@" + json.dumps({"results": results, "stdout": out.getvalue()[-2000:]}))
'''


def _limits():
    """Linux only (Render): cap CPU, memory and file size of the candidate's process."""
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024,) * 2)


def run(problem, code, timeout=10):
    with tempfile.TemporaryDirectory() as d:
        paths = {n: os.path.join(d, n) for n in ("harness.py", "solution.txt", "spec.json")}
        with open(paths["harness.py"], "w", encoding="utf-8") as f:
            f.write(HARNESS)
        with open(paths["solution.txt"], "w", encoding="utf-8") as f:
            f.write(code)
        with open(paths["spec.json"], "w", encoding="utf-8") as f:
            json.dump({"kind": problem.get("kind", "python"), "tests": problem["tests"]}, f)
        try:
            p = subprocess.run([sys.executable, "-I", paths["harness.py"], paths["solution.txt"], paths["spec.json"]],
                               capture_output=True, text=True, timeout=timeout, cwd=d,
                               # no secrets (API key, DATABASE_URL) reach the candidate's code
                               env={"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                                    "PYTHONIOENCODING": "utf-8"},
                               preexec_fn=_limits if os.name == "posix" else None)
        except subprocess.TimeoutExpired:
            return {"error": f"Time limit exceeded ({timeout}s). Check for infinite loops or slow complexity.",
                    "results": [], "passed": 0, "total": len(problem["tests"])}
        marker = p.stdout.rfind("@@RESULT@@")
        if marker == -1:
            return {"error": (p.stderr or p.stdout)[-1500:] or "No output", "results": [],
                    "passed": 0, "total": len(problem["tests"])}
        data = json.loads(p.stdout[marker + len("@@RESULT@@"):])
        if "compile_error" in data:
            return {"error": data["compile_error"], "stdout": data.get("stdout", ""), "results": [],
                    "passed": 0, "total": len(problem["tests"])}
        res = data["results"]
        return {"results": res, "stdout": data.get("stdout", ""),
                "passed": sum(r["ok"] for r in res), "total": len(res)}
