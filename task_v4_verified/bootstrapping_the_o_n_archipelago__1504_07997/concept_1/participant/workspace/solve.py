import json
import sys

import numpy as np
from numpy.polynomial.chebyshev import chebval
from scipy.optimize import minimize_scalar, nnls


def unpack(packed):
    return np.array([[packed[0], packed[1]], [packed[1], packed[2]]])


def solve(case):
    atoms = []
    coordinates = []
    blocks = {block["id"]: block for block in case["blocks"]}
    for block in case["blocks"]:
        coefficients = np.asarray(block["matrix"], dtype=float)

        def geometry(position):
            matrix = unpack(chebval(position, coefficients))
            eigenvalues, eigenvectors = np.linalg.eigh(matrix)
            selected = int(np.argmin(np.abs(eigenvalues)))
            relative = abs(eigenvalues[selected]) / max(np.linalg.norm(matrix), 1e-280)
            vector = eigenvectors[:, selected]
            return relative, np.outer(vector, vector)

        if block["kind"] == "point":
            candidates = [0.0]
        else:
            grid = np.linspace(-1, 1, 257)
            values = [geometry(position)[0] for position in grid]
            candidates = [-1.0, 1.0]
            for index in range(1, len(grid) - 1):
                if values[index] <= min(values[index - 1], values[index + 1]):
                    result = minimize_scalar(
                        lambda position: geometry(position)[0],
                        bounds=(grid[index - 1], grid[index + 1]),
                        method="bounded",
                        options={"xatol": 1e-13},
                    )
                    candidates.append(float(result.x))
        accepted = []
        for position in sorted(candidates):
            relative, projector = geometry(position)
            if relative > 1e-9 or any(abs(position - previous) < 2e-5 for previous in accepted):
                continue
            accepted.append(position)
            physical = float(block["origin"]) + float(block["scale"]) * position
            atoms.append({
                "block": block["id"],
                "x": format(physical, ".17g"),
                "projector": [float(projector[0, 0]), float(projector[0, 1]), float(projector[1, 1])],
                "weight": "1",
            })
            coordinates.append(position)
    if atoms:
        rhs = np.asarray(case["rhs"], dtype=float)
        design = np.zeros((len(rhs), len(atoms)))
        for column, (atom, position) in enumerate(zip(atoms, coordinates)):
            projector = np.asarray(atom["projector"]) * np.array([1.0, 2.0, 1.0])
            for row, kernel in enumerate(blocks[atom["block"]]["moments"]):
                design[row, column] = np.dot(chebval(position, np.asarray(kernel, dtype=float)), projector)
        scales = np.maximum(1, np.abs(rhs))
        design = design / scales[:, None]
        target = rhs / scales
        column_scales = np.maximum(np.linalg.norm(design, axis=0), 1e-200)
        balanced = design / column_scales
        try:
            weights, _ = nnls(balanced, target, maxiter=20 * len(atoms))
        except (RuntimeError, np.linalg.LinAlgError):
            weights = np.maximum(0, np.linalg.lstsq(balanced, target, rcond=1e-12)[0])
        for atom, weight in zip(atoms, weights / column_scales):
            atom["weight"] = format(max(float(weight), 1e-30), ".17g")
    return {"version": 1, "atoms": atoms}


if __name__ == "__main__":
    json.dump(solve(json.load(sys.stdin)), sys.stdout, allow_nan=False)
    sys.stdout.write("\n")
