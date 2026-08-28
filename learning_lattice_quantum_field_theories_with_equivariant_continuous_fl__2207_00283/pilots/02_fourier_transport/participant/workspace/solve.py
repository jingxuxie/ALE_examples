"""Implement the contract in ../input/CONTRACT.md; no private imports."""

import sys

import numpy as np


def solve(inputs):
    """Return a dictionary of output arrays for one contract-v1 archive."""
    raise NotImplementedError("Implement Fourier representation and transport")


def main():
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        inputs = dict(archive)
    np.savez(sys.argv[2], **solve(inputs))


if __name__ == "__main__":
    main()
