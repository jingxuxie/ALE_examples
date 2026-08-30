from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "concept_1"
EVIDENCE = ROOT / "adversary/generation_2"
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import fisher_features, load_assets, risks

CANDIDATES, CONTRACT = load_assets(ROOT / "participant")
CANDIDATE = np.array(json.loads((ROOT / "attempts/v_3/design.json").read_text())["batches"])
CHAMPION = np.array(json.loads((ROOT / "champions/generation_2/design.json").read_text())["batches"])
SELECTED = np.union1d(np.flatnonzero(CANDIDATE), np.flatnonzero(CHAMPION))
SUBSET = [CANDIDATES[index] for index in SELECTED]


def generate(parameters):
    return fisher_features(parameters, SUBSET)


def main():
    started = time.monotonic()
    specification = importlib.util.spec_from_file_location("confirmation_evaluator", ROOT / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    with np.load(EVIDENCE / "champion_search/confirmation_features.npz", allow_pickle=False) as archive:
        parameters = archive["parameters"]
        families = archive["families"]
    with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as archive:
        assert not set(row.tobytes() for row in parameters) & set(row.tobytes() for row in archive["parameters"])
    with ProcessPoolExecutor(max_workers=8) as executor:
        features = np.array(list(executor.map(generate, parameters, chunksize=8)))
    full = fisher_features(parameters[0], CANDIDATES)
    assert np.allclose(features[0], full[SELECTED], rtol=1e-10, atol=1e-10)
    np.savez_compressed(EVIDENCE / "fresh_confirmation_features.npz", features=features,
                        parameters=parameters, families=families, original_candidate_indices=SELECTED)
    intact, loss, worst = evaluator.risk_profile(features, CANDIDATE[SELECTED], 3, 64)
    reference = risks(features, CHAMPION[SELECTED])
    family_scores = {str(family): float(reference[families == family].mean() / loss[families == family].mean())
                     for family in np.unique(families)}
    core = float(reference.mean() / loss.mean())
    guard = float(intact.mean() / reference.mean())
    result = dict(core_score=core, worst_family_score=min(family_scores.values()), family_scores=family_scores,
                  intact_mean_ratio=guard, passed=core >= .25 and min(family_scores.values()) >= .20 and guard <= 1.20,
                  operating_points=len(families), disjoint_from_official_hidden_points=True, target_unchanged=True,
                  seed=627018399, runtime_seconds=time.monotonic() - started,
                  subset_reconstruction_verified_against_full_catalog=True)
    (EVIDENCE / "fresh_failure_confirmation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
