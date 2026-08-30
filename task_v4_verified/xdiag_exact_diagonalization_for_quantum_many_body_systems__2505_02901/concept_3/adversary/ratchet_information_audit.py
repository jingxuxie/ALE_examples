import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
GENERATION = ROOT / "generations/generation_1"
sys.path.insert(0, str(ROOT / "participant/workspace"))
sys.path.insert(0, str(ROOT / "adversary/portfolio"))
from physics import LOWER, UPPER, STATES
from derivatives import predict_with_jac


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=GENERATION)
    parser.add_argument("--queries", type=int)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    random = np.random.default_rng(965531)
    config = json.loads((arguments.package / "participant/input/config.json").read_text())
    cases = json.loads((arguments.package / "evaluator/hidden/devices.json").read_text())
    if arguments.queries:
        total_shots = config["shots"] * config["query_budget"]
        assert total_shots % arguments.queries == 0
        config.update(query_budget=arguments.queries, shots=total_shots // arguments.queries)
    candidates = [{"type": "query", "preparation": int(random.choice(STATES)), "time": float(random.uniform(0.5, 5.8)), "phases": random.uniform(-np.pi, np.pi, 6).tolist()} for index in range(160)]
    results = []
    for case in cases:
        normalized = (np.asarray(case["parameters"]) - LOWER) / (UPPER - LOWER)
        predictions, jacobians = predict_with_jac(normalized, candidates)
        matrices = config["shots"] * np.einsum("qap,qak,qa->qpk", jacobians, jacobians, 1 / np.maximum(predictions, 1e-14))
        information = 1e-7 * np.eye(20)
        selected = []
        for query in range(config["query_budget"]):
            risks = np.trace(np.linalg.inv(information[None, :, :] + matrices), axis1=1, axis2=2)
            if selected:
                risks[selected] = np.inf
            choice = int(np.argmin(risks))
            selected.append(choice)
            information += matrices[choice]
        for sweep in range(2):
            for position in range(len(selected)):
                base = information - matrices[selected[position]]
                risks = np.trace(np.linalg.inv(base[None, :, :] + matrices), axis1=1, axis2=2)
                other = [choice for slot, choice in enumerate(selected) if slot != position]
                risks[other] = np.inf
                choice = int(np.argmin(risks))
                selected[position] = choice
                information = base + matrices[choice]
        bound = float(np.sqrt(np.trace(np.linalg.inv(information)) / 20))
        results.append({"id": case["id"], "family": case["family"], "local_normalized_rmse_bound": bound, "selected_probes": [candidates[index] for index in selected]})
    report = {"mean_oracle_local_bound": float(np.mean([result["local_normalized_rmse_bound"] for result in results])), "max_oracle_local_bound": max(result["local_normalized_rmse_bound"] for result in results), "target_rmse": 0.03, "devices": results, "note": "This privileged parameter-aware Fisher audit supports statistical plausibility only. It is neither a feasible controller nor evidence of global identifiability or demonstrated solvability."}
    output = arguments.output or arguments.package / "adversary/information_audit.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "devices"}))


if __name__ == "__main__":
    main()
