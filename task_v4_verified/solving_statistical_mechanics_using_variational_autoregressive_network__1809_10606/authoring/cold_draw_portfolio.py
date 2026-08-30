import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"
RECOVERED = CONCEPT / "adversary/champion_reproduction/recovered"
STRESS = CONCEPT / "adversary/champion1_cold_stress"
OUTPUT = CONCEPT / "adversary/cold_draw_portfolio"


def main():
    OUTPUT.mkdir(exist_ok=False)
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    began = time.monotonic()
    indices = np.linspace(0, 2399, 64, dtype=int)
    mixing = (0.25, 0.5, 0.75, 1.0)
    queries = json.loads((STRESS / "queries.json").read_text())
    identifiers = np.asarray([query["id"] for query in queries], dtype="<U24")
    protocol = {"created_at": datetime.now(timezone.utc).isoformat(), "chains": 4,
                "indices_per_chain": indices.tolist(), "posterior_draw_mixing_weights": mixing,
                "candidate_count": 1024, "anchor": "Previously frozen weakly regularized public-data fit",
                "selection": "One global posterior-draw index and one global mixing weight, ranked by maximum normalized error across the three fixed gates; no query-specific label fitting.",
                "privilege": "Final selection uses organizer-only labels. This is an expensive privileged portfolio feasibility witness, NOT a blind validation score or an identifiability theorem.",
                "no_ongoing_fresh_submission_reads": True, "no_refitting": True,
                "source_sha256": {str(path.relative_to(CONCEPT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in [RECOVERED / ("chain_" + str(chain) + ".npz") for chain in range(4)] + [STRESS / "cold_weakfit.npz", STRESS / "queries.json"]}}
    (OUTPUT / "protocol.json").write_text(json.dumps(protocol, indent=2))
    sys.path.insert(0, str(RECOVERED))
    from infer import Likelihood, load_data
    from native import NativeLikelihood
    configurations, betas, specification = load_data()
    predictor = NativeLikelihood(Likelihood(configurations, betas, specification))
    bank, descriptors, parameters = [], [], []
    for chain in range(4):
        with np.load(RECOVERED / ("chain_" + str(chain) + ".npz"), allow_pickle=False) as archive:
            values = archive["theta"][indices].copy()
        for index, parameter in zip(indices, values):
            prediction = predictor.predict(parameter, queries)
            prediction /= prediction.sum(axis=1, keepdims=True)
            bank.append(prediction)
            descriptors.append({"chain": chain, "draw_index": int(index)})
            parameters.append(parameter)
    bank = np.asarray(bank)
    with np.load(STRESS / "cold_weakfit.npz", allow_pickle=False) as archive:
        anchor = archive["probabilities"].copy()
    np.savez(OUTPUT / "frozen_model_bank.npz", probabilities=bank, parameters=np.asarray(parameters), anchor=anchor, query_ids=identifiers)
    (OUTPUT / "predictions_frozen.json").write_text(json.dumps({"frozen_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256((OUTPUT / "frozen_model_bank.npz").read_bytes()).hexdigest(), "no_candidate_selection_yet": True}, indent=2))
    with np.load(STRESS / "true_probabilities.npz", allow_pickle=False) as archive:
        truth = archive["probabilities"].copy()
    rows, best, best_ratio, best_prediction = [], None, float("inf"), None
    for index, prediction in enumerate(bank):
        for weight in mixing:
            proposal = weight * prediction + (1 - weight) * anchor
            proposal /= proposal.sum(axis=1, keepdims=True)
            divergence = np.maximum(0, np.sum(truth * (np.log(truth) - np.log(proposal)), axis=1))
            variation = 0.5 * np.abs(truth - proposal).sum(axis=1)
            family_means = {family: float(divergence[[query["family"] == family for query in queries]].mean()) for family in ("zero_field", "readout_field")}
            metrics = {"mean_forward_kl": float(divergence.mean()), "worst_family_mean_kl": max(family_means.values()), "max_tv": float(variation.max())}
            ratio = max(metrics["mean_forward_kl"] / 0.02, metrics["worst_family_mean_kl"] / 0.035, metrics["max_tv"] / 0.12)
            record = dict(descriptors[index], weight=weight, metrics=metrics, gate_ratio=ratio, passed=ratio <= 1)
            rows.append(record)
            if ratio < best_ratio:
                best, best_ratio, best_prediction = record, ratio, proposal.copy()
    target = OUTPUT / "best"
    target.mkdir()
    np.savez(target / "predictions.npz", probabilities=np.ascontiguousarray(best_prediction, dtype="<f8"), query_ids=identifiers)
    (OUTPUT / "scores.json").write_text(json.dumps(rows, indent=2))
    report = {"passed": bool(best_ratio <= 1), "best": best, "passing_candidates": sum(row["passed"] for row in rows),
              "candidate_count": len(rows), "runtime_seconds": time.monotonic() - began,
              "cpu_affinity": sorted(os.sched_getaffinity(0)), "address_space_limit": 8 * 1024**3,
              "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "privilege": protocol["privilege"],
              "upstream_public_training_seconds": 438.6284170279978,
              "note": "The upstream public-data posterior was already frozen. Labels select a global candidate; no probability entry is copied or fitted directly to a label."}
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
