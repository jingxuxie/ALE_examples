import itertools
import json
import time

import numpy as np

from physics import HERE, ROOT, OLD_SCALE, champion, exact, fast, row_to_scenario


def branches(angles, mask):
    controls = angles.copy()
    selected = np.asarray(mask, dtype=bool)
    controls[selected] = np.where(controls[selected] >= 0, controls[selected] - np.pi,
                                  controls[selected] + np.pi)
    return controls


def main():
    started = time.monotonic()
    generator = np.random.default_rng(82731)
    base = champion()
    prior_worst = np.load(ROOT / "champions" / "generation_1" / "worst_errors.npy", allow_pickle=False)[0]
    corners = [np.r_[np.asarray(signs) * OLD_SCALE[:3], np.full(12, signs[2] * 0.005)]
               for signs in itertools.product((-1, 1), repeat=3)]
    patterns = [np.ones(12), (-1.0) ** np.arange(12), np.r_[np.ones(6), -np.ones(6)],
                1 - 2 * np.asarray([0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0])]
    screening = np.asarray([np.r_[prior_worst, np.zeros(12)],
                            np.r_[np.zeros(15), 0.01 * patterns[0]],
                            np.r_[prior_worst, 0.01 * patterns[0]],
                            np.r_[corners[3], 0.01 * patterns[0]],
                            np.r_[corners[4], 0.01 * patterns[0]],
                            np.r_[prior_worst, 0.01 * patterns[2]]])
    masks = [np.zeros(24, dtype=bool), np.ones(24, dtype=bool)]
    for period in (2, 3, 4, 6, 8, 12):
        for offset in range(period):
            masks.append(np.arange(24) % period == offset)
            masks.append((np.arange(24) // period) % 2 == offset % 2)
    for probability in (0.15, 0.3, 0.5, 0.7):
        masks.extend(generator.random((40, 24)) < probability)
    masks = np.unique(np.asarray(masks), axis=0)
    ranked = []
    ideal = fast(base, np.zeros((1, 27)))[0][0]
    ideal_disagreement = 0.0
    for index, mask in enumerate(masks):
        controls = branches(base, mask)
        scores, _ = fast(controls, screening)
        nominal = fast(controls, np.zeros((1, 27)))[0][0]
        ideal_disagreement = max(ideal_disagreement, abs(float(nominal - ideal)))
        ranked.append((float(scores.min()), index))
        if (index + 1) % 40 == 0:
            print(json.dumps({"branch_schedules": index + 1, "best_screen_min": max(score for score, _ in ranked),
                              "seconds": time.monotonic() - started}), flush=True)
    structured = np.load(HERE / "structured_drift_cases.npz", allow_pickle=False)["scenarios"]
    labels = json.loads((HERE / "structured_labels.json").read_text())
    structured = structured[[index for index, label in enumerate(labels) if label["amplitude"] == 0.01]]
    calibration = np.asarray([np.r_[old, np.zeros(12)] for old in [np.zeros(15), prior_worst, *corners]])
    validation = np.r_[calibration, structured]
    records = []
    best = -1.0
    for screened, index in sorted(ranked, reverse=True)[:10]:
        controls = branches(base, masks[index])
        scores, _ = fast(controls, validation)
        record = {"mask": masks[index].astype(int).tolist(), "screen_min": screened,
                  "validation_min": float(scores.min())}
        records.append(record)
        if record["validation_min"] > best:
            best = record["validation_min"]
            chosen = controls
            chosen_mask = masks[index]
            worst = int(np.argmin(scores))
            chosen_worst = validation[worst]
    candidate = {"schema_version": 1, "angles": chosen.tolist()}
    (HERE / "branch_private_candidate.json").write_text(json.dumps(candidate, indent=2) + "\n")
    report = {"private_only": True, "schedules_tested": len(masks),
              "screening_cases_per_schedule": len(screening), "validation_cases": len(validation),
              "max_nominal_branch_disagreement": ideal_disagreement,
              "selected_mask": chosen_mask.astype(int).tolist(), "best_validation_min": best,
              "independent_worst": exact(chosen, chosen_worst),
              "worst_scenario": row_to_scenario(chosen_worst), "shortlist": records,
              "seconds": time.monotonic() - started, "not_a_continuum_certificate": True}
    (HERE / "branch_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
