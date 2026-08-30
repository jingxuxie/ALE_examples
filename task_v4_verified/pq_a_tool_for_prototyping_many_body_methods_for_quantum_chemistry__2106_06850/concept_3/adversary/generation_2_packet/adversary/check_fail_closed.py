"""Bounded private adversarial checks; no participant code is executed."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
specification = importlib.util.spec_from_file_location("private_evaluate", ROOT / "evaluator" / "evaluate.py")
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)


def main():
    started = time.perf_counter()
    certificate = json.loads((ROOT / "evaluator" / "private" / "certificates.json").read_text())
    tests = []
    with tempfile.TemporaryDirectory(prefix="concept3-audit-") as temporary:
        root = Path(temporary)

        def check(name, contents=None, expected_pass=False):
            destination = root / (name + ".json")
            if contents is not None:
                destination.write_text(contents, encoding="utf-8")
            result = evaluator.evaluate(destination)
            tests.append({"name": name, "pass": result["pass"] == expected_pass,
                          "reported_pass": result["pass"], "core": result["core"], "reason": result["reason"]})

        check("certificate", json.dumps(certificate), True)
        for name, contents in (("missing", None), ("malformed", "{"), ("empty", ""),
                               ("duplicate_key", '{"schema_version":1,"schema_version":1,"circuits":[]}'),
                               ("nan", '{"schema_version":1,"circuits":[],"theta":NaN}'),
                               ("oversized", " " * 131073), ("wrong_root", "[]"),
                               ("deep_nesting", "[" * 1500 + "0" + "]" * 1500)):
            check(name, contents)
        mutations = {}
        for name, value in (("bool_angle", True), ("overflow_angle", 1e308), ("infinite_angle", float("inf"))):
            altered = copy.deepcopy(certificate)
            altered["circuits"][0]["gates"][0]["theta"] = value
            mutations[name] = altered
        altered = copy.deepcopy(certificate)
        altered["circuits"][0]["gates"] += altered["circuits"][0]["gates"][:1]
        mutations["over_budget"] = altered
        altered = copy.deepcopy(certificate)
        altered["circuits"][0]["gates"][0] = {"annihilate": [0], "create": [1], "theta": 0.5}
        mutations["spin_flip"] = altered
        altered = copy.deepcopy(certificate)
        altered["circuits"][0]["gates"][0] = {"annihilate": [0, 2, 4], "create": [1, 3, 5], "theta": 0.5}
        mutations["rank_three"] = altered
        altered = copy.deepcopy(certificate)
        altered["circuits"][0]["gates"][0]["create"] = [99]
        mutations["bad_orbital"] = altered
        altered = copy.deepcopy(certificate)
        altered["circuits"][0]["gates"][0]["theta"] *= -1
        mutations["wrong_sign"] = altered
        altered = copy.deepcopy(certificate)
        altered["circuits"][0]["gates"].reverse()
        mutations["wrong_order"] = altered
        altered = copy.deepcopy(certificate)
        altered["circuits"][1] = altered["circuits"][0]
        mutations["duplicate_case"] = altered
        altered = copy.deepcopy(certificate)
        altered["circuits"].pop()
        mutations["missing_case"] = altered
        altered = copy.deepcopy(certificate)
        altered["code"] = "raise SystemExit(0)"
        mutations["unknown_key"] = altered
        for name, altered in mutations.items():
            check(name, json.dumps(altered))
        symlink = root / "symlink.json"
        symlink.symlink_to(ROOT / "evaluator" / "private" / "certificates.json")
        result = evaluator.evaluate(symlink)
        tests.append({"name": "symlink", "pass": not result["pass"] and result["core"] == 0})
        result = evaluator.evaluate(root)
        tests.append({"name": "directory", "pass": not result["pass"] and result["core"] == 0})
    report = {"pass": all(test["pass"] for test in tests), "tests": tests,
              "runtime_seconds": time.perf_counter() - started}
    (ROOT / "adversary" / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"pass": report["pass"], "test_count": len(tests), "runtime_seconds": report["runtime_seconds"]}))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
