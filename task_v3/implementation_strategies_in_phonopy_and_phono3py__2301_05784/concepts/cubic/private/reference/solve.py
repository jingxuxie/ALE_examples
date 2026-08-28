"""Private official-kernel CLI; never stage this directory to participants."""

import argparse

import numpy as np

from oracle import Oracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        result = Oracle().solve(archive)
    np.savez_compressed(arguments.output, **result)


if __name__ == "__main__":
    main()
