import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"
STRESS = CONCEPT / "adversary/champion1_cold_stress"
RECOVERED = CONCEPT / "adversary/champion_reproduction/recovered"
OUTPUT = STRESS / "full_posterior"


def main():
    OUTPUT.mkdir(exist_ok=False)
    started = time.monotonic()
    queries = json.loads((STRESS / "queries.json").read_text())
    old_queries = json.loads((CONCEPT / "participant/input/queries.json").read_text())
    inputs = [RECOVERED / ("chain_" + str(chain) + ".npz") for chain in range(4)]
    inputs += [STRESS / "queries.json", RECOVERED / "native.py", RECOVERED / "strip.cpp", RECOVERED / "strip.so"]
    record = {"started_at": datetime.now(timezone.utc).isoformat(), "no_refitting": True,
              "all_frozen_draws": True, "no_query_changes": True,
              "source_sha256": {str(path.relative_to(CONCEPT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
              "method": "Complete native posterior prediction of the source-faithful replay; not bitwise original fitted chains."}
    (OUTPUT / "commitment.json").write_text(json.dumps(record, indent=2))
    sys.path.insert(0, str(RECOVERED))
    from infer import Likelihood, load_data
    from native import NativeLikelihood
    configurations, betas, specification = load_data()
    predictor = NativeLikelihood(Likelihood(configurations, betas, specification))
    totals = np.zeros((4, len(queries) + len(old_queries), 64))
    counts = []
    for chain in range(4):
        with np.load(RECOVERED / ("chain_" + str(chain) + ".npz"), allow_pickle=False) as archive:
            parameters = archive["theta"].copy()
        counts.append(len(parameters))
        for values in parameters:
            totals[chain] += predictor.predict(values, queries + old_queries)
        print(json.dumps({"chain": chain, "draws": len(parameters), "seconds": time.monotonic() - started}), flush=True)
    assert sum(counts) == 9600
    predictions = totals.sum(axis=0) / sum(counts)
    predictions /= predictions.sum(axis=1, keepdims=True)
    assert np.isfinite(predictions).all() and np.all(predictions > 0)
    cold = np.ascontiguousarray(predictions[:len(queries)], dtype="<f8")
    np.savez(OUTPUT / "predictions.npz", probabilities=cold, query_ids=np.asarray([query["id"] for query in queries], dtype="<U24"))
    with np.load(RECOVERED / "predictions.npz", allow_pickle=False) as archive:
        replay_difference = float(np.max(np.abs(predictions[len(queries):] - archive["probabilities"])))
    assert replay_difference < 1e-12
    with np.load(STRESS / "true_probabilities.npz", allow_pickle=False) as archive:
        truth = archive["probabilities"].copy()
        assert archive["query_ids"].tolist() == [query["id"] for query in queries]
    divergence = np.maximum(0, np.sum(truth * (np.log(truth) - np.log(cold)), axis=1))
    variation = 0.5 * np.abs(truth - cold).sum(axis=1)
    families = {family: float(divergence[[query["family"] == family for query in queries]].mean()) for family in sorted({query["family"] for query in queries})}
    record.update(completed_at=datetime.now(timezone.utc).isoformat(), runtime_seconds=time.monotonic() - started,
                  posterior_draw_count=sum(counts), original_replay_max_absolute_difference=replay_difference,
                  valid=True, passed=bool(divergence.mean() <= 0.02 and max(families.values()) <= 0.035 and variation.max() <= 0.12),
                  metrics={"mean_forward_kl": float(divergence.mean()), "worst_family_mean_kl": max(families.values()), "max_tv": float(variation.max())},
                  family_mean_kl=families, tv_failures=int(np.sum(variation > 0.12)),
                  per_query=[{"id": query["id"], "kl": float(kl), "tv": float(tv)} for query, kl, tv in zip(queries, divergence, variation)])
    (OUTPUT / "report.json").write_text(json.dumps(record, indent=2))
    print(json.dumps({key: record[key] for key in ("valid", "passed", "metrics", "tv_failures", "runtime_seconds", "original_replay_max_absolute_difference")}))


if __name__ == "__main__":
    main()
