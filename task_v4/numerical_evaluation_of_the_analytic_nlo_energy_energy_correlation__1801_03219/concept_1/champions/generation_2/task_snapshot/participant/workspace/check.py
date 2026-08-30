import json
from pathlib import Path
import sys

import numpy as np

from model import evaluate, load_model


def main():
    data = np.load(Path(__file__).resolve().parents[1] / "input" / "calibration.npz")
    model = load_model(Path(sys.argv[1]) / "model.json")
    result = {"scalar_count": model["scalar_count"]}
    for label, derivative, tolerance in [("values", False, 2e-8), ("derivatives", True, 2e-7)]:
        truth = data[label]
        errors = np.abs(evaluate(model, data["coordinates"], derivative) - truth)/(1+np.abs(truth))
        result[label] = {"worst_mixed_error": float(np.max(errors)),
                         "worst_tolerance_ratio": float(np.max(errors)/tolerance)}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
