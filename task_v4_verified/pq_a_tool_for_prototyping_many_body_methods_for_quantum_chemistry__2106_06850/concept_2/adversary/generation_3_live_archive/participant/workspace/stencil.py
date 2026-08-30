"""The complete, deterministic public integral-perturbation stencil."""

import json
from pathlib import Path

import numpy as np

STENCIL = json.loads(Path(__file__).with_name("stencil.json").read_text())


def stencil_points(pair_matrix):
    matrix = np.asarray(pair_matrix, dtype=float)
    if matrix.shape != (15, 15) or not np.all(np.isfinite(matrix)):
        raise ValueError("expected finite 15 by 15 pair matrix")
    yield {"point": 0, "axis": None, "sign": 0}, matrix.copy()
    point = 1
    for row in range(15):
        for column in range(row, 15):
            displacement = np.zeros((15, 15))
            displacement[row, column] = STENCIL["radius"] / (1 if row == column else np.sqrt(2))
            displacement[column, row] = displacement[row, column]
            for sign in (1, -1):
                yield {"point": point, "axis": [row, column], "sign": sign}, matrix + sign * displacement
                point += 1
