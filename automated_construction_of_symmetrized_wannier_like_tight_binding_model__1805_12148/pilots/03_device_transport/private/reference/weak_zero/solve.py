"""Finite, correctly shaped zero-transport weak control; not a transport solver."""

import argparse

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as case:
        energy_count = len(case["energies"])
        lead_count = int(case["lead_count"])
        orbital_count = case["h_matrices"].shape[1]
        dimensions = [len(case[f"lead_cells_{index}"]) * orbital_count for index in range(lead_count)]
    result = {f"sigma_{index}": np.zeros((energy_count, size, size), dtype=np.complex128)
              for index, size in enumerate(dimensions)}
    result["mode_counts"] = np.zeros((energy_count, lead_count), dtype=np.int64)
    result["channels"] = np.zeros((energy_count, lead_count, lead_count, max(dimensions)))
    for key in ("transmission", "partition_noise", "lb_conductance"):
        result[key] = np.zeros((energy_count, lead_count, lead_count))
    np.savez_compressed(arguments.output, **result)


if __name__ == "__main__":
    main()
