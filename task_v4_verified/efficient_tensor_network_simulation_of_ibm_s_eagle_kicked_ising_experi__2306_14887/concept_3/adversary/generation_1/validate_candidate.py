import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from physics import HERE, ROOT, OLD_SCALE, champion, exact, fast, row_to_scenario


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pulses", type=Path, required=True)
    parser.add_argument("--amplitude", type=float, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    started = time.monotonic()
    raw = args.pulses.read_bytes()
    angles = np.asarray(json.loads(raw)["angles"])
    assert angles.shape == (24, 2) and np.max(np.abs(angles)) <= np.pi
    snapshot = HERE / (args.label + "_validated_candidate.json")
    snapshot.write_bytes(raw)
    original = json.loads((ROOT / "evaluator" / "hidden" / "scenarios.json").read_text())["scenarios"]
    original = np.asarray([[row["gain_a"], row["gain_b"], row["zz_common"], *row["zz_local"], *([0.0] * 12)] for row in original])
    old = np.load(HERE / "old_box_cases.npz", allow_pickle=False)["scenarios"]
    structured = np.load(HERE / "structured_drift_cases.npz", allow_pickle=False)["scenarios"]
    labels = json.loads((HERE / "structured_labels.json").read_text())
    structured = structured[[index for index, label in enumerate(labels) if label["amplitude"] == 0.01]].copy()
    structured[:, 15:] *= args.amplitude / 0.01
    boundary = np.load(HERE / "boundary_drift_cases.npz", allow_pickle=False)["scenarios"].copy()
    boundary[:, 15:] *= args.amplitude / 0.01
    family_rows = {"original_frozen_63": original, "original_box_1064": old,
                   "structured_drift_260": structured, "broad_joint_drift_5888": boundary}
    summary = {}
    confirmations = []
    for name, rows in family_rows.items():
        assert np.all(np.abs(rows[:, :15]) <= OLD_SCALE + 1e-15)
        assert np.max(np.abs(rows[:, 15:])) <= args.amplitude + 1e-15
        scores = []
        for first in range(0, len(rows), 256):
            batch, _ = fast(angles, rows[first:first + 256])
            scores.extend(batch.tolist())
        scores = np.asarray(scores)
        np.savez_compressed(HERE / (args.label + "_" + name + ".npz"), scenarios=rows, fidelities=scores)
        summary[name] = {"cases": len(rows), "minimum": float(scores.min()),
                         "mean": float(scores.mean()), "below_095": int(np.sum(scores < 0.95))}
        for index in np.argsort(scores)[:4]:
            independent = exact(angles, rows[index])
            assert abs(independent["fidelity"] - scores[index]) < 1e-10
            confirmations.append({"family": name, "compiled_fidelity": float(scores[index]),
                                  "independent": independent, "scenario": row_to_scenario(rows[index])})
        print(json.dumps({"candidate_family": name, **summary[name], "seconds": time.monotonic() - started}), flush=True)
    minimum = min(family["minimum"] for family in summary.values())
    report = {"private_candidate_sha256": hashlib.sha256(raw).hexdigest(), "drift_bound": args.amplitude,
              "threshold": 0.95, "minimum": minimum, "feasible_on_tested_suite": minimum >= 0.95,
              "families": summary, "independent_confirmations": confirmations,
              "case_evaluations": sum(family["cases"] for family in summary.values()),
              "seconds": time.monotonic() - started,
              "not_a_continuum_certificate": True, "original_task_unchanged": True}
    (HERE / (args.label + "_broad_validation.json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "independent_confirmations"}), flush=True)


if __name__ == "__main__":
    main()
