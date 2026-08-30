import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
import json
import numpy as np
from contractor import measure, save_mps
from optimizer import optimize
from benchmark import make_case


requests = []
for sector in ("even", "odd", "any"):
    for mass in (-0.9, -1.3):
        requests.append(make_case("critical_" + sector + str(mass), 22, 14, 6, sector,
                                  mass, 2.0, 0.65, 1.0))
requests.append(make_case("high_cutoff", 22, 14, 12, "even", -2.8, 1.2, 1.85, 1.5))
requests.append(make_case("low_coupling_odd", 22, 14, 12, "odd", -0.1, 1.2, 1.1, 0.06))
request = make_case("two_wells", 22, 14, 12, "any", -2.0, 1.5, 0.9, 1.0)
request["mass2"][8:14] = [0.8] * 6
request["coupling"][10] = 0.06
request["field"] = [0.004] * 11 + [-0.004] * 11
requests.append(request)
results = []
budget = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
for request in requests:
    request["budget_seconds"] = budget
    request["wall_seconds"] = 120.0
    Path("experiments/" + request["case_id"] + ".json").write_text(json.dumps(request))
    start = time.process_time()
    tensors = optimize(request, start - 0.2)
    elapsed = time.process_time() - start
    metrics = measure(tensors, request)
    save_mps("experiments/" + request["case_id"] + str(int(budget)) + ".npz", tensors)
    result = dict(case=request["case_id"], cpu=elapsed, **metrics)
    print(json.dumps(result), flush=True)
    results.append(result)
Path("experiments/stress" + str(int(budget)) + ".json").write_text(json.dumps(results, indent=2))
