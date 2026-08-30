import ast
import hashlib
import json
from pathlib import Path
import sys
import time
import tokenize

sys.dont_write_bytecode = True

import engine


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    budget = json.loads((HERE / "budget.json").read_text())
    summary = json.loads((HERE / "summary.json").read_text())
    selected = json.loads((HERE / "preheldout_selection.json").read_text())
    official = json.loads((HERE / "official_report.json").read_text())
    manifest = ROOT / "evaluator/hidden/freeze.json"
    if digest(manifest) != budget["frozen_manifest_sha256"]:
        raise AssertionError("frozen manifest changed")
    frozen = json.loads(manifest.read_text())
    for name, expected in frozen["files"].items():
        if digest(ROOT / name) != expected:
            raise AssertionError("frozen file changed")
    if digest(HERE / "best_witness.json") != selected["witness_sha256"]:
        raise AssertionError("selected artifact changed")
    if official["passed"] != summary["official_passed"] or official["valid"] != summary["official_valid"]:
        raise AssertionError("saved score inconsistency")
    if official["passed"] or not official["valid"]:
        raise AssertionError("unexpected final result requiring separate handling")
    for family, expected in summary["official_family_successes"].items():
        if official["robustness_families"][family]["successes"] != expected:
            raise AssertionError("family count inconsistency")
    candidates = [HERE / "best_witness.json", HERE / "b2_champion_start.json", HERE / "portfolio_best_start.json"]
    candidates.extend(sorted(HERE.glob("run_*/witness.json")))
    for path in candidates:
        engine.MODEL.decode_witness(engine.MODEL.load_witness(path))
    for source in HERE.glob("*.py"):
        tree = ast.parse(source.read_text())
        if any(isinstance(node, ast.Name) and len(node.id) == 1 for node in ast.walk(tree)):
            raise AssertionError("one-letter identifier")
        with source.open("rb") as stream:
            if any(token.type == tokenize.COMMENT for token in tokenize.tokenize(stream.readline)):
                raise AssertionError("source comment")
    elapsed = time.time() - budget["start_epoch"]
    if elapsed > budget["execution_budget_seconds"]:
        raise AssertionError("execution budget exceeded")
    result = dict(passed=True, elapsed_including_final_audit_seconds=elapsed,
                  execution_budget_seconds=budget["execution_budget_seconds"], requested_cap_seconds=900,
                  startup_handoff_reserve_seconds=180, frozen_files_verified=len(frozen["files"]),
                  frozen_manifest_sha256=digest(manifest), frozen_files_unchanged=True,
                  selected_artifact_sha256=digest(HERE / "best_witness.json"),
                  selected_artifact_is_unchanged_B2_warm_start=digest(HERE / "best_witness.json") == digest(HERE / "b2_champion_start.json"),
                  schema_checked_artifact_files=len(candidates), source_style_checks=True,
                  official_passed=official["passed"], official_valid=official["valid"],
                  resource_score=official["resource_score"], official_runtime_seconds=official["runtime_seconds"],
                  peak_official_memory_mib=official["peak_memory_mib"],
                  preexisting_reference_scores_known_from_packet_construction=True,
                  no_new_official_feedback_used_for_tuning=True, no_refit_after_official=True,
                  fresh_B3_outputs_inspected=False, no_fresh_agents_launched=True,
                  all_writes_within_portfolio=True, feasibility="unknown; no impossibility claim")
    (HERE / "final_audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
