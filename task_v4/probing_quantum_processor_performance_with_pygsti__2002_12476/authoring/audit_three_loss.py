import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "concept_1"
DESTINATION = ROOT / "adversary/generation_2"


def main():
    specification = importlib.util.spec_from_file_location("dense_risk", ROOT / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    batches = np.array(json.loads((ROOT / "champions/generation_2/design.json").read_text())["batches"])
    active = np.flatnonzero(batches)
    cases = np.array(list(itertools.combinations(range(len(active)), 3)))
    with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as archive:
        features = archive["features"][:6]
    intact, dense_loss, lost = evaluator.risk_profile(features, batches, 3, 64)
    independent = []
    for model in features:
        rows = model[active] * np.sqrt(batches[active, None] * 64)
        covariance = np.linalg.inv(rows.T @ rows + 1e-10 * np.eye(14))
        information_fraction = rows @ covariance @ rows.T
        risk_gram = rows @ covariance[:, :12] @ covariance[:12, :] @ rows.T
        local_fraction = information_fraction[cases[:, :, None], cases[:, None, :]]
        local_gram = risk_gram[cases[:, :, None], cases[:, None, :]]
        correction = np.linalg.solve(np.eye(3)[None] - local_fraction, local_gram)
        risks = np.trace(covariance[:12, :12]) + np.trace(correction, axis1=1, axis2=2)
        independent.append(float(risks.max()))
    error = float(np.max(abs(dense_loss - independent) / dense_loss))
    assert error < 1e-6, error
    assert np.all(dense_loss >= intact)
    assert all(len(case) == 3 for case in lost)
    degenerate = np.zeros_like(batches)
    degenerate[active[:2]] = 1
    _, empty_loss, empty_sets = evaluator.risk_profile(features[:1], degenerate, 3, 64)
    assert np.allclose(empty_loss, 12 / 1e-10, rtol=1e-12)
    assert len(empty_sets[0]) == 2
    report = dict(passed=True, removal_count=3, cases_per_model=len(cases), models=len(features),
                  independent_rank_three_relative_error=error, dense_loss=dense_loss.tolist(),
                  intact=intact.tolist(), fewer_than_three_loses_all=True,
                  monotonicity_justification="Removing positive-semidefinite information cannot reduce regularized A-risk; enumerating exactly min(k, support_size) therefore covers the worst case for up to k losses.",
                  target_not_yet_selected=True)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    (DESTINATION / "three_loss_numerical_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("dense_loss", "intact")}, indent=2))


if __name__ == "__main__":
    main()
