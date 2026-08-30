import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares, nnls


def complete(instance):
    design = np.asarray(instance["design"])
    target = np.asarray(instance["target"])
    scales = np.asarray(instance["scales"])
    diagonal = []
    for component in (0, 2):
        coefficients, residual = nnls(design / scales[:, component, None], target[:, component] / scales[:, component], maxiter=3000)
        diagonal.append(coefficients)
    support = [0] + [int(index) for index in np.argsort(-(diagonal[0]+diagonal[1])) if index != 0][:instance["max_atoms"]-1]
    vectors = np.sqrt(np.maximum(np.stack(diagonal, axis=1)[support], 1e-7))
    vectors[0, 0] = np.sqrt(instance["shared_ope_squared"])

    def residual(parameters):
        current = np.concatenate([[vectors[0, 0]], parameters]).reshape(-1, 2)
        products = np.stack([current[:, 0]**2, current[:, 0]*current[:, 1], current[:, 1]**2], axis=1)
        return ((design[:, support] @ products - target) / scales).ravel()

    optimized = least_squares(residual, vectors.ravel()[1:], bounds=(-4, 4), max_nfev=1200,
                              ftol=1e-12, xtol=1e-12, gtol=1e-12)
    vectors = np.concatenate([[vectors[0, 0]], optimized.x]).reshape(-1, 2)
    return {"id": instance["id"], "atoms": [{"index": index, "ope": vector.tolist()}
                                           for index, vector in zip(support, vectors)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    arguments = parser.parse_args()
    cases = []
    for instance in json.loads(Path(arguments.input).read_text())["instances"]:
        try:
            cases.append(complete(instance))
        except Exception:
            cases.append({"id": instance["id"], "atoms": []})
        Path(arguments.output).write_text(json.dumps({"cases": cases}) + "\n")


if __name__ == "__main__":
    main()
