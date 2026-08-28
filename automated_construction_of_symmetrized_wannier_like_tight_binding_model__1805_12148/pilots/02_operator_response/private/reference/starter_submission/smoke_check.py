import argparse
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    arguments = parser.parse_args()
    with np.load(arguments.result, allow_pickle=False) as result:
        for name in result.files:
            assert np.isfinite(result[name]).all(), name
        vectors = result["rvec"]
        assert np.array_equal(vectors, np.rint(vectors))
        assert len({tuple(vector) for vector in vectors}) == len(vectors)
        lookup = {tuple(vector): index for index, vector in enumerate(vectors)}
        hopping = result["ham"]
        residual = 0.0
        for index, vector in enumerate(vectors):
            inverse = lookup.get(tuple(-vector))
            partner = np.zeros_like(hopping[index]) if inverse is None else hopping[inverse].conj().T
            residual = max(residual, float(np.max(np.abs(hopping[index] - partner))))
        assert residual < 2e-7, residual
        print({"finite": True, "unique_R": True, "H_hermiticity_residual": residual})


if __name__ == "__main__":
    main()
