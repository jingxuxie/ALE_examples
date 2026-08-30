import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import time
import numpy as np
from contractor import measure
from optimizer import optimize
from benchmark import make_case

rng = np.random.default_rng(95621)
results = []
for index in range(16):
    length = int(rng.choice([8, 12, 18, 22]))
    dimension = int(rng.choice([6, 8, 11, 14]))
    cap = int(rng.choice([6, 7, 8, 10, 12]))
    sector = ("even", "odd", "any")[index % 3]
    request = make_case("random_" + str(index), length, dimension, cap, sector,
                        float(rng.uniform(-1.7, 0.5)), float(rng.uniform(1.2, 2.8)),
                        float(rng.uniform(0.55, 1.85)), float(rng.uniform(0.2, 1.5)))
    if index % 4:
        request["mass2"] = (np.array(request["mass2"]) + rng.uniform(-0.4, 0.4, length)).tolist()
        request["omega"] = rng.uniform(0.55, 1.85, length).tolist()
        request["coupling"][length // 2] = 0.06
    if sector == "any" and index % 2:
        request["field"] = rng.uniform(-0.004, 0.004, length).tolist()
    request["budget_seconds"] = 25.0
    request["wall_seconds"] = 120.0
    Path("experiments/random_" + str(index) + ".json").write_text(json.dumps(request))
    result = dict(index=index, length=length, dimension=dimension, cap=cap, sector=sector)
    for sweeps in (3, 8):
        start = time.process_time()
        tensors = optimize(request, pair_sweeps=sweeps)
        result["cpu" + str(sweeps)] = time.process_time() - start
        result["energy" + str(sweeps)] = measure(tensors, request)["energy"]
    result["difference"] = result["energy3"] - result["energy8"]
    print(json.dumps(result), flush=True)
    results.append(result)
Path("experiments/sweep_check.json").write_text(json.dumps(results, indent=2))
