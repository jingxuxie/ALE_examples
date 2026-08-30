"""Private timing control: actual v4 algorithm with only its internal deadline lifted."""

import argparse
import numpy as np
import actual_v4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        instance = {key: archive[key] for key in archive.files}
    delta, renormalization = actual_v4.solve(instance, deadline=float("inf"))
    np.savez(arguments.output, delta=delta, z=renormalization)


if __name__ == "__main__":
    main()
