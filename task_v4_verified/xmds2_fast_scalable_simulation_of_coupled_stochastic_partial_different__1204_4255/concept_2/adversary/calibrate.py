import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from simulator import DEFAULT, quick


def run(count):
    generator = np.random.default_rng(20260828)
    started = time.monotonic()
    records = []
    for index in range(count):
        parameters = dict(DEFAULT)
        if index:
            parameters.update({
                "dispersion": generator.uniform(0.18, 0.45),
                "nonlinearity": generator.uniform(6, 20),
                "duration": generator.uniform(0.45, 1.4),
                "cross": generator.uniform(0.55, 1.3),
                "coupling": generator.uniform(0.2, 1.2),
                "detuning": generator.uniform(-0.5, 0.5),
                "population": generator.uniform(0.35, 0.65),
            })
            for name in ("a1", "a2"):
                parameters[name] = generator.uniform(0.08, 0.4)
            for name in ("b1", "b2", "c1", "c2"):
                parameters[name] = generator.uniform(-0.25, 0.25)
            for name in ("phase1", "phase2", "shift", "relative_phase"):
                parameters[name] = generator.uniform(-np.pi, np.pi)
        try:
            result = quick(parameters)
        except (ValueError, FloatingPointError) as error:
            result = {"error": str(error)}
        record = {"index": index, "parameters": parameters, "metrics": result}
        records.append(record)
        print(json.dumps({"index": index, **result}), flush=True)
    destination = ROOT / "adversary" / "calibration.json"
    destination.write_text(json.dumps({"wall_seconds": time.monotonic() - started, "records": records}, indent=2))


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 24)
