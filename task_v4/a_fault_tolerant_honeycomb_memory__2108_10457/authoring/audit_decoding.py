import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "authoring" / "deps"))
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import numpy as np
import pymatching
import stim


def main():
    concept = ROOT / "concept_1"
    hidden = concept / "evaluator" / "hidden"
    records = []
    examples = []
    for case in json.loads((hidden / "manifest.json").read_text()):
        request = hidden / "requests" / case["id"]
        syndrome = np.load(request / "syndromes.npy", allow_pickle=False)
        truth = np.load(hidden / "labels" / (case["id"] + ".npy"), allow_pickle=False)
        correlated = np.load(hidden / "baseline" / (case["id"] + ".npy"), allow_pickle=False)
        model = stim.DetectorErrorModel.from_file(request / "model.dem")
        uncorrelated = pymatching.Matching.from_detector_error_model(model).decode_batch(syndrome)[:, 0]
        correlated_wrong = correlated != truth
        uncorrelated_wrong = uncorrelated != truth
        records.append({"id": case["id"], "family": case["family"], "shots": len(truth),
                        "correlated_errors": int(correlated_wrong.sum()),
                        "uncorrelated_errors": int(uncorrelated_wrong.sum()),
                        "correlation_rescues": int((~correlated_wrong & uncorrelated_wrong).sum()),
                        "correlation_regressions": int((correlated_wrong & ~uncorrelated_wrong).sum()),
                        "both_wrong": int((correlated_wrong & uncorrelated_wrong).sum()),
                        "metadata": json.loads((request / "metadata.json").read_text())})
        for index in np.flatnonzero(correlated_wrong & ~uncorrelated_wrong)[:3]:
            examples.append({"case": case["id"], "shot": int(index), "truth": int(truth[index]),
                             "detectors": np.flatnonzero(syndrome[index]).tolist()})
    report = {"records": records, "reproducible_counterexamples": examples,
              "note": "Both-wrong is a label-informed oracle lower bound, NOT an executable solution or achievability proof.",
              "known_passing_solution": False}
    (concept / "adversary" / "correlation_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"shots": sum(record["shots"] for record in records),
                      "baseline_errors": sum(record["correlated_errors"] for record in records),
                      "correlation_regressions": sum(record["correlation_regressions"] for record in records),
                      "both_wrong": sum(record["both_wrong"] for record in records)}, indent=2))


if __name__ == "__main__":
    main()
