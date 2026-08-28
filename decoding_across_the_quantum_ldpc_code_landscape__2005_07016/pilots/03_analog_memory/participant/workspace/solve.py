import argparse

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as case:
        shots, rounds, num_checks = case["readout"].shape
        num_qubits = case["checks"].shape[1]
    np.savez_compressed(
        arguments.output,
        increments=np.zeros((shots, rounds, num_qubits), dtype=np.uint8),
        syndrome_history=np.zeros((shots, rounds, num_checks), dtype=np.uint8),
    )


if __name__ == "__main__":
    main()

