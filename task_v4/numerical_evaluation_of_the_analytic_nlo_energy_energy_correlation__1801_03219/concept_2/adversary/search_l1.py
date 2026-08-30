"""Optimize material error per integrated absolute moment, not raw error alone."""

import json
import time

import numpy as np
from scipy.linalg import svd
from scipy.optimize import linprog

from search import BINS, COLOR, Kernel, assess, basis, matrices, quantize, response, save
from search_single_leaf import leaf_error


def main():
    started = time.monotonic()
    kernel = Kernel()
    best = -1.0
    records = []
    for frequency in (53, 52, 51, 50):
        for bin_name in ("collinear", "central", "backward"):
            template = {"version": 1, "bin": bin_name, "band_start": frequency, "tilt": 0, "curvature": 0}
            constraints, _, reference = matrices(kernel, template)
            points = (np.arange(512) + .5) / 512
            left, right = BINS[bin_name]
            spectra = 2 * (right - left) * kernel(left + (right - left) * points) * COLOR
            modes = response(points, template)[:, None] * basis(points, template)
            for leaf in range(8):
                matrix = constraints[:, [leaf, 8 + leaf // 2], :].reshape(6, 24)
                matrix /= np.linalg.norm(matrix, axis=1)[:, None]
                _, _, right_vectors = svd(matrix, full_matrices=True)
                orthogonal_rows = right_vectors[:6]
                nullspace = right_vectors[6:].T
                error = leaf_error(kernel, template, leaf)
                for channel in (0, 1, 2):
                    objective_error = error[channel] / np.linalg.norm(error[channel])
                    weighted_modes = modes * spectra[:, channel, None]
                    weighted_modes /= np.linalg.norm(weighted_modes) / np.sqrt(weighted_modes.size)
                    inequalities = np.block([[weighted_modes, -np.eye(512)], [-weighted_modes, -np.eye(512)]])
                    equality = np.zeros((7, 536))
                    equality[:6, :24] = orthogonal_rows
                    equality[6, :24] = objective_error
                    rhs = np.zeros(7)
                    rhs[6] = 1
                    result = linprog(np.concatenate((np.zeros(24), np.ones(512) / 512)),
                                     A_ub=inequalities, b_ub=np.zeros(1024), A_eq=equality, b_eq=rhs,
                                     bounds=[(None, None)] * 24 + [(0, None)] * 512,
                                     method="highs", options={"dual_feasibility_tolerance": 1e-9, "primal_feasibility_tolerance": 1e-9})
                    if not result.success:
                        continue
                    vector = nullspace @ (nullspace.T @ result.x[:24])
                    try:
                        witness = quantize(template, vector)
                    except ValueError:
                        continue
                    results = assess(kernel, witness, reference)
                    margin = min(item["margin_screen"] for item in results)
                    record = {"bin": bin_name, "band": frequency, "leaf": leaf,
                              "objective_channel": channel, "margin": margin}
                    records.append(record)
                    if margin > best:
                        best = margin
                        save("adversary/best_screen/witness.json", witness)
                        save("adversary/best_screen/screen.json", {"margin": margin, "results": results,
                                                                 "method": "material-error L1 optimization",
                                                                 "leaf": leaf})
                        print(json.dumps(record), flush=True)
                    if best > 1.5:
                        break
                if best > 1.5:
                    break
            if best > 1.5:
                break
        if best > 1.5:
            break
    save("adversary/l1_search_outcomes.json", {"attempts": len(records), "best_screen_margin": best,
                                              "seconds": time.monotonic() - started, "records": records,
                                              "warning": "Screen only; independent certification required."})


if __name__ == "__main__":
    main()
