import argparse
import json
import os
from pathlib import Path

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from simulator import fidelities, load_pulses, training_scenarios


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    scores = fidelities(load_pulses(args.submission), training_scenarios())
    print(json.dumps({"public_min_fidelity": float(scores.min()),
                      "public_mean_fidelity": float(scores.mean()),
                      "public_fidelities": scores.tolist()}, indent=2))


if __name__ == "__main__":
    main()
