import argparse
import json
from pathlib import Path

import numpy as np


def diagnose(payload):
    rows = []
    for case in payload["cases"]:
        trace = max([value["residual"] for value in case.get("observables", {}).values()] + [0.0])
        worst_error = max(integral["estimated_error"] for integral in case["integrals"].values())
        nonfinite = sum(not np.all(np.isfinite(value))
                        for integral in case["integrals"].values()
                        for coefficient in integral["coefficients"].values()
                        for value in coefficient.values())
        rows.append({"case_id": case["id"], "family": case["family"], "trace_residual": trace,
                     "max_internal_error": worst_error, "nonfinite_channels": nonfinite,
                     "unconverged_integrals": sum(not integral.get("converged", False)
                                                   for integral in case["integrals"].values()),
                     "seconds": case["seconds"]})
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions")
    arguments = parser.parse_args()
    print(json.dumps(diagnose(json.loads(Path(arguments.predictions).read_text())), indent=2))
