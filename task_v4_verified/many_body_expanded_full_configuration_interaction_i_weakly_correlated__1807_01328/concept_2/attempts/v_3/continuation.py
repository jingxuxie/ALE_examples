import argparse
import json
import time

import search
import scan
import numpy as np
from scipy.optimize import least_squares


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--iterations", type=int, default=220)
    arguments = parser.parse_args()
    pools = search.assay.training_uniforms(956700, 512)
    started = time.monotonic()
    for position, name in enumerate(arguments.files):
        initial = search.load(name)
        sign = np.sign(search.evaluate(initial)["tail"])
        for target in [55, 65, 80, 100, 125, 150, 200, 300, 500, 800, 1200]:
            objective = search.NominalObjective(sign * target * 1e-6)
            fit = least_squares(objective.fun, initial, jac=objective.jac,
                                bounds=(-search.BOUND, search.BOUND), max_nfev=arguments.iterations,
                                ftol=1e-8, xtol=1e-9, gtol=1e-7)
            output = f"continuation_{position:02d}_{target:04d}.json"
            search.save(fit.x, output)
            info = scan.proxy(fit.x, pools)
            if info is None:
                info = search.summary(search.evaluate(fit.x))
            info.update(file=output, source=name, target=target, nfev=fit.nfev,
                        cost=float(fit.cost), seconds=time.monotonic() - started)
            print(json.dumps(info), flush=True)
