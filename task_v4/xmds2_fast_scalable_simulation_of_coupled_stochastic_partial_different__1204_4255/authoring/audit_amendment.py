import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "concept_1" / "evaluator" / "evaluate.py"
specification = importlib.util.spec_from_file_location("checked_evaluator", path)
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)
cases = json.loads((path.parent / "hidden" / "cases.json").read_text())
transport = {"stderr": "", "returncode": 0, "timed_out": False, "elapsed_seconds": 0.1}
evaluator.run_submission = lambda *args, **kwargs: {**transport, "stdout": ("[" * 2000 + "]" * 2000 + "\n") * len(cases)}
nested = evaluator.evaluate(ROOT / "concept_1" / "participant" / "baseline")
zero_path = ROOT / "concept_1" / "adversary" / "zero_cost_case.json"
zero = json.loads(zero_path.read_text())
if isinstance(zero, dict):
    instance = zero.get("instance", zero)
else:
    instance = zero[0]["instance"]
case_file = ROOT / "authoring" / "zero_regression.json"
case_file.write_text(json.dumps([{"id": "zero", "family": "zero", "instance": instance, "baseline": {"cost": 0}}]) + "\n")
evaluator.run_submission = lambda *args, **kwargs: {**transport, "stdout": json.dumps({"actions": [["read"] for request in instance["requests"]]}) + "\n"}
zero_result = evaluator.evaluate(ROOT / "concept_1" / "participant" / "baseline", case_file)
report = {"nested_json_cleanly_rejected": nested["valid"] is False, "zero_cost_rule": zero_result["valid"] and zero_result["core_score"] == 0, "participant_unchanged": {}, "hidden_cases_unchanged": {}}
for record_path in (ROOT / "concept_1" / "attempts").glob("v_*.run.json"):
    import hashlib
    record = json.loads(record_path.read_text())
    participant = ROOT / "concept_1" / "participant"
    current = {str(file.relative_to(participant)): hashlib.sha256(file.read_bytes()).hexdigest() for file in participant.rglob("*") if file.is_file() and "__pycache__" not in file.parts}
    report["participant_unchanged"][record_path.name] = current == record["participant_sha256"]
    report["hidden_cases_unchanged"][record_path.name] = hashlib.sha256((path.parent / "hidden" / "cases.json").read_bytes()).hexdigest() == record["evaluator_sha256"]["hidden/cases.json"]
report["passed"] = report["nested_json_cleanly_rejected"] and report["zero_cost_rule"] and all(report["participant_unchanged"].values()) and all(report["hidden_cases_unchanged"].values())
(ROOT / "authoring" / "amendment_audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
if not report["passed"]:
    raise SystemExit(1)
