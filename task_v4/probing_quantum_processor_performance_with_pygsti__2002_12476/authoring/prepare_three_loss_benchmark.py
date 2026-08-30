from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "concept_1"
DESTINATION = ROOT / "adversary/generation_2"
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import FAMILIES, fisher_features, load_assets, sample_parameters

SPECIFICATION = importlib.util.spec_from_file_location("three_loss_evaluator", ROOT / "evaluator/evaluate.py")
EVALUATOR = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(EVALUATOR)
CANDIDATES, CONTRACT = load_assets(ROOT / "participant")
BATCHES = np.array(json.loads((ROOT / "champions/generation_2/design.json").read_text())["batches"])


def one_model(parameters):
    features = fisher_features(parameters, CANDIDATES)
    intact, loss, sets = EVALUATOR.risk_profile(features[None], BATCHES, 3, 64)
    return features, intact[0], loss[0], sets[0]


def main():
    started = time.monotonic()
    destination = DESTINATION / "candidate_benchmark.npz"
    if destination.exists():
        raise ValueError("independent benchmark already generated")
    seed = 83170246915
    generator = np.random.default_rng(seed)
    families = np.repeat(FAMILIES, 100)
    parameters = np.array([sample_parameters(generator, str(family)) for family in families])
    with ProcessPoolExecutor(max_workers=12) as executor:
        outputs = list(executor.map(one_model, parameters, chunksize=4))
    with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as old:
        data = {key: old[key] for key in ("costs", "nominal_features")}
    data.update(features=np.array([row[0] for row in outputs]), parameters=parameters, families=families,
                champion_intact_risks=np.array([row[1] for row in outputs]),
                champion_loss_risks=np.array([row[2] for row in outputs]))
    data["baseline_risks"] = data["champion_intact_risks"]
    np.savez_compressed(destination, **data)
    report = dict(seed=seed, models=len(families), per_family=100,
                  independent_of_prior_private_and_fresh_draws=True,
                  public_forward_model_unchanged=True, loss_count=3,
                  mean_intact_risk=float(data["champion_intact_risks"].mean()),
                  mean_loss_risk=float(data["champion_loss_risks"].mean()),
                  worst_lost_sets=[row[3] for row in outputs],
                  runtime_seconds=time.monotonic() - started)
    report["families"] = {str(family): dict(
        intact_mean=float(data["champion_intact_risks"][families == family].mean()),
        loss_mean=float(data["champion_loss_risks"][families == family].mean())) for family in FAMILIES}
    (DESTINATION / "candidate_benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "worst_lost_sets"}, indent=2))


if __name__ == "__main__":
    main()
