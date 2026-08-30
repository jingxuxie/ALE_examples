import itertools
import json

import numpy as np

from physics import HERE, ROOT, OLD_SCALE, champion, exact, fast, row_to_scenario


def main():
    bound = 0.005
    records = []
    rows = []
    def add(family, row):
        rows.append(np.asarray(row))
        records.append({"name": f"{family}_{sum(record['family'] == family for record in records)}",
                        "family": family, **row_to_scenario(np.asarray(row))})
    original = json.loads((ROOT / "evaluator" / "hidden" / "scenarios.json").read_text())["scenarios"]
    for scenario in original:
        add("original_zero_drift", np.r_[scenario["gain_a"], scenario["gain_b"], scenario["zz_common"],
                                        scenario["zz_local"], np.zeros(12)])
    patterns = [np.ones(12), (-1.0) ** np.arange(12), np.r_[np.ones(6), -np.ones(6)],
                1 - 2 * np.asarray([0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0])]
    for pattern in patterns + [np.eye(12)[site] for site in (0, 3, 6, 9)]:
        for sign in (-1, 1):
            add("nominal_drift_core", np.r_[np.zeros(15), sign * bound * pattern])
    for signs in itertools.product((-1, 1), repeat=3):
        old = np.r_[np.asarray(signs) * OLD_SCALE[:3], np.full(12, signs[2] * 0.005)]
        for pattern in patterns:
            for sign in (-1, 1):
                add("coherent_joint_stress", np.r_[old, sign * bound * pattern])
    boundary = np.load(HERE / "boundary_drift_cases.npz", allow_pickle=False)
    for index in np.argsort(boundary["fidelities"])[:16]:
        row = boundary["scenarios"][index].copy()
        row[15:] *= 0.5
        add("champion_counterexamples", row)
    generator = np.random.default_rng(5272887)
    for first, last in ((4864, 5376), (5376, 5888)):
        for index in generator.choice(np.arange(first, last), 32, replace=False):
            row = boundary["scenarios"][index].copy()
            row[15:] *= 0.5
            add("local_disorder_samples", row)
    rows = np.asarray(rows)
    assert len(rows) == 223
    assert np.all(np.abs(rows[:, :15]) <= OLD_SCALE + 1e-15)
    assert np.max(np.abs(rows[:, 15:])) <= bound + 1e-15
    payload = {"proposal_only_not_frozen": True, "threshold": 0.95,
               "operation": "D_l then K_l then product_v exp(-i delta_v Z_v/2)",
               "drift_bound_radians_per_site_per_layer": bound,
               "scenarios": records}
    (HERE / "proposed_suite.json").write_text(json.dumps(payload, indent=2) + "\n")
    candidates = {"fresh_generation_1": champion(),
                  "private_refocused": np.asarray(json.loads((HERE / "drift_0005_validated_candidate.json").read_text())["angles"])}
    report = {"proposal_only_not_frozen": True, "threshold": 0.95, "scenario_count": len(rows)}
    for name, angles in candidates.items():
        scores, _ = fast(angles, rows)
        worst = int(np.argmin(scores))
        checked = exact(angles, rows[worst])
        assert abs(checked["fidelity"] - scores[worst]) < 1e-10
        report[name] = {"minimum": float(scores.min()), "below_095": int(np.sum(scores < 0.95)),
                        "independent_worst": checked, "worst_case": records[worst],
                        "family_minima": {family: float(min(scores[index] for index, record in enumerate(records)
                                                             if record["family"] == family))
                                          for family in sorted({record["family"] for record in records})}}
    (HERE / "proposed_suite_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
