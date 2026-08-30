import itertools
import json
import time

import numpy as np
from scipy.optimize import minimize

from physics import HERE, ROOT, CALIBRATION_SCALE, CHECKER, champion, confirm, error_derivatives, fast, static_row


def main():
    started = time.monotonic()
    controls = champion()
    generator = np.random.default_rng(8292002)
    prior = json.loads((ROOT / "champions" / "generation_2" / "field_scan_validation.json").read_text())
    worst_rows = np.asarray([static_row(entry["worst_scenario"]) for entry in prior["calibrations"]])
    frozen = json.loads((ROOT / "evaluator" / "hidden" / "scenarios.json").read_text())["scenarios"]
    static_rows = np.asarray([static_row(row) for row in frozen] + list(worst_rows))
    random_old = generator.choice([-1, 1], size=(256, 15)) * CALIBRATION_SCALE
    random_drift = generator.choice([-0.01, 0.01], size=(256, 12))
    interior = (2 * generator.beta(0.35, 0.35, (256, 27)) - 1) * np.r_[CALIBRATION_SCALE, np.full(12, 0.01)]
    static_rows = np.r_[static_rows, np.c_[random_old, random_drift, random_drift],
                        np.c_[interior, interior[:, 15:]]]
    static_scores, _ = fast(controls, static_rows)
    np.savez_compressed(HERE / "static_recheck.npz", scenarios=static_rows, fidelities=static_scores)
    static_checked = [confirm(controls, static_rows[index], static_scores[index], "static_recheck")
                      for index in np.argsort(static_scores)[:8]]
    static_report = {"cases": len(static_rows), "new_random_cases": 512,
                     "minimum": float(static_scores.min()), "below_095": int(np.sum(static_scores < 0.95)),
                     "confirmed": static_checked, "seconds": time.monotonic() - started}
    (HERE / "static_recheck_report.json").write_text(json.dumps(static_report, indent=2) + "\n")
    print(json.dumps({"static_recheck": {key: value for key, value in static_report.items() if key != "confirmed"}}), flush=True)
    patterns = {"uniform": np.ones(12), "staggered": (-1.0) ** np.arange(12),
                "half_ring": np.r_[np.ones(6), -np.ones(6)],
                "control_groups": 1 - 2 * np.asarray(CHECKER.GROUPS),
                "old_worst_spatial": worst_rows[0, 15:27] / 0.01,
                "single_site": np.eye(12)[0]}
    bases = [np.zeros(15)] + [np.r_[np.asarray(signs) * CALIBRATION_SCALE[:3], np.full(12, signs[2] * 0.005)]
                              for signs in itertools.product((-1, 1), repeat=3)]
    rows = []
    labels = []
    for base_index, old in enumerate(bases):
        for name, pattern in patterns.items():
            for even, odd in itertools.product((-1, -0.5, 0, 0.5, 1), repeat=2):
                rows.append(np.r_[old, 0.01 * even * pattern, 0.01 * odd * pattern])
                labels.append({"family": "amplitude_plane", "old_base": base_index,
                               "pattern": name, "even": even, "odd": odd})
        for first_name, second_name in itertools.product(patterns, repeat=2):
            if first_name == second_name:
                continue
            for sign in (-1, 1):
                rows.append(np.r_[old, 0.01 * patterns[first_name], sign * 0.01 * patterns[second_name]])
                labels.append({"family": "different_spatial_patterns", "old_base": base_index,
                               "even_pattern": first_name, "odd_pattern": second_name, "relative_sign": sign})
    for index in range(1024):
        if index < 512:
            row = np.r_[generator.choice([-1, 1], 15) * CALIBRATION_SCALE,
                        generator.choice([-0.01, 0.01], 24)]
        else:
            row = (2 * generator.beta(0.35, 0.35, 39) - 1) * np.r_[CALIBRATION_SCALE, np.full(24, 0.01)]
        rows.append(row)
        labels.append({"family": "random_vertices" if index < 512 else "random_near_boundary"})
    rows = np.asarray(rows)
    scores, _ = fast(controls, rows)
    np.savez_compressed(HERE / "matching_broad.npz", scenarios=rows, fidelities=scores)
    (HERE / "matching_labels.json").write_text(json.dumps(labels, indent=2) + "\n")
    selected = set(np.argsort(scores)[:12].tolist())
    families = {}
    for family in sorted({label["family"] for label in labels}):
        indices = [index for index, label in enumerate(labels) if label["family"] == family]
        worst = min(indices, key=lambda index: scores[index])
        selected.add(worst)
        families[family] = {"cases": len(indices), "minimum": float(scores[worst]),
                            "below_095": int(np.sum(scores[indices] < 0.95))}
    checked = [confirm(controls, rows[index], scores[index], labels[index])
               for index in sorted(selected, key=lambda index: scores[index])]
    report = {"model": "PROPOSED_MATCHING_DEPENDENT_EXTENSION", "cases": len(rows),
              "minimum": float(scores.min()), "families": families, "confirmed": checked,
              "seconds": time.monotonic() - started}
    (HERE / "matching_broad_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"matching_broad": families, "minimum": report["minimum"], "seconds": report["seconds"]}), flush=True)
    scale = np.r_[CALIBRATION_SCALE, np.full(24, 0.01)]
    seeds = [*rows[np.argsort(scores)[:12]], *worst_rows,
             *(generator.uniform(-1, 1, (36, 39)) * scale)]
    records = []
    best_rows = []
    for restart, seed in enumerate(seeds):
        def objective(normalized):
            value, derivative = error_derivatives(controls, [normalized * scale])
            return float(value[0]), derivative[0] * scale
        result = minimize(objective, seed / scale, jac=True, method="L-BFGS-B",
                          bounds=[(-1.0, 1.0)] * 39,
                          options={"maxiter": 80, "ftol": 1e-12, "gtol": 1e-8})
        row = np.clip(result.x, -1, 1) * scale
        score = float(fast(controls, [row])[0][0])
        records.append({"restart": restart, "minimum": score, "iterations": int(result.nit),
                        "evaluations": int(result.nfev)})
        best_rows.append(row)
        if (restart + 1) % 8 == 0:
            np.savez_compressed(HERE / "continuous_candidates.npz", scenarios=np.asarray(best_rows),
                                fidelities=np.asarray([record["minimum"] for record in records]))
            (HERE / "continuous_progress.json").write_text(json.dumps(records, indent=2) + "\n")
            print(json.dumps({"continuous_restarts": restart + 1,
                              "minimum": min(record["minimum"] for record in records),
                              "seconds": time.monotonic() - started}), flush=True)
    values = np.asarray([record["minimum"] for record in records])
    best_rows = np.asarray(best_rows)
    np.savez_compressed(HERE / "continuous_candidates.npz", scenarios=best_rows, fidelities=values)
    confirmed = [confirm(controls, best_rows[index], values[index], "continuous_worst_case")
                 for index in np.argsort(values)[:12]]
    final = {"restarts": len(seeds), "minimum": float(values.min()),
             "below_095": int(np.sum(values < 0.95)), "confirmed": confirmed,
             "optimizer_records": records, "seconds": time.monotonic() - started,
             "not_a_continuum_certificate": True}
    (HERE / "continuous_report.json").write_text(json.dumps(final, indent=2) + "\n")
    print(json.dumps({"continuous_complete": len(seeds), "minimum": final["minimum"], "seconds": final["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
