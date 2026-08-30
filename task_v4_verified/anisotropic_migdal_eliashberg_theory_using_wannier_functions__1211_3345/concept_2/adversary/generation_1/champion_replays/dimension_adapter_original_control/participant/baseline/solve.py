import argparse
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("witness.npz"))
    arguments = parser.parse_args()
    reference_path = Path(__file__).resolve().parents[1] / "input" / "reference.npz"
    with np.load(reference_path, allow_pickle=False) as archive:
        reference = np.array(archive["reference"], copy=True)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("wb") as stream:
        np.savez_compressed(stream, kernels=np.stack([reference, reference]))


if __name__ == "__main__":
    main()
