"""Adversarial integrity tests, confined to this task's adversary directory."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
specification = importlib.util.spec_from_file_location("checker", ROOT / "evaluator" / "evaluate.py")
checker = importlib.util.module_from_spec(specification)
specification.loader.exec_module(checker)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    champion = json.loads((ROOT / "champions" / "builder" / "witness.json").read_text())
    checks = []
    cases = {"empty": {}, "extra_key": {**champion, "claimed_score": 100},
             "bool_depth": {**champion, "depth": True}, "float_depth": {**champion, "depth": 36.0},
             "short_depth": {**champion, "depth": 0}, "long_depth": {**champion, "depth": 1000000},
             "wrong_observable": {**champion, "observable": "magnetization"},
             "zero_fields": {**champion, "knots": [0.0] * 6},
             "clifford": {**champion, "knots": [1.5707963267948966] * 6},
             "nan": {**champion, "knots": [float("nan")] * 6},
             "infinity": {**champion, "knots": [float("inf")] * 6},
             "booleans": {**champion, "knots": [True] * 6},
             "wrong_count": {**champion, "knots": [0.7] * 5},
             "slew": {**champion, "depth": 12, "knots": [0.12,1.45,0.12,1.45,0.12,1.45]}}
    for name, witness in cases.items():
        directory = ROOT / "adversary" / name
        directory.mkdir(exist_ok=True)
        (directory / "witness.json").write_text(json.dumps(witness))
        result = checker.evaluate(directory)
        checks.append({"name": name, "passed": not result["valid"] and not result["passed"] and result["worst_family_score"] == 0,
                       "reason": result["reason"]})
    for name, text in (("duplicate", '{"depth":36,"depth":24}'), ("oversized", " " * 16385), ("malformed", "{")):
        directory = ROOT / "adversary" / name
        directory.mkdir(exist_ok=True)
        (directory / "witness.json").write_text(text)
        result = checker.evaluate(directory)
        checks.append({"name": name, "passed": not result["valid"], "reason": result["reason"]})
    directory = ROOT / "adversary" / "missing"
    directory.mkdir(exist_ok=True)
    result = checker.evaluate(directory)
    checks.append({"name": "missing", "passed": not result["valid"], "reason": result["reason"]})
    directory = ROOT / "adversary" / "symlink"
    directory.mkdir(exist_ok=True)
    link = directory / "witness.json"
    if not link.is_symlink():
        link.symlink_to(ROOT / "champions" / "builder" / "witness.json")
    result = checker.evaluate(directory)
    checks.append({"name": "symlink", "passed": not result["valid"], "reason": result["reason"]})
    normal = checker.evaluate(ROOT / "champions" / "builder")
    directory = ROOT / "adversary" / "poison"
    directory.mkdir(exist_ok=True)
    (directory / "input").mkdir(exist_ok=True)
    (directory / "input" / "target.json").write_text('{"error_min":0,"spread_max":999}')
    (directory / "witness.json").write_text(json.dumps(champion))
    for name in ("simulator.py", "protocol.py", "numpy.py", "sitecustomize.py", "evaluate.py"):
        (directory / name).write_text('raise RuntimeError("UNTRUSTED SUBMISSION CODE EXECUTED")\n')
    environment = dict(os.environ, PYTHONPATH=str(directory), PYTHONDONTWRITEBYTECODE="1")
    process = subprocess.run([sys.executable, "-I", str(ROOT / "evaluator" / "evaluate.py"),
                              "--submission", str(directory), "--output", str(directory / "result.json")],
                             cwd=directory, env=environment, capture_output=True, text=True, timeout=90)
    poisoned = json.loads((directory / "result.json").read_text()) if process.returncode == 0 else {}
    fields = ("valid", "passed", "core_score", "worst_family_score", "resource_score", "families", "target_sha256")
    checks.append({"name": "isolated_from_submission_and_cwd", "passed": all(normal.get(key) == poisoned.get(key) for key in fields),
                   "returncode": process.returncode})
    public = (ROOT / "participant" / "input" / "target.json").read_bytes()
    trusted = (ROOT / "evaluator" / "resources" / "target.json").read_bytes()
    checks.append({"name": "public_trusted_target_equal", "passed": public == trusted})
    for name in ("simulator.py", "protocol.py"):
        checks.append({"name": "frozen_copy_" + name,
                       "passed": (ROOT / "participant" / "workspace" / name).read_bytes() == (ROOT / "evaluator" / "resources" / name).read_bytes()})
    report = {"passed": all(check["passed"] for check in checks), "checks": checks}
    options.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "checks": len(checks)}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
