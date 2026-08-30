import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import COLUMNS, PAIRS, ROWS, certify, grid_constraints, objective, save


def main():
    selected = np.flatnonzero(ROWS % 2 == COLUMNS % 2)
    design = grid_constraints(64)[:, selected]
    _, unique = np.unique(np.round(design, 10), axis=0, return_index=True)
    design = design[unique]
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    equality = np.zeros((2, len(selected)))
    equality[0, np.where(selected == PAIRS.index((4, 4)))[0][0]] = 1
    equality[1, np.where(selected == PAIRS.index((5, 5)))[0][0]] = 1
    best = 1.
    pool = []
    for sign in (-1, 1):
        cost = np.zeros(len(PAIRS))
        cost[PAIRS.index((0, 4))] = 1
        cost[PAIRS.index((1, 5))] = sign
        for first_diagonal in np.linspace(-.2, .7, 19):
            for second_diagonal in np.linspace(-.2, .7, 19):
                result = linprog(-cost[selected], A_ub=constraints, b_ub=upper,
                                 A_eq=equality, b_eq=[first_diagonal, second_diagonal],
                                 bounds=(-1, 1), method="highs")
                if not result.success:
                    continue
                coefficients = np.zeros(len(PAIRS))
                coefficients[selected] = result.x
                value = objective(coefficients)[0]
                if value > 1.58:
                    pool.append((value, coefficients.copy()))
                if value > best:
                    certified, report = certify(coefficients)
                    if report["trace"] > best:
                        best = report["trace"]
                        save(coefficients, Path("block_scan.json"))
                        print("BEST", sign, first_diagonal, second_diagonal, json.dumps(report), flush=True)
            print("scan", sign, first_diagonal, "best", best, flush=True)
    pool.sort(key=lambda entry: entry[0], reverse=True)
    np.save("block_pool.npy", np.array([entry[1] for entry in pool[:60]]))
    print("pool", len(pool), [entry[0] for entry in pool[:20]], flush=True)


if __name__ == "__main__":
    main()
