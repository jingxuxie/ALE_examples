"""Existing capability: bulk bands only. Device transport remains to be implemented."""

import argparse

import numpy as np

from bulk import eigenvalues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        case = {name: archive[name] for name in archive.files}
    wavevectors = np.column_stack((np.linspace(-0.5, 0.5, 65), np.zeros((65, 2))))
    bands = np.asarray([eigenvalues(case, wavevector) for wavevector in wavevectors])
    np.savez_compressed(arguments.output, bulk_wavevectors=wavevectors, bulk_bands=bands)


if __name__ == "__main__":
    main()
