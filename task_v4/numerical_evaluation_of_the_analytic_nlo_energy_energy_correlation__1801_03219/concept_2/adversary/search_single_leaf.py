"""Optimize the actual missed error of a single adaptive leaf."""

import json
import time

import numpy as np
from scipy.linalg import svd

from search import BINS, COLOR, KWEIGHTS, NODES, Kernel, assess, basis, matrices, quantize, response, save


def leaf_error(kernel, witness, leaf):
    left, right = BINS[witness["bin"]]

    def integral(nodes, weights):
        points = (leaf + (nodes + 1) / 2) / 8
        spectra = 2 * (right - left) * kernel(left + (right - left) * points) * COLOR
        modes = response(points, witness)[:, None] * basis(points, witness)
        return np.einsum("n,nc,nk->ck", weights / 16, spectra, modes)

    nodes, weights = np.polynomial.legendre.leggauss(80)
    return integral(NODES, KWEIGHTS) - integral(nodes, weights)


def main():
    started = time.monotonic()
    kernel = Kernel()
    best = -1.0
    records = []
    for frequency in range(53, 30, -1):
        for bin_name in ("central", "backward", "collinear"):
            template = {"version": 1, "bin": bin_name, "band_start": frequency, "tilt": 0, "curvature": 0}
            constraints, _, reference = matrices(kernel, template)
            for leaf in range(8):
                matrix = constraints[:, [leaf, 8 + leaf // 2], :].reshape(6, 24)
                matrix /= np.linalg.norm(matrix, axis=1)[:, None]
                _, singular, right_vectors = svd(matrix, full_matrices=True)
                nullspace = right_vectors[6:].T
                error = leaf_error(kernel, template, leaf)
                for channel in range(3):
                    vector = nullspace @ (nullspace.T @ error[channel])
                    try:
                        witness = quantize(template, vector)
                    except ValueError:
                        continue
                    results = assess(kernel, witness, reference)
                    margin = min(result["margin_screen"] for result in results)
                    record = {"bin": bin_name, "band": frequency, "leaf": leaf,
                              "objective_channel": channel, "margin": margin,
                              "panels": [result["panels"] for result in results]}
                    records.append(record)
                    if margin > best:
                        best = margin
                        save("adversary/best_screen/witness.json", witness)
                        save("adversary/best_screen/screen.json", {"margin": margin, "results": results,
                                                                 "method": "single-leaf constrained error maximization",
                                                                 "leaf": leaf, "singular_values": singular.tolist()})
                        print(json.dumps(record), flush=True)
                    if best > 10:
                        break
                if best > 10:
                    break
            if best > 10:
                break
        if best > 10:
            break
    save("adversary/single_leaf_search_outcomes.json", {"attempts": len(records), "best_screen_margin": best,
                                                       "seconds": time.monotonic() - started, "records": records,
                                                       "warning": "Screen only; independent certification required."})


if __name__ == "__main__":
    main()
