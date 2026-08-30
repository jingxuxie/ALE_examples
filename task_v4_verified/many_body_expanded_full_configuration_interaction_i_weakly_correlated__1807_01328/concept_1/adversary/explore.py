import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from pair_model import FAMILIES, increments


def features(table):
    terms = increments(table)
    second = sum(value for mask, value in enumerate(terms) if mask.bit_count() <= 2)
    third = sum(value for mask, value in enumerate(terms) if mask.bit_count() == 3)
    candidates = [mask for mask in range(256) if mask.bit_count() == 4]
    candidates.sort(key=lambda mask: -sum(abs(terms[mask ^ (1 << orbital)]) for orbital in range(8) if mask & (1 << orbital)))
    selected = sum(terms[mask] for mask in candidates[:26])
    unqueried_proxy = sum(sum(terms[mask ^ (1 << orbital)] for orbital in range(8) if mask & (1 << orbital)) for mask in candidates[26:])
    return np.array([second, third, selected, unqueried_proxy])


def main():
    public = np.load(ROOT / "participant/input/practice.npz")["energies"]
    hidden = np.load(ROOT / "evaluator/hidden/cases.npz")["energies"]
    coefficients = {}
    public_features = np.array([features(table) for table in public])
    hidden_features = np.array([features(table) for table in hidden])
    predictions = hidden_features[:, :3].sum(axis=1)
    for index, family in enumerate(FAMILIES):
        selected = np.arange(index, len(public), len(FAMILIES))
        training = public_features[selected]
        residual = public[selected, -1] - training[:, :2].sum(axis=1)
        design = training[:, 2:]
        penalty = 1e-3 * max(np.sum(design ** 2), 1e-12)
        weights = np.linalg.solve(design.T @ design + penalty * np.eye(2), design.T @ residual)
        coefficients[family] = weights.tolist()
        testing = np.arange(index, len(hidden), len(FAMILIES))
        predictions[testing] = hidden_features[testing, :2].sum(axis=1) + hidden_features[testing, 2:] @ weights
    errors = predictions - hidden[:, -1]
    family_rmse = {family: float(np.sqrt(np.mean(errors[index::len(FAMILIES)] ** 2))) for index, family in enumerate(FAMILIES)}
    report = {"train_count": len(public), "private_test_count": len(hidden),
              "search_kind": "public-trained family ridge residual correction; identical 160-unit acquisition",
              "rmse_hartree": float(np.sqrt(np.mean(errors ** 2))),
              "family_rmse_hartree": family_rmse,
              "passes": bool(np.sqrt(np.mean(errors ** 2)) <= 1e-5 and max(family_rmse.values()) <= 2.5e-5),
              "coefficients_fit_only_on_public_practice": coefficients}
    (ROOT / "adversary/public_fit_search.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
