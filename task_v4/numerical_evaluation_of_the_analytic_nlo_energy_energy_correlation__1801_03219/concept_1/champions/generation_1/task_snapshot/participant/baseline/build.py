import json
from pathlib import Path
import sys

import numpy as np
from numpy.polynomial import chebyshev


def main():
    data = np.load(Path(__file__).resolve().parents[1] / "input" / "calibration.npz")
    knots = np.linspace(-24, 24, 7)
    coefficients = []
    for left, right in zip(knots[:-1], knots[1:]):
        selected = (data["coordinates"] >= left) & (data["coordinates"] <= right)
        transformed = (2*data["coordinates"][selected]-left-right)/(right-left)
        coefficients.append([
            chebyshev.chebfit(transformed, data["values"][selected, channel], 15).tolist()
            for channel in range(3)
        ])
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    (output / "model.json").write_text(json.dumps({"knots": knots.tolist(), "coefficients": coefficients}))


if __name__ == "__main__":
    main()
