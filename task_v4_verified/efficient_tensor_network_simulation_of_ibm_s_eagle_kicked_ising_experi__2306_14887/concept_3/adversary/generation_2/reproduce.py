import argparse
import json
from pathlib import Path

import numpy as np

from physics import champion, confirm, fast


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--artifact", type=Path)
    arguments = parser.parse_args()
    document = json.loads(arguments.case.read_text())
    scenario = document["scenario"]
    row = np.r_[scenario["gain_a"], scenario["gain_b"], scenario["zz_common"], scenario["zz_local"],
                scenario["z_drift_even_matching"], scenario["z_drift_odd_matching"]]
    controls = champion() if arguments.artifact is None else np.asarray(json.loads(arguments.artifact.read_text())["angles"])
    if row.shape != (39,) or not np.all(np.isfinite(row)):
        raise ValueError("A finite 39-coordinate calibration is required.")
    if controls.shape != (24, 2) or not np.all(np.isfinite(controls)) or np.max(np.abs(controls)) > np.pi:
        raise ValueError("A bounded finite 24-by-2 control array is required.")
    score = float(fast(controls, [row])[0][0])
    result = confirm(controls, row, score, document.get("label", "reproduced_case"))
    result["original_compiled_difference"] = abs(score - document["compiled_fidelity"])
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
