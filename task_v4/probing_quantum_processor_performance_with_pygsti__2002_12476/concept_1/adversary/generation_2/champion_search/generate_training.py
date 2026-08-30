import argparse
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import Benchmark, HERE, ROOT

sys.path.insert(0, str(ROOT / "generations/generation_1/participant/workspace"))
from physics import FAMILIES, fisher_features, sample_parameters


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-family", type=int, default=30)
    parser.add_argument("--seed", type=int, default=735046610)
    args = parser.parse_args()
    started = time.monotonic()
    benchmark = Benchmark()
    rng = np.random.default_rng(args.seed)
    families = np.repeat(np.array(FAMILIES), args.per_family)
    parameters = np.array([sample_parameters(rng, str(family)) for family in families])
    features = []
    for index, point in enumerate(parameters):
        features.append(fisher_features(point, benchmark.candidates))
        if (index + 1) % 12 == 0:
            print(json.dumps(dict(complete=index + 1, total=len(parameters), seconds=time.monotonic() - started)), flush=True)
    np.savez_compressed(HERE / "own_training.npz", features=np.array(features), parameters=parameters,
                        families=families, seed=np.array(args.seed), costs=benchmark.costs)
    print(json.dumps(dict(event="own_training_ready", seconds=time.monotonic() - started, scenarios=len(parameters),
                          seed=args.seed, main_held_out_benchmark_used=False)), flush=True)


if __name__ == "__main__":
    main()
