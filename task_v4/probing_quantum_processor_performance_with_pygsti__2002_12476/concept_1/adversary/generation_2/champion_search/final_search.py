import argparse
import json
import os
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import HERE
from multi_exchange import MultiSearch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=290)
    parser.add_argument("--seed", type=int, default=10832291)
    parser.add_argument("--start", default="phase_4_design.json")
    args = parser.parse_args()
    search = MultiSearch(args.seconds, args.seed, True)
    counts = np.array(json.loads((HERE / args.start).read_text())["batches"])
    search.consider(counts, "final_private_seed")
    search.exchange(counts, rounds=8, width=5)
    search.log("final_private_finished", core=search.best[1]["core_score"],
               worst=search.best[1]["worst_family_score"],
               intact=search.best[1]["intact_mean_ratio"],
               passed=search.best[1]["passed"])


if __name__ == "__main__":
    main()
