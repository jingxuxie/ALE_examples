import json
import os
import resource
import sys
import time

import numpy as np
from threadpoolctl import threadpool_limits

import solver
from test_solver import settings


def main():
    length = int(sys.argv[1])
    spin = float(sys.argv[2])
    potential = float(sys.argv[3])
    duration = float(sys.argv[4])
    configuration = settings(length, spin, potential)
    if len(sys.argv) > 5:
        configuration["protection"] = sys.argv[5]
    parameters = [0.16, 0.16, 0.03]
    pairs = [[site, site + separation] for separation in [1, 2, 4, 8] for site in range(length - separation)]
    times = [0.0, duration / 3, 2 * duration / 3, duration]
    original_step = solver.MatrixProductEvolution.step
    counter = [0, 0.0]
    start = time.monotonic()

    def monitored_step(evolution, interval, order=4):
        original_step(evolution, interval, order)
        counter[0] += 1
        counter[1] += interval
        if counter[0] % 2 == 0:
            print("progress", counter[1], "seconds", time.monotonic() - start,
                  "rank", max(tensor.shape[-1] for tensor in evolution.tensors),
                  "cap", evolution.max_bond, "discarded", evolution.discarded, flush=True)

    solver.MatrixProductEvolution.step = monitored_step
    with threadpool_limits(1):
        blocks = solver.simulate_chain(configuration, parameters, times, pairs)
    result = {"settings": configuration, "times": times, "pairs": pairs,
              "elapsed": time.monotonic() - start, "parameters": parameters,
              "peak_memory_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
    for name, values in zip(["density", "violation", "correlation"], blocks):
        result[name] = values.tolist()
        assert np.isfinite(values).all()
    assert np.min(blocks[0]) >= -1e-9 and np.max(blocks[0]) <= 1 + 1e-9
    assert np.max(np.abs(blocks[2])) <= 0.25 + 1e-9
    destination = os.environ.get("CHAIN_OUTPUT", "chain_check.json")
    with open(destination, "w") as stream:
        json.dump(result, stream)
    print("finished", destination, result["elapsed"], flush=True)


if __name__ == "__main__":
    main()
