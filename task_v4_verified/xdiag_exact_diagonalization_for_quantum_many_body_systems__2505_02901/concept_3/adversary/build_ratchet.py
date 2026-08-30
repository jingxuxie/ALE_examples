from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import LOWER, UPPER, STATES, probabilities


def main():
    destination = ROOT / "generations/generation_1"
    if destination.exists():
        raise RuntimeError("ratchet already exists; do not overwrite a frozen generation")
    for directory in ("evaluator/hidden", "adversary", "attempts", "champions"):
        (destination / directory).mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "participant", destination / "participant", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("evaluate.py", "validate.py"):
        shutil.copy2(ROOT / "evaluator" / name, destination / "evaluator" / name)
    shutil.copy2(ROOT / "evaluator/hidden/device_model.py", destination / "evaluator/hidden/device_model.py")
    shutil.copy2(ROOT / "champions/generation_1/solve.py", destination / "participant/baseline/solve.py")
    config_path = destination / "participant/input/config.json"
    config = json.loads(config_path.read_text())
    config.update(query_budget=3, shots=12288)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    task = destination / "participant/TASK.md"
    description = task.read_text().replace("a runnable weak\n+controller", "the current-champion\n+controller")
    description = description.replace("a runnable weak", "the current-champion").replace("18 experiments of 2,048 shots", "3 experiments of 12,288 shots")
    description = description.replace("across disorder regimes.", "across mixed-sign field-disorder regimes. Configuration changes are expensive;\n+the total shot budget remains 36,864.")
    task.write_text(description.replace("\n+", "\n"))
    protocol = destination / "participant/input/protocol.md"
    description = protocol.read_text().replace('"remaining":17', '"remaining":2')
    description = description.replace("The hidden suite covers smooth\n+near-uniform exchange, frustrated exchange, and strong field disorder, within\n+the same public parameter box.", "The hidden suite covers mixed-sign field disorder, weak exchange with mixed\n+fields, and frustrated mixed fields, within the same public parameter box.")
    description = description.replace("The hidden suite covers smooth\nnear-uniform exchange, frustrated exchange, and strong field disorder, within\nthe same public parameter box.", "The hidden suite covers mixed-sign field disorder, weak exchange with mixed\nfields, and frustrated mixed fields, within the same public parameter box.")
    protocol.write_text(description.replace("\n+", "\n"))
    random = np.random.default_rng(705531891)
    cases = []
    examples = []
    families = ("mixed_sign_disorder", "weak_exchange_mixed", "frustrated_mixed")
    for family in families:
        for index in range(7):
            parameters = LOWER + (UPPER - LOWER) * random.uniform(0.08, 0.92, 20)
            signs = random.choice([-1, 1], 5)
            if np.all(signs == signs[0]):
                signs[0] *= -1
            parameters[6:11] = signs * random.uniform(0.25, 0.49, 5)
            if family == "mixed_sign_disorder":
                parameters[:6] = random.uniform(0.6, 1.2, 6)
                parameters[11] = random.uniform(0.45, 1.5)
                parameters[12:14] = random.uniform(0.07, 0.4, 2)
            elif family == "weak_exchange_mixed":
                parameters[:6] = random.uniform(0.55, 0.8, 6)
                parameters[11] = random.uniform(0.3, 0.9)
                parameters[12:14] = random.uniform(0.05, 0.16, 2)
            else:
                parameters[:6] = random.uniform(0.55, 0.9, 6)
                parameters[11] = random.uniform(1.2, 1.7)
                parameters[12:14] = random.uniform(0.4, 0.5, 2)
            parameters[14:20] = random.uniform(0.008, 0.05, 6)
            assert np.all(parameters >= LOWER) and np.all(parameters <= UPPER)
            if index == 0:
                experiment = {"type": "query", "preparation": int(STATES[7]), "time": 1.2, "phases": [0.3, 0.1, -0.2, 0.4, -0.1, 0.0]}
                examples.append({"family": family, "parameters": parameters.tolist(), "experiment": experiment, "probabilities": probabilities(parameters, experiment).tolist()})
            else:
                cases.append({"id": f"device-{int(random.integers(10000000, 99999999))}", "family": family, "parameters": parameters.tolist(), "noise_seed": int(random.integers(2**31))})
    (destination / "evaluator/hidden/devices.json").write_text(json.dumps(cases, indent=2) + "\n")
    (destination / "participant/input/development.json").write_text(json.dumps(examples, indent=2) + "\n")
    audit = json.loads((ROOT / "adversary/champion_stress_resource_audit.json").read_text())["budgets"]["3"]
    clusters = {}
    original_cases = json.loads((ROOT / "adversary/stress_devices.json").read_text())
    index = {case["id"]: case for case in original_cases}
    for result in audit["devices"]:
        cluster = index[result["id"]]["parameter_cluster"]
        clusters.setdefault(cluster, []).append(result["normalized_rmse"])
    cluster_report = [{"cluster": name, "mean_error": float(np.mean(errors)), "noise_repetition_errors": errors} for name, errors in clusters.items()]
    cluster_report.sort(key=lambda value: value["mean_error"], reverse=True)
    provenance = {"created_at": datetime.now(timezone.utc).isoformat(), "parent_generation": 0, "champion_source": "attempts/v_2/solve.py", "champion_sha256": hashlib.sha256((ROOT / "champions/generation_1/solve.py").read_bytes()).hexdigest(), "counterexample_audit": "../../adversary/champion_stress_resource_audit.json", "original_target_not_regraded": True, "original_queries": 18, "new_queries": 3, "original_shots_per_query": 2048, "new_shots_per_query": 12288, "unchanged_total_shots": 36864, "root_cause": "Configuration-limited inference becomes poorly conditioned or multimodal for mixed-sign fields. The incumbent passes the original task and broad original-budget stress tests but misses the fixed core target in the compressed-budget stress suite.", "counterexample_core_score": audit["core_score"], "counterexample_worst_family_score": audit["worst_family_score"], "parameter_clusters": cluster_report, "new_devices_are_fresh_draws": True}
    (destination / "adversary/ratchet_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    status = {"name": "Configuration-limited interacting-spin spectroscopy", "verification_mode": "E", "status": "built", "generation": 1, "ratchet_generations": 1, "target": {"core_score": 0.970, "worst_family_score": 0.950}, "solvability": "unknown", "query_budget": 3, "shots": 12288, "hidden_devices": len(cases)}
    (destination / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"generation": str(destination), "hidden_devices": len(cases), "target": status["target"], "query_budget": 3, "total_shots": 36864}))


if __name__ == "__main__":
    main()
