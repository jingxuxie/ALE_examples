import argparse
import copy
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))
from physics import load_model, weight_batch
from evaluate import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion", required=True)
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--target-beta", type=float, required=True)
    parser.add_argument("--private-witness", required=True)
    arguments = parser.parse_args()
    model = load_model()
    champion_path = Path(arguments.champion)
    fields = json.loads(champion_path.read_text())["fields"]
    records = []
    for beta in np.linspace(0.65, 1.6, 96):
        for chemical in np.linspace(0.6, 1.4, 17):
            candidate_model = copy.deepcopy(model)
            candidate_model["beta"] = float(beta)
            candidate_model["chemical_potential"] = float(chemical)
            signs, logabs = weight_batch(fields, candidate_model)
            records.append({"beta": float(beta), "chemical_potential": float(chemical),
                            "sign": int(signs[0]), "logabs_weight": float(logabs[0])})
    candidate_model = copy.deepcopy(model)
    candidate_model["beta"] = arguments.target_beta
    output = ROOT / "adversary" / f"generation_{arguments.generation}"
    output.mkdir(exist_ok=True)
    champion_report = evaluate(champion_path, candidate_model)
    private_payload = json.loads(Path(arguments.private_witness).read_text())
    private_path = output / "privileged_witness.json"
    private_path.write_text(json.dumps({"fields": private_payload["fields"]}) + "\n")
    private_report = evaluate(private_path, candidate_model)
    (output / "champion_at_target.json").write_text(json.dumps(champion_report, indent=2) + "\n")
    (output / "privileged_at_target.json").write_text(json.dumps(private_report, indent=2) + "\n")
    report = {
        "cases": len(records), "champion_negative_cases": sum(row["sign"] == -1 for row in records),
        "champion_failed_cases": sum(row["sign"] != -1 for row in records),
        "target_beta": arguments.target_beta, "champion_passes_new_target": champion_report["passed"],
        "privileged_passes_new_target": private_report["passed"],
        "root_cause_clusters": [{"name": "loss_of_sign_at_shorter_imaginary_time", "scientific_interpretation": "A correlated field pattern that produces negative fermionic exchange weight at a longer projection length becomes positive as imaginary-time propagation shortens. The new generation demands a rarer pattern at a fixed shorter beta, while keeping lattice, interaction, doping, time slices and certification rigor unchanged."}],
        "records": records,
    }
    (output / "challenge_sweep.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}), flush=True)


if __name__ == "__main__":
    main()
