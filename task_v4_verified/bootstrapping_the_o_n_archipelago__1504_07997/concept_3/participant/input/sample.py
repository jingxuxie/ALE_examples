"""Print a reproducible, labeled public training sample."""

import argparse
import json

from model import FAMILIES, Oracle, TARGETS, generate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=150407997)
    parser.add_argument("--family", choices=FAMILIES, default="regular")
    args = parser.parse_args()
    instance = generate(args.seed, args.family)
    oracle = Oracle(instance, args.seed + 1)
    observations = []
    for time in (0.5, 2.0, 4.0):
        for probe in ([1.0, 0.0], [0.0, 1.0], [2 ** -0.5, 2 ** -0.5]):
            observations.append({"t": time, "u": probe, **oracle.measure(time, probe)})
    print(json.dumps({
        "training_only": True, "seed": args.seed, "family": args.family,
        "truth": dict(zip(TARGETS, instance.target().tolist())),
        "observations": observations,
    }, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
