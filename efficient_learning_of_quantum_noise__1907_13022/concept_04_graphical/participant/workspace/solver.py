import sys

import numpy as np

from local_adapter import read_tables


def main(input_path, output_path):
    with np.load(input_path, allow_pickle=False) as data:
        tables = list(read_tables(data))
    if not tables:
        raise ValueError("No local observations")
    raise NotImplementedError("Learn the interactions and implement normalized global queries")


if __name__ == "__main__":
    main(*sys.argv[1:])
