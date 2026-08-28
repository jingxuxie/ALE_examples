import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "private"
specification = importlib.util.spec_from_file_location("mps_evaluator", PRIVATE / "evaluator.py")
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)


def main():
    manifest = json.loads((PRIVATE / "challenge_pool" / "manifest.json").read_text())
    small = json.loads((PRIVATE / "reference" / "validation" / "small_exact.json").read_text())
    records = []
    for split, entries in manifest["splits"].items():
        for entry in entries:
            source = PRIVATE / entry["reference"]
            if not source.exists():
                records.append({"id": entry["id"], "split": split, "passed": False, "reason": "missing_reference"})
                continue
            artifact = json.loads(source.read_text())
            if not artifact.get("ready"):
                records.append({"id": entry["id"], "split": split, "passed": False, "reason": "unconverged_reference"})
                continue
            case = json.loads((PRIVATE / entry["input"]).read_text())
            reference, weak = artifact["reference"], artifact["weak"]
            strong_score, components = evaluator.score_output(case, reference, weak, reference)
            weak_score, _ = evaluator.score_output(case, reference, weak, weak)
            energy_only, _ = evaluator.score_output(case, reference, weak, {"energy": reference["energy"]})
            zero_correlations, _ = evaluator.score_output(case, reference, weak, {"energy": reference["energy"], "gap": reference["gap"], "correlations": [0.0] * len(reference["correlations"])})
            invalid_score, _ = evaluator.score_output(case, reference, weak, {"energy": float("nan"), "gap": True, "correlations": [float("inf")] * len(reference["correlations"])})
            final_sectors = artifact["convergence"]["history"][-1]["sectors"]
            largest_norm_error = max(sector["norm_error"] for sector in final_sectors)
            last_energy_changes = [abs(sector["last_sweep_energies"][-1] - sector["last_sweep_energies"][-2]) / case["length"] for sector in final_sectors]
            digest = hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()
            passed = strong_score > 0.999999 and weak_score < 0.15 and energy_only <= 0.20000001 and invalid_score == 0.0 and largest_norm_error < 1e-7 and max(last_energy_changes) < 1e-7 and digest == artifact["input_sha256"]
            records.append({
                "id": entry["id"], "split": split, "passed": passed,
                "strong_score": strong_score, "weak_score": weak_score,
                "perfect_energy_only_score": energy_only,
                "perfect_energy_and_gap_zero_correlations_score": zero_correlations,
                "invalid_output_score": invalid_score,
                "reference_chi": artifact["convergence"]["history"][-1]["chi"],
                "convergence": artifact["convergence"]["last_difference"],
                "norm_error": largest_norm_error, "last_energy_changes_per_site": last_energy_changes,
                "component_scales": {name: value["scale"] for name, value in components.items()},
                "generation_seconds": artifact["generation_seconds"],
            })
    result = {"passed": small["passed"] and all(record["passed"] for record in records), "small_exact_passed": small["passed"], "cases": records}
    destination = PRIVATE / "reference" / "validation" / "artifact_audit.json"
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
