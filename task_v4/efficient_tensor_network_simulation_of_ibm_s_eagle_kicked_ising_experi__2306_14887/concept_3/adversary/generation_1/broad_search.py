import itertools
import json
import time

import numpy as np

from physics import HERE, ROOT, OLD_SCALE, CHECKER, admissibility, champion, exact, fast, row_to_scenario


def confirm(angles, row, score, family, drift_bound):
    trusted = exact(angles, row)
    assert abs(trusted["fidelity"] - score) < 1e-10
    assert trusted["norm_error"] < 1e-10
    return {"family": family, "scenario": row_to_scenario(row),
            "compiled_fidelity": float(score), "independent": trusted,
            "admissibility": admissibility(row, drift_bound),
            "proposed_drift_bound": drift_bound,
            "below_095": trusted["fidelity"] < 0.95}


def main():
    started = time.monotonic()
    generator = np.random.default_rng(2026082801)
    angles = champion()
    prior_worst = np.load(ROOT / "champions" / "generation_1" / "worst_errors.npy", allow_pickle=False)
    common_corners = np.asarray([np.r_[np.asarray(signs) * OLD_SCALE[:3], np.zeros(12)]
                                 for signs in itertools.product((-1, 1), repeat=3)])
    old_rows = np.r_[prior_worst[:32], common_corners,
                     generator.uniform(-1, 1, (384, 15)) * OLD_SCALE,
                     (2 * generator.beta(0.35, 0.35, (640, 15)) - 1) * OLD_SCALE]
    old_rows = np.c_[old_rows, np.zeros((len(old_rows), 12))]
    old_scores, _ = fast(angles, old_rows)
    old_order = np.argsort(old_scores)
    old_confirmed = [confirm(angles, old_rows[index], old_scores[index], "original_box", 0.0)
                     for index in old_order[:12]]
    for index in old_order[:12]:
        state = CHECKER.evolve(angles, row_to_scenario(old_rows[index]))
        original_score = abs((state[0] + state[-1]) / np.sqrt(2)) ** 2
        assert abs(original_score - old_scores[index]) < 1e-10
    old_report = {"new_independent_full_state_cases": len(old_rows),
                  "new_nonvertex_random_cases": 1024, "prior_worst_rechecks": len(prior_worst[:32]),
                  "minimum": float(old_scores.min()), "failures_below_095": int(np.sum(old_scores < 0.95)),
                  "seconds": time.monotonic() - started, "confirmed_lowest": old_confirmed,
                  "not_a_continuum_certificate": True}
    (HERE / "old_box_report.json").write_text(json.dumps(old_report, indent=2) + "\n")
    np.savez_compressed(HERE / "old_box_cases.npz", scenarios=old_rows, fidelities=old_scores)
    print(json.dumps({key: value for key, value in old_report.items() if key != "confirmed_lowest"}), flush=True)
    patterns = {"uniform": np.ones(12), "alternating": (-1.0) ** np.arange(12),
                "control_groups": 1 - 2 * np.asarray(CHECKER.GROUPS),
                "half_ring": np.r_[np.ones(6), -np.ones(6)]}
    for site in range(12):
        patterns[f"local_site_{site}"] = np.eye(12)[site]
    for frequency in range(1, 6):
        for phase_index in range(2):
            pattern = np.cos(2 * np.pi * frequency * np.arange(12) / 12 + phase_index * np.pi / 2)
            patterns[f"wave_{frequency}_{phase_index}"] = pattern / max(abs(pattern))
    old_bases = [np.zeros(15), prior_worst[0], *common_corners]
    amplitudes = (0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02)
    rows = []
    labels = []
    for amplitude in amplitudes:
        for base_index, base in enumerate(old_bases):
            for name, pattern in patterns.items():
                rows.append(np.r_[base, amplitude * pattern])
                labels.append({"amplitude": amplitude, "old_base": base_index, "pattern": name})
    rows = np.asarray(rows)
    scores, _ = fast(angles, rows)
    np.savez_compressed(HERE / "structured_drift_cases.npz", scenarios=rows, fidelities=scores)
    (HERE / "structured_labels.json").write_text(json.dumps(labels, indent=2) + "\n")
    selected = set(np.argsort(scores)[:12].tolist())
    summaries = []
    for amplitude in amplitudes:
        indices = [index for index, label in enumerate(labels) if label["amplitude"] == amplitude]
        worst = min(indices, key=lambda index: scores[index])
        selected.add(worst)
        summaries.append({"amplitude": amplitude, "case_count": len(indices),
                          "minimum": float(scores[worst]), "worst": labels[worst],
                          "below_095": int(np.sum(scores[indices] < 0.95))})
        for family in ("uniform", "alternating", "control_groups", "half_ring", "local_site_0"):
            family_indices = [index for index in indices if labels[index]["pattern"] == family]
            selected.add(min(family_indices, key=lambda index: scores[index]))
    confirmed = [confirm(angles, rows[index], scores[index], labels[index], labels[index]["amplitude"])
                 for index in sorted(selected, key=lambda index: scores[index])]
    report = {"model": "PROPOSED_EXTENSION_NOT_ORIGINAL_TASK", "operation": "After each original K_l D_l, apply product_v exp(-i delta_v Z_v/2); delta static across all 24 layers",
              "threshold_unchanged": 0.95, "case_count": len(rows), "amplitude_summaries": summaries,
              "independently_confirmed": confirmed, "elapsed_seconds": time.monotonic() - started}
    (HERE / "structured_drift_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"structured_summary": summaries, "seconds": time.monotonic() - started}), flush=True)


if __name__ == "__main__":
    main()
