import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant"))
from baseline import baseline_policy
from cascade_sim import BASES, FEATURES
from scoring import TARGET


def save_text(relative, text):
    patch = f"*** Begin Patch\n*** Add File: {ROOT / relative}\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, capture_output=True)


def save_json(relative, value):
    save_text(relative, json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    if (ROOT / "evaluator/frozen.json").exists():
        raise RuntimeError("already frozen; do not replace target or cases")
    for name in ["train.json", "dev.json", "distribution.json"]:
        save_text(f"participant/input/{name}", (ROOT / "participant/inputs" / name).read_text())
    save_json("participant/baseline/policy.json", baseline_policy())
    size = {"type": "object", "additionalProperties": False, "required": ["basis", "scale", "round"],
            "properties": {"basis": {"enum": sorted(BASES)}, "scale": {"type": "number", "minimum": 0.0625, "maximum": 16},
                           "round": {"enum": ["ceil", "floor", "nearest"]}}}
    properties = {"size": size, "reuse": {"enum": ["all", "roots", "recent"]},
                  "batch": {"enum": ["pass", "smallest"]}, "stop": {"type": "boolean"}}
    action = {"type": "object", "additionalProperties": False, "minProperties": 1, "properties": properties}
    schedule_action = {**action, "required": list(properties), "properties": {**properties, "stop": {"const": False}}}
    condition = {"type": "array", "minItems": 3, "maxItems": 3, "prefixItems": [
        {"enum": sorted(FEATURES)}, {"enum": ["lt", "le", "gt", "ge"]}, {"type": "number"}]}
    rule = {"type": "object", "additionalProperties": False, "required": ["when", "action"],
            "properties": {"when": {"type": "array", "minItems": 1, "maxItems": 8, "items": condition}, "action": action}}
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Adaptive Cascade policy v1",
              "type": "object", "additionalProperties": False, "required": ["version", "max_passes", "schedule", "rules"],
              "properties": {"version": {"type": "integer", "const": 1},
                             "max_passes": {"type": "integer", "minimum": 4, "maximum": 20},
                             "schedule": {"type": "array", "minItems": 4, "maxItems": 4, "items": schedule_action},
                             "rules": {"type": "array", "maxItems": 64, "items": rule}}}
    save_json("participant/policy.schema.json", schema)
    report = json.loads((ROOT / "champions/baseline/hidden.json").read_text())
    calibration = json.loads((ROOT / "adversary/calibration/summary.json").read_text())
    timestamp = datetime.now(timezone.utc).isoformat()
    save_json("adversary/target_freeze_report.json", {
        "frozen_at_utc": timestamp, "mode": "A_BASELINE_IMPROVEMENT", "target": TARGET,
        "baseline_hidden_normal_frames": report["candidate_total"]["frames"],
        "baseline_hidden_normal_failures": report["candidate_total"]["failures"],
        "baseline_hidden_stress_frames": report["stress"]["frames"],
        "baseline_hidden_stress_failures": report["stress"]["failures"],
        "baseline_hidden_reliability_pass": report["reliability_pass"],
        "training_probes": calibration,
        "rationale": "Best single-factor training improvement is 7.3663%, below 8%, and it misses the 3% bandwidth and short-frame gates. Eight passes improves 3.7525% but fails conditional-tail FER. Shortening ten passes improves only 2.5016%. Per-family tradeoffs justify multivariate adaptive optimization, not a 1D sweep.",
        "calibration_limit": "No improved candidate was tested on hidden cases. No fresh worker has run. Feasibility of all gates together is unproven; hard_open is intentional.",
        "fresh_attempts_before_freeze": 0,
    })
    save_json("adversary/status.json", {"status": "audited_open", "known_correctness_blockers": [],
              "baseline_reliability_pass": True, "one_factor_probes_meet_all_improvement_gates": False,
              "risks": ["finite sample FER is not a security guarantee", "conditional stress is not population FER", "parent must hide the complete trusted tree", "fresh feasibility not established"]})
    save_json("champions/status.json", {"baseline": "baseline/policy.json", "improved_champion": None,
              "baseline_hidden_reliability_pass": True, "promotion_rule": "all frozen gates must pass"})
    save_json("status.json", {"concept": "concept_1", "mode": "A_BASELINE_IMPROVEMENT", "status": "hard_open",
              "frozen": True, "frozen_at_utc": timestamp, "ready_for_fresh_attempt": True,
              "target": TARGET, "public_workspace": "participant", "submission": "policy.json",
              "evaluator": "evaluator/evaluate.py", "baseline": "participant/baseline/policy.json",
              "hidden_cases": "evaluator/hidden/cases.json", "target_report": "adversary/target_freeze_report.json",
              "fresh_agents_launched": 0, "improved_champion": None,
              "baseline_hidden_normal_failures": 0, "baseline_hidden_normal_frames": 4096,
              "baseline_hidden_stress_failures": 0, "baseline_hidden_stress_frames": 768,
              "parent_evaluation_command": "python3 -I evaluator/evaluate.py --policy /absolute/path/to/policy.json --split hidden --jobs 8 --output /absolute/path/to/report.json",
              "isolation": "Parent copies only participant; original trusted reference and hidden data remain inaccessible to the worker. Candidate JSON is never imported or executed."})
    frozen_paths = [path for path in (ROOT / "participant").rglob("*")
                    if path.is_file() and "__pycache__" not in path.parts]
    frozen_paths.extend(ROOT / relative for relative in ["evaluator/evaluate.py", "evaluator/test_validation.py",
                        "evaluator/build_cases.py", "evaluator/hidden/cases.json", "champions/baseline/policy.json",
                        "adversary/target_freeze_report.json"])
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(frozen_paths)}
    save_json("evaluator/frozen.json", {"version": 1, "frozen_at_utc": timestamp, "target": TARGET,
              "sha256": hashes, "fresh_attempts_before_freeze": 0})
    print(json.dumps({"frozen": True, "target": TARGET, "hashed_files": len(hashes)}))


if __name__ == "__main__":
    main()
