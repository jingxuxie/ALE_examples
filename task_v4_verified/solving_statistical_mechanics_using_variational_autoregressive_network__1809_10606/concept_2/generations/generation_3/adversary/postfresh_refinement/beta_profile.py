import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import json
from pathlib import Path

import numpy as np

import continue_search as engine

HERE = Path(__file__).resolve().parent
os.sched_setaffinity(0, {engine.CORES[-1]})
records = []
for source in ("seeds/v_2/witness.json", "best/witness.json", "adaptive/best/witness.json"):
    document = json.loads((HERE / source).read_text())
    weights = np.asarray(document["weights"])[engine.verify.LOWER]
    for beta in (1, 1.002, 1.005, 1.01, 1.02, 1.04, 1.08, 1.15, 1.3):
        problem = engine.BASE_PROBLEM(dict(document, beta=beta))
        metrics, derivatives = problem.calculate(weights)
        records.append({"source": source, "beta": beta, "score": engine.score(problem, metrics, derivatives),
                        "variance": float(metrics[1]), "gradient": float(np.max(np.abs(derivatives[0]))),
                        "target_sector": float(problem.target_sector)})
(HERE / "fixed_weights_beta_profile.json").write_text(json.dumps(records, indent=2) + "\n")
for source in sorted({row["source"] for row in records}):
    print(json.dumps(max((row for row in records if row["source"] == source), key=lambda row: row["score"])))
