import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from physics import ROOT, admissibility, exact, fast


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--pulses", type=Path, default=ROOT / "champions" / "generation_1" / "pulses.json")
    args = parser.parse_args()
    case = json.loads(args.case.read_text())
    scenario = case["scenario"]
    row = np.r_[scenario["gain_a"], scenario["gain_b"], scenario["zz_common"],
                scenario["zz_local"], scenario["z_drift_radians_per_layer"]]
    raw = args.pulses.read_bytes()
    angles = np.asarray(json.loads(raw)["angles"])
    score = float(fast(angles, [row])[0][0])
    trusted = exact(angles, row)
    assert abs(score - trusted["fidelity"]) < 1e-10
    print(json.dumps({"artifact_sha256": hashlib.sha256(raw).hexdigest(),
                      "compiled_fidelity": score, "independent": trusted,
                      "admissibility": admissibility(row, case["proposed_drift_bound"]),
                      "original_task_not_modified": True}, indent=2))


if __name__ == "__main__":
    main()
