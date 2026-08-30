import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone

import search


def add_file(path, content):
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
    patch += "\n".join("+" + line for line in content.splitlines()) + "\n*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)


def main():
    specification = search.selected_specification(search.SELECTED)
    provisional = search.selected_specification(search.OUTPUT / "provisional_specification.json")
    normalized_actual = [(scenario["coupling_scale"], search.offsets(scenario).tolist()) for scenario in specification["scenarios"]]
    normalized_provisional = [(scenario["coupling_scale"], search.offsets(scenario).tolist()) for scenario in provisional["scenarios"]]
    assert normalized_actual == normalized_provisional
    candidates = []
    for path in sorted((search.OUTPUT / "provisional").glob("worker_*_best_witness.json")):
        witness = json.loads(path.read_text())
        result = search.independent(witness, specification)
        candidates.append((result["worst_family_score"], path, witness, result))
    score, seed_path, witness, reproduced = max(candidates)
    assert reproduced["passed"]
    add_file(search.OUTPUT / "passing_witness.json", json.dumps(witness, indent=2) + "\n")
    source = search.ROOT / "evaluator/evaluate.py"
    source_content = source.read_text()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    evaluator = search.OUTPUT / "selected_evaluator/evaluate.py"
    add_file(evaluator, source_content)
    assert hashlib.sha256(evaluator.read_bytes()).hexdigest() == source_hash
    hidden = evaluator.parent / "hidden"
    selected_content = search.SELECTED.read_text()
    calibration_content = (search.ARCHIVE / "evaluator/hidden/calibration.json").read_text()
    add_file(hidden / "specification.json", selected_content)
    add_file(hidden / "calibration.json", calibration_content)
    hashes = {name: hashlib.sha256((hidden / name).read_bytes()).hexdigest()
              for name in ["specification.json", "calibration.json"]}
    add_file(hidden / "manifest.json", json.dumps(hashes, indent=2) + "\n")
    command = [sys.executable, "-B", str(evaluator), "--submission", str(search.OUTPUT / "passing_witness.json"),
               "--output", str(search.OUTPUT / "selected_evaluator_result.json")]
    subprocess.run(command, check=True, capture_output=True, text=True)
    official = json.loads((search.OUTPUT / "selected_evaluator_result.json").read_text())
    assert official["passed"] and official["valid"] and len(official["scenarios"]) == len(specification["scenarios"]) == 21
    assert abs(official["worst_family_score"] - reproduced["worst_family_score"]) < 3e-12
    finals = [json.loads(path.read_text()) for path in (search.OUTPUT / "provisional").glob("worker_*_final.json")]
    scenarios = official["scenarios"]
    live_specification = json.loads((search.ROOT / "evaluator/hidden/specification.json").read_text())
    live_matches = live_specification == json.loads(search.SELECTED.read_text())
    if live_matches:
        subprocess.run([sys.executable, "-B", str(source), "--submission", str(search.OUTPUT / "passing_witness.json"),
                        "--output", str(search.OUTPUT / "live_evaluator_result.json")],
                       check=True, capture_output=True, text=True)
        assert json.loads((search.OUTPUT / "live_evaluator_result.json").read_text())["passed"]
    report = {"completed_at_utc": datetime.now(timezone.utc).isoformat(), "passed": True, "solvability": "demonstrated",
              "core_score": official["core_score"], "worst_family_score": official["worst_family_score"],
              "margins": search.margins(official), "scenario_count": len(scenarios),
              "maximum_calibration_error": max(family["max_abs_error"] for scenario in scenarios for family in scenario["calibration"].values()),
              "maximum_family_rms_error": max(family["rms_error"] for scenario in scenarios for family in scenario["calibration"].values()),
              "maximum_final_leakage": max(scenario["final_leakage"] for scenario in scenarios),
              "same_circuit_as_champion": witness["circuit"] == json.loads((search.ROOT / "champions/generation_1/witness.json").read_text())["circuit"],
              "search_method": "Two champion-seeded constrained continuous parameter optimizations; no circuit optimization was needed.",
              "optimizer_worker_seconds": [record["seconds"] for record in finals],
              "simulation_batch_calls": sum(record["batch_calls"] for record in finals),
              "circuit_scenario_evaluations": sum(record["circuit_scenario_evaluations"] for record in finals),
              "actual_selected_specification_sha256": hashes["specification.json"],
              "actual_selected_phase_radius": specification.get("independent_phase_radius"),
              "provisional_and_actual_physical_scenarios_identical": True,
              "exact_evaluator_source_sha256": source_hash, "exact_evaluator_source_byte_identical": True,
              "exact_evaluator_instantiated_with_actual_selected_specification": True,
              "live_root_evaluator_already_matches_selected_specification": live_matches,
              "evaluator_runtime_seconds": official["runtime_seconds"],
              "active_fresh_outputs_inspected": False, "participant_evaluator_status_edited": False,
              "witness": "adversary/robust_champion_search/passing_witness.json",
              "evaluation": "adversary/robust_champion_search/selected_evaluator_result.json"}
    search.save("proof_report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
