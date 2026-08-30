import argparse
import json
import time

import search
import smooth
import numpy as np
from scipy.optimize import least_squares


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=80)
    parser.add_argument("--iterations", type=int, default=180)
    parser.add_argument("--prefix", default="structured")
    parser.add_argument("--mode", choices=["coherent", "cycle", "matching", "single"], default="coherent")
    parser.add_argument("--gap", type=float, default=0)
    parser.add_argument("--small", action="store_true")
    arguments = parser.parse_args()
    random = np.random.default_rng(746230)
    started = time.monotonic()
    best = 0
    for run in range(arguments.count):
        initial = np.zeros(42)
        if arguments.mode == "coherent":
            signs = random.choice([-1, 1], 7)
            strength = random.uniform(0.16, 0.34)
            if arguments.small:
                signs = np.r_[1, [1 if (run // 2) & (1 << position) else -1 for position in range(6)]]
                strength = random.uniform(0.025, 0.1) * (1 if run % 2 == 0 else -1)
            for position, (source, destination) in enumerate(search.VIRTUAL_EDGES):
                initial[position] = -strength * signs[source] * signs[destination] + random.normal(scale=0.003 if arguments.small else 0.025)
            initial[21:] = random.uniform(-0.599, -0.3, 21)
            if arguments.small:
                initial[21:] = random.uniform(-0.599, 0.599, 21)
            active = np.arange(42)
        elif arguments.mode == "cycle":
            extra = [2, 4, 5, 6][run % 4]
            nodes = [0, 1, 3, extra]
            active_hopping = [position for position, edge in enumerate(search.VIRTUAL_EDGES) if all(node in nodes for node in edge)]
            active = np.r_[active_hopping, np.arange(21, 42)]
            for source in [0, 1]:
                for destination in [3, extra]:
                    position = search.VIRTUAL_EDGES.index(tuple(sorted((source, destination))))
                    initial[position] = random.uniform(0.18, 0.44) * random.choice([-1, 1])
            initial[21:] = random.uniform(-0.599, 0.599, 21)
        elif arguments.mode == "matching":
            permutation = random.permutation(7)
            active_hopping = [search.VIRTUAL_EDGES.index(tuple(sorted(permutation[position:position + 2])))
                              for position in (0, 2, 4)]
            initial[active_hopping] = random.uniform(0.2, 0.449, 3) * random.choice([-1, 1], 3)
            initial[21:] = random.uniform(-0.599, 0.599, 21)
            active = np.r_[active_hopping, np.arange(21, 42)]
        else:
            leaf = [0, 1, 2, 4, 5, 6][run % 6]
            fixed = search.VIRTUAL_EDGES.index(tuple(sorted((3, leaf))))
            initial[:21] = random.uniform(-0.015, 0.015, 21)
            initial[fixed] = (0.449 if run % 3 else 0.3) * random.choice([-1, 1])
            initial[21:] = random.uniform(-0.599, 0.599, 21)
            active = np.array([position for position in range(42) if position != fixed])
        initial = np.clip(initial, -search.BOUND + 0.00101, search.BOUND - 0.00101)
        target = -[100e-6, 200e-6, 500e-6, 65e-6][run % 4]
        if arguments.mode in ("matching", "single"):
            target = (-1 if run % 4 != 3 else 1) * 80e-6
        if arguments.small:
            target = (-1 if run % 2 == 0 else 1) * 100e-6
        objective = smooth.Objective(target, sensitivity_weight=3.5)

        def expand(variables):
            controls = initial.copy()
            controls[active] = variables
            return controls

        def residual(variables):
            values = objective.fun(expand(variables))
            if arguments.gap:
                values = np.r_[values, (objective.result["physical"][1] - arguments.gap) * 400]
            return values

        def jacobian(variables):
            values = objective.jac(expand(variables))[:, active]
            if arguments.gap:
                values = np.vstack([values, objective.result["physical_gradient"][1, active] * 400])
            return values

        fit = least_squares(residual, initial[active], jac=jacobian,
                            bounds=(-search.BOUND[active] + 0.001, search.BOUND[active] - 0.001),
                            max_nfev=arguments.iterations, ftol=1e-8, xtol=1e-9, gtol=1e-7)
        controls = expand(fit.x)
        result = search.evaluate(controls)
        info = search.summary(result)
        info.update(run=run, nfev=fit.nfev, cost=float(fit.cost), seconds=time.monotonic() - started)
        search.save(controls, f"{arguments.prefix}_{run:03d}.json")
        if info["robust_factor"] > best and np.all(result["physical"] >= [0.95, 0.4, 0.6]):
            best = info["robust_factor"]
            search.save(controls, f"{arguments.prefix}_best.json")
        print(json.dumps(info), flush=True)


if __name__ == "__main__":
    main()
