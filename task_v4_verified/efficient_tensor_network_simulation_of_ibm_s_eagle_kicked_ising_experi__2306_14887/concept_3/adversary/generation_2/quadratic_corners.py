import json
import time

import numpy as np

from physics import HERE, ROOT, champion, confirm, error_derivatives, fast


def main():
    started = time.monotonic()
    controls = champion()
    prior = json.loads((ROOT / "champions" / "generation_2" / "field_scan_validation.json").read_text())
    calibrations = [np.zeros(15)] + [np.asarray(entry["calibration"]) for entry in prior["calibrations"]]
    odd_signs = 1.0 - 2.0 * ((np.arange(4096)[:, None] >> np.arange(12)) & 1)
    even_signs = odd_signs[::2]
    all_rows = []
    all_scores = []
    records = []
    for index, calibration in enumerate(calibrations):
        central = np.r_[calibration, np.zeros(24)]
        offsets = np.zeros((48, 39))
        step = 0.0002
        for coordinate in range(24):
            offsets[2 * coordinate, 15 + coordinate] = step
            offsets[2 * coordinate + 1, 15 + coordinate] = -step
        derivatives = error_derivatives(controls, central + offsets)[1][:, 15:]
        hessian = ((derivatives[::2] - derivatives[1::2]) / (2 * step)).T
        asymmetry = float(np.max(np.abs(hessian - hessian.T)))
        loss_matrix = -0.5 * 0.01 ** 2 * (hessian + hessian.T) / 2
        losses = 2 * (even_signs @ loss_matrix[:12, 12:]) @ odd_signs.T
        losses += np.einsum("bi,ij,bj->b", even_signs, loss_matrix[:12, :12], even_signs)[:, None]
        losses += np.einsum("bi,ij,bj->b", odd_signs, loss_matrix[12:, 12:], odd_signs)[None, :]
        selected = np.argpartition(losses.reshape(-1), -48)[-48:]
        even_indices, odd_indices = np.unravel_index(selected, losses.shape)
        rows = np.c_[np.tile(calibration, (len(selected), 1)),
                     0.01 * even_signs[even_indices], 0.01 * odd_signs[odd_indices]]
        scores = fast(controls, rows)[0]
        center_fidelity = float(fast(controls, [central])[0][0])
        prediction = center_fidelity - losses.reshape(-1)[selected]
        all_rows.extend(rows)
        all_scores.extend(scores)
        worst = int(np.argmin(scores))
        records.append({"calibration_index": index, "surrogate_corners_ranked": int(losses.size),
                        "exact_cases": len(rows), "minimum": float(scores.min()),
                        "below_095": int(np.sum(scores < 0.95)),
                        "hessian_symmetry_error": asymmetry,
                        "maximum_prediction_error_on_selected": float(np.max(np.abs(prediction - scores))),
                        "worst_even_odd_difference": float(np.max(np.abs(rows[worst, 15:27] - rows[worst, 27:39])))})
        print(json.dumps(records[-1]), flush=True)
    all_rows = np.asarray(all_rows)
    all_scores = np.asarray(all_scores)
    np.savez_compressed(HERE / "quadratic_corner_cases.npz", scenarios=all_rows, fidelities=all_scores)
    report = {"calibrations": len(calibrations), "exact_cases": len(all_rows),
              "surrogate_only_corners_per_calibration": int(losses.size),
              "minimum": float(all_scores.min()), "below_095": int(np.sum(all_scores < 0.95)),
              "records": records, "seconds": time.monotonic() - started,
              "confirmed": [confirm(controls, all_rows[index], all_scores[index], "quadratic_ranked_corner")
                            for index in np.argsort(all_scores)[:8]],
              "not_an_exact_exhaustive_corner_check": True,
              "method": "Rank all 24-site two-matching sign corners modulo simultaneous field-sign symmetry using the quadratic loss Hessian; confirm only the top 48 per calibration with exact dynamics."}
    (HERE / "quadratic_corner_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"complete": True, "minimum": report["minimum"], "seconds": report["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
