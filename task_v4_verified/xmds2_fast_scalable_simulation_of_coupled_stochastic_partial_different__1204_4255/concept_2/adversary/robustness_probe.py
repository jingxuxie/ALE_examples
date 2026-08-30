import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from search_api import assess, screen


base = json.loads((ROOT / "adversary" / "privileged_candidate.json").read_text())
started = time.monotonic()
records = []
best = None
best_score = 0
for factor in (0.99, 0.98, 0.97, 0.96):
    parameters = dict(base["parameters"])
    parameters["duration"] *= factor
    reports = screen(parameters, True)
    gap = min(report["observable_gap"] for report in reports.values())
    certificate = max(report["certificate"] for report in reports.values())
    tail = max(report["tail_mass"] for report in reports.values())
    score = min(1, gap / 0.3) * min(1, 0.0001 / certificate, 0.02 / tail)
    records.append({"duration_factor": factor, "screening_gap": gap, "certificate": certificate, "tail": tail, "score": score})
    print(json.dumps(records[-1]), flush=True)
    if score > best_score:
        best_score, best = score, parameters
if best is not None:
    (ROOT / "adversary" / "robust_candidate.json").write_text(json.dumps({"schema_version": 1, "parameters": best}, indent=2) + "\n")
(ROOT / "adversary" / "robustness_probe.json").write_text(json.dumps({"records": records, "runtime_seconds": time.monotonic() - started}, indent=2) + "\n")
