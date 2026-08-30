"""Search correlated false convergence of one adaptive sibling pair."""

import json
import time

import numpy as np
from scipy.linalg import svd

from search import Kernel, assess, matrices, quantize, save


def main():
    started = time.monotonic()
    kernel = Kernel()
    best = -1.0
    records = []
    for frequency in range(53, 20, -1):
        for bin_name in ("central", "backward", "collinear"):
            template = {"version": 1, "bin": bin_name, "band_start": frequency, "tilt": 0, "curvature": 0}
            constraints, error, reference = matrices(kernel, template)
            for parent in range(4):
                matrix = constraints[:, [2 * parent, 2 * parent + 1, 8 + parent], :].reshape(9, 24)
                matrix /= np.linalg.norm(matrix, axis=1)[:, None]
                _, singular, right_vectors = svd(matrix, full_matrices=True)
                nullspace = right_vectors[9:].T
                for channel in range(3):
                    vector = nullspace @ (nullspace.T @ error[channel])
                    try:
                        witness = quantize(template, vector)
                    except ValueError:
                        continue
                    results = assess(kernel, witness, reference)
                    margin = min(result["margin_screen"] for result in results)
                    record = {"bin": bin_name, "band": frequency, "parent": parent,
                              "objective_channel": channel, "margin": margin,
                              "panels": [result["panels"] for result in results]}
                    records.append(record)
                    if margin > best:
                        best = margin
                        save("adversary/best_screen/witness.json", witness)
                        save("adversary/best_screen/screen.json", {"margin": margin, "results": results,
                                                                 "method": "localized sibling-pair nullspace",
                                                                 "parent": parent, "singular_values": singular.tolist()})
                        print(json.dumps(record), flush=True)
                    if best > 10:
                        break
                if best > 10:
                    break
            if best > 10:
                break
        if best > 10:
            break
    save("adversary/localized_search_outcomes.json", {"attempts": len(records), "best_screen_margin": best,
                                                     "seconds": time.monotonic() - started, "records": records,
                                                     "warning": "Screening only; independent high-precision and native-source validation still required."})


if __name__ == "__main__":
    main()
