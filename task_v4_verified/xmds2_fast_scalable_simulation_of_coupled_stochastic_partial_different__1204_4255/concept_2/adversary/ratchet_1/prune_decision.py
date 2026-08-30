import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "generations/generation_2"
files = {}
protocol = json.loads((STAGE / "participant/input/protocol.json").read_text())
protocol["resources"]["evaluation_wall_seconds"] = 660
protocol["reference"]["evaluation_pruning"] = "First compute the exact fixed-lattice certificate and diagnostics for all 37 members. Prioritize members by ascending diagnostic guard factor, breaking ties by public family order. Each visited member receives the unchanged full temporal, spatial and independent-method reference checks. Stop at the first reference-unresolved or threshold-failing member. A trustworthy failing member proves the all-members target false; no unchecked member can turn that zero into a pass. A pass requires all 37 fully validated members."
protocol["reference"]["validity_scope"] = "valid means admissible input and a numerically trustworthy acceptance/rejection decision. A valid early rejection does not claim convergence of unvisited members; complete_assessment and skipped_members make this explicit. Any visited unresolved reference yields valid=false."
protocol["target"]["family_score"] = "Binary indicator: 1 exactly when this member has a resolved reference, conservative_gap>=0.3 and all four diagnostic/certificate limits pass; otherwise 0. The former continuous margin score is retained only as continuous_score diagnostic."
protocol["target"]["core_score"] = "Minimum of all 37 binary family scores, equal to worst_family_score. A fully verified failing member fixes this minimum at 0 regardless of unvisited members, so early rejection gives the exact binary objective. Score 1 requires all 37 members passed with resolved references. Invalid/unresolved/resource failures score 0."
protocol["target"]["definition"] += " The mathematical acceptance set is unchanged by the binary scoring/early-rejection implementation."
protocol["interface"]["output"] += " Binary scores and complete_assessment, skipped_members, observed_continuous_score are reported; only complete, fully referenced assessments can pass."
protocol["resources"]["wall_budget_rationale"] = "53-case and 37-case full-sweep drafts hit 420 wall seconds under host contention, using only 345.45 and 257.15 CPU seconds. Final wall budget is 660 seconds; CPU budget remains 400. Certified early rejection reduces failing-witness cost without weakening acceptance."
for name in ("participant/input/protocol.json", "evaluator/hidden/protocol.json"):
    files[STAGE / name] = json.dumps(protocol, indent=2) + "\n"
api = (STAGE / "participant/workspace/search_api.py").read_text()
start = api.index("def assess(parameters):")
end = api.index("\n\ndef screen(", start)
replacement = '''def assess(parameters):
    reports = []
    candidates = list(family(parameters))
    screening = certificate_screen(parameters, all_members=True)
    factors = {name: min([1.0] + [limit / max(metrics[key], 1e-300) for key, limit in PROTOCOL["limits"].items()]) for name, metrics in screening.items()}
    candidates.sort(key=lambda item: factors[item[0]])
    reason = "robust_false_convergence_target_met"
    valid = True
    for name, member in candidates:
        descriptor = next(item for item in PROTOCOL["family"] if item["name"] == name)
        report = {"name": name, "group": descriptor["group"], **assess_member(member)}
        report["continuous_score"] = report["family_score"]
        report["family_score"] = float(report["passed"])
        reports.append(report)
        if not report["reference"]["resolved"]:
            valid = False
            reason = "reference_not_resolved"
            break
        if not report["passed"]:
            reason = "certified_family_threshold_failure"
            break
    complete = len(reports) == len(PROTOCOL["family"])
    passed = valid and complete and all(report["passed"] for report in reports)
    visited = {report["name"] for report in reports}
    score = float(passed)
    return {
        "protocol_id": PROTOCOL["protocol_id"], "core_score": score,
        "worst_family_score": score, "valid": valid, "passed": passed,
        "reason": reason, "family": reports,
        "complete_assessment": complete, "expected_family_members": len(PROTOCOL["family"]),
        "evaluated_family_members": len(reports),
        "skipped_members": [member["name"] for member in PROTOCOL["family"] if member["name"] not in visited],
        "certificate_screen": screening,
        "observed_continuous_score": min(report["continuous_score"] for report in reports),
        "group_scores": {group: min(report["family_score"] for report in reports if report["group"] == group) for group in sorted({report["group"] for report in reports})},
    }
'''
api = api[:start] + replacement + api[end:]
for name in ("participant/workspace/search_api.py", "evaluator/hidden/search_api.py"):
    files[STAGE / name] = api
evaluator = (STAGE / "evaluator/evaluate.py").read_text().replace("timeout=420", "timeout=660").replace('"wall_limit_seconds": 420', '"wall_limit_seconds": 660')
files[STAGE / "evaluator/evaluate.py"] = evaluator
for name in ("participant/workspace/README.md", "README.md"):
    text = (STAGE / name).read_text().replace("420-second", "660-second").replace("420 seconds", "660 seconds")
    text = text.replace("A single unresolved reference terminates a full assessment with zero credit; no unresolved or unassessed member can pass.", "After the cheap all-member guard sweep, each visited member receives full reference validation. A verified threshold failure ends assessment with exact binary score zero; unvisited members are explicit. Only all 37 fully checked passing members receive score one. An unresolved visited reference fails closed.")
    text += "\nThe binary objective enables certified early rejection without changing the acceptance set. Wall allowance is 660 seconds, CPU allowance remains 400 seconds. Continuous margin diagnostics are not the official score.\n"
    files[STAGE / name] = text
status = json.loads((STAGE / "status.json").read_text())
status.update(evaluation_wall_seconds=660, build_status="certified_early_rejection_validation_running", scoring="binary all-members acceptance; exact early rejection on a fully referenced failing member")
files[STAGE / "status.json"] = json.dumps(status, indent=2) + "\n"
files[ROOT / "adversary/ratchet_1/draft_37_budget_failure.json"] = (STAGE / "attempts/baseline.evaluation.json").read_text()
sections = ["*** Begin Patch"]
for path, content in files.items():
    sections.append("*** Add File: " + str(path.relative_to(ROOT)))
    sections.extend("+" + line for line in content.splitlines())
sections.append("*** End Patch")
subprocess.run(["apply_patch"], input="\n".join(sections) + "\n", text=True, cwd=ROOT, check=True)
