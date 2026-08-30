"""Size/timing calibration on development-only draws, never test labels."""

import json
import os
from pathlib import Path
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.sched_setaffinity(0, {sorted(os.sched_getaffinity(0))[160 % len(os.sched_getaffinity(0))]})
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/input"))

import numpy as np

from distribution import draw_batch
from exact import label_instance


def main():
    report = {}
    for n_sites in (8, 10):
        inputs = draw_batch(2, 910773, n_sites)
        rows = []
        start = time.perf_counter()
        for index in range(len(inputs["family"])):
            result = label_instance(inputs["hopping"][index], inputs["interaction"][index],
                                    inputs["potential"][index])
            rows.append({"family": int(inputs["family"][index]),
                         "seconds": result["seconds"], "cpu_seconds": result["cpu_seconds"],
                         "gaps": result["gaps"].tolist(),
                         "max_residual": float(np.max(result["residuals"]))})
            print(n_sites, index, rows[-1], flush=True)
        report[str(n_sites)] = {"rows": rows, "seconds": time.perf_counter() - start,
                                "projected_256_seconds": sum(row["seconds"] for row in rows) * 32}
        (ROOT / "evaluator/hidden/pilot_report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
