import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from optimize import COLUMNS, ERROR_WEIGHTS, ROWS, save


def main():
    coefficients = np.array(json.loads(Path("refined.json").read_text())["kernel_b"])

    def rotate(angle):
        rotation = np.zeros((18, 18))
        for harmonic in range(1, 10):
            cosine = np.cos(harmonic * angle)
            sine = np.sin(harmonic * angle)
            block = slice(2 * harmonic - 2, 2 * harmonic)
            rotation[block, block] = [[cosine, -sine], [sine, cosine]]
        result = rotation.T @ coefficients @ rotation
        return (result + result.T) / 2

    def error(angle):
        return ERROR_WEIGHTS @ np.abs(rotate(angle)[ROWS, COLUMNS])

    angles = np.arange(2048) * np.pi / 2048
    errors = np.array([error(angle) for angle in angles])
    index = errors.argmin()
    optimum = minimize_scalar(error, bounds=(angles[index] - np.pi / 2048, angles[index] + np.pi / 2048),
                              method="bounded", options={"xatol": 1e-13})
    rotated = rotate(optimum.x)
    print("angle", optimum.x, "error", optimum.fun,
          "cross reflection", np.max(np.abs(rotated[np.indices((18, 18)).sum(axis=0) % 2 == 1])))
    print(save(rotated[ROWS, COLUMNS], Path("oriented.json")))


if __name__ == "__main__":
    main()
