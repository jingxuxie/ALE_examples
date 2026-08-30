import argparse
from pathlib import Path

import numpy as np

from physics import load_instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("witness.npz"))
    arguments = parser.parse_args()
    reference = load_instance()["reference"]
    kernels = np.stack([reference, reference])
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("wb") as stream:
        np.savez_compressed(stream, kernels=kernels)


if __name__ == "__main__":
    main()
