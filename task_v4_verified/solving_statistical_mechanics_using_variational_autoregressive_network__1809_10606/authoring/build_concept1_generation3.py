from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
GENERATION = CONCEPT / "generations/generation_3"


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False))


def main():
    for folder in ("participant/input", "evaluator/hidden", "attempts", "champions", "adversary"):
        (GENERATION / folder).mkdir(parents=True, exist_ok=True)
    cases = {item["id"]: item for item in read(CONCEPT / "adversary/champion2_connected_stress/challenge_space.json")}
    scores = {item["id"]: item for item in read(CONCEPT / "adversary/champion2_connected_stress/results.json")}
    selected = [("cold_cycles", "frustrated_cages_3_" + str(index)) for index in range(3)]
    selected += [("coupled_regions", "interacting_regions_3_" + str(index)) for index in range(3)]
    manifest, baseline_records = [], []
    for family, identifier in selected:
        case, previous = cases[identifier], scores[identifier]
        raw = json.dumps(case["instance"]).encode()
        (GENERATION / "evaluator/hidden" / (identifier + ".json")).write_bytes(raw)
        manifest.append({"id": identifier, "family": family, "file": identifier + ".json", "sha256": hashlib.sha256(raw).hexdigest(),
                         "baseline_kl": previous["kl"], "baseline_ess": previous["ess"], "baseline_provenance": "concept_1/adversary/champion2_connected_stress/results.json"})
        baseline_records.append(dict(previous, family=family))
    old_manifest = {item["id"]: item for item in read(CONCEPT / "generations/generation_2/evaluator/hidden/manifest.json")["cases"]}
    old_scores = {item["id"]: item for item in read(CONCEPT / "generations/generation_2/attempts/v_1_run/replay_score.json")["cases"]}
    for identifier in ("quartets_2", "quintets_2", "mixed_2"):
        previous = old_scores[identifier]
        raw = (CONCEPT / "generations/generation_2/evaluator/hidden" / old_manifest[identifier]["file"]).read_bytes()
        (GENERATION / "evaluator/hidden" / (identifier + ".json")).write_bytes(raw)
        manifest.append({"id": identifier, "family": "local_sectors", "file": identifier + ".json", "sha256": hashlib.sha256(raw).hexdigest(),
                         "baseline_kl": previous["kl"], "baseline_ess": previous["ess"], "baseline_provenance": "concept_1/generations/generation_2/attempts/v_1_run/replay_score.json"})
        baseline_records.append(dict(previous, family="local_sectors"))
    write(GENERATION / "participant/input/example_cycles.json", cases["frustrated_cages_2_1"]["instance"])
    write(GENERATION / "participant/input/example_coupled.json", cases["interacting_regions_2_0"]["instance"])
    shutil.copyfile(CONCEPT / "generations/generation_2/participant/input/example_quartets.json", GENERATION / "participant/input/example_local_sectors.json")
    spec = importlib.util.spec_from_file_location("third_evaluator", GENERATION / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    write(GENERATION / "evaluator/hidden/manifest.json", {"version": 3, "cases": manifest, "families": ["cold_cycles", "coupled_regions", "local_sectors"], "targets_fixed_before_fresh": True})
    families = {family: float(np.mean([record["kl"] for record in baseline_records if record["family"] == family])) for family in sorted({record["family"] for record in baseline_records})}
    mean = float(np.mean([record["kl"] for record in baseline_records]))
    baseline = {"valid": True, "passed": False, "mean_kl": mean, "worst_family_kl": max(families.values()), "family_kl": families,
                "minimum_ess": min(record["ess"] for record in baseline_records), "core_score": 1 / (1 + mean),
                "worst_family_score": 1 / (1 + max(families.values())), "runtime_resource_score": 1 - max(record["wall_seconds"] for record in baseline_records) / 120,
                "baseline_mean_kl": mean, "baseline_ratio": 1, "targets": evaluator.TARGET, "cases": baseline_records,
                "reason": "Frozen calibration reuses actual same-source same-instance exact scores and identical invocation limits; all source reports are retained."}
    write(GENERATION / "adversary/baseline_report.json", baseline)
    write(GENERATION / "adversary/ratchet_rationale.json", {"ratchet": 2, "previous_task_passed": True,
          "challenge_count": 36, "failure_count_kl_over_004": 3, "peak_kl": 16.569112576267543,
          "root_cause": "Regional initialization and refinement are not uniformly reliable on strongly interacting and cold cyclic materials. Local-sector controls prevent replacing the model by an earlier method that failed those controls.",
          "old_champion_control": "The older prefix-based champion solves the three new regressions, but fails the retained local-sector family. A private generic portfolio is available for independent feasibility testing.",
          "target_rationale": "Keep absolute accuracy/tail targets and overall 60% improvement; do not impose arbitrary relative tightening on already accurate families.",
          "calibration_policy": "Reuse prior exact calibration of identical source on identical numerical instances; freeze before this fresh attempt, with no target updates after launch."})
    frozen = {str(path.relative_to(GENERATION)): hashlib.sha256(path.read_bytes()).hexdigest() for folder in (GENERATION / "participant", GENERATION / "evaluator") for path in sorted(folder.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}
    write(GENERATION / "adversary/release_manifest.json", {"frozen_at": datetime.now(timezone.utc).isoformat(), "sha256": frozen})
    write(GENERATION / "status.json", {"status": "built_not_tested", "verification_mode": "A", "generation": 3,
          "ratchet_generations": 2, "solvability": "unknown", "targets_frozen_before_fresh_launch": True,
          "baseline": baseline, "ready": True})
    print(json.dumps({"ready": True, "mean_baseline_kl": mean, "families": families, "minimum_ess": baseline["minimum_ess"]}))


if __name__ == "__main__":
    main()
