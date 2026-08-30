import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_2"
PUBLIC = CONCEPT / "participant"
EVALUATOR = CONCEPT / "evaluator"
if not (CONCEPT / "generations/generation_1/snapshot.json").exists():
    raise RuntimeError("archive generation1 before ratcheting")
if (CONCEPT / "attempts/v_2").exists():
    raise RuntimeError("refusing to change an already-tested generation")
shutil.copyfile(PUBLIC / "workspace/design_common.py", EVALUATOR / "design_common.py")
sys.path.insert(0, str(EVALUATOR))
from design_common import aggregate, generate_supports, load_case, read_design, score_case


family = json.loads((PUBLIC / "input/family.json").read_text())
family["densities"] = {"dense_iid": [0.28, 0.30, 0.32]}
family["generation"] = 2
(PUBLIC / "input/family.json").write_text(json.dumps(family, indent=2) + "\n")
shutil.copyfile(CONCEPT / "champions/generation_1/design.json", PUBLIC / "baseline/design.json")
baseline = read_design(PUBLIC / "baseline/design.json")
practice = {}
hidden = {}
results = {}
for case_index, identifier in enumerate(family["cases"]):
    case = load_case(PUBLIC / "input" / (identifier + ".json.gz"))
    practice[identifier] = generate_supports(case, 28173 + 37 * case_index, 256, family["densities"])
    hidden[identifier] = generate_supports(case, 19870471 + 113 * case_index, 4096, family["densities"])
    results[identifier] = score_case(case, hidden[identifier], baseline)
    print(identifier, results[identifier], flush=True)
(PUBLIC / "input/practice.json").write_text(json.dumps(practice, separators=(",", ":")) + "\n")
(EVALUATOR / "hidden/supports.json").write_text(json.dumps(hidden, separators=(",", ":")) + "\n")
score = aggregate(results)
protocol = {"mode": "C", "generation": 2, "metric": "exact_all_four_logicals_correctability_fraction",
            "target_fraction": 0.85, "group_floors": {group: 0.60 for group in score["groups"]},
            "baseline_fraction": score["correctness_fraction"], "cases": family["cases"],
            "supports_per_group": 4096, "fixed_before_first_attempt": True,
            "fresh_agent_attempts": 0}
paths = [EVALUATOR / "design_common.py", EVALUATOR / "evaluate.py", EVALUATOR / "hidden/supports.json"]
paths += [EVALUATOR / "hidden" / (identifier + ".json.gz") for identifier in family["cases"]]
protocol["sha256"] = {str(path.relative_to(EVALUATOR)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
(EVALUATOR / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
(PUBLIC / "input/objective.json").write_text(json.dumps({key: value for key, value in protocol.items() if key != "sha256"}, indent=2) + "\n")
report = {"generation": 2, "baseline_score": score, "target_fraction": 0.85, "group_floor": 0.60,
          "basis": "Champion failed in dense IID erasure profiles despite strong nominal and structured-noise robustness. A separate 18,432-support precision audit found worst fraction 0.49414 at density 0.32. Original score thresholds are unchanged; the physical density workload is the ratchet.",
          "broad_search": "adversary/broad_private/champion_1.json",
          "precision_audit": "adversary/broad_private/dense_precision.json",
          "cluster": "short finite-size logical dependencies proliferating under dense independent spacetime erasures",
          "known_passing_dense_design": False}
(CONCEPT / "adversary/ratchet_1.json").write_text(json.dumps(report, indent=2) + "\n")
(CONCEPT / "status.json").write_text(json.dumps({"mode": "C", "current_generation": 2,
    "ratchet_generations": 1, "status": "pending_tournament", "previous_generation_status": "solved",
    "baseline_score": score, "solvability": "unknown for dense generation; demonstrated for nominal generation"}, indent=2) + "\n")
print(json.dumps({"baseline_core": score["core_score"], "baseline_worst": score["worst_family_score"]}, indent=2))
