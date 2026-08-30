import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from simulator import diagnostics, field_distance, independent, integrate, observable_distance


records = json.loads((ROOT / "adversary" / "calibration.json").read_text())["records"]
results = []
for record_index in (1, 8, 23):
    parameters = records[record_index]["parameters"]
    started = time.monotonic()
    coarse = integrate(parameters, 32, 512)
    fine = integrate(parameters, 32, 1024)
    medium = integrate(parameters, 128, 4096)
    refined = integrate(parameters, 192, 8192)
    other, evaluations = independent(parameters, 128)
    result = {
        "index": record_index,
        "parameters": parameters,
        "certificate": float(np.max(field_distance(coarse, fine))),
        "gap": observable_distance(fine, refined).tolist(),
        "spacetime_field_delta": float(np.max(field_distance(medium, refined))),
        "spacetime_observable_delta": float(np.max(observable_distance(medium, refined))),
        "independent_field_delta": float(np.max(field_distance(medium, other))),
        "independent_observable_delta": float(np.max(observable_distance(medium, other))),
        "reference_diagnostics": diagnostics(parameters, refined),
        "diagnostics": diagnostics(parameters, fine),
        "independent_evaluations": evaluations,
        "wall_seconds": time.monotonic() - started,
    }
    results.append(result)
    print(json.dumps(result), flush=True)
(ROOT / "adversary" / "reference_probe.json").write_text(json.dumps(results, indent=2))
