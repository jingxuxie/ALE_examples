import json
from pathlib import Path
import sys
import time
import warnings

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "participant/input/runtime"), str(ROOT / "participant/input")]

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csc_matrix, eye, hstack
from models import SPECS, load_model


def main():
    output = ROOT / "attempts/private_map_pilot.json"
    records = []
    for spec in SPECS:
        model = load_model(ROOT / "participant/input/cases" / spec["case_id"])
        with np.load(ROOT / "evaluator/hidden/pilot" / (spec["case_id"] + ".npz"), allow_pickle=False) as data:
            syndromes, labels, baseline = data["syndromes"][:32], data["labels"][:32], data["baseline"][:32]
        detectors, mechanisms = model["detector_matrix"].shape
        matrix = hstack([csc_matrix(model["detector_matrix"], dtype=float), -2 * eye(detectors, format="csc")], format="csc")
        objective = np.r_[np.log((1 - model["probabilities"]) / model["probabilities"]), np.zeros(detectors)]
        upper = np.r_[np.ones(mechanisms), model["detector_matrix"].sum(axis=1) // 2]
        candidate = baseline.copy()
        outcomes = []
        started = time.process_time()
        for index, syndrome in enumerate(syndromes):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                result = milp(objective, integrality=np.ones(mechanisms + detectors), bounds=Bounds(np.zeros_like(upper), upper),
                              constraints=LinearConstraint(matrix, syndrome, syndrome),
                              options={"time_limit": 1.0, "mip_rel_gap": 0.01, "threads": 1})
            valid = False
            if result.x is not None:
                errors = np.rint(result.x[:mechanisms]).astype(np.uint8)
                valid = bool(np.array_equal((model["detector_matrix"] @ errors) % 2, syndrome))
                if valid:
                    candidate[index] = (model["observable_matrix"] @ errors) % 2
            outcomes.append(dict(status=int(result.status), feasible=valid, gap=float(result.mip_gap) if valid else None))
        baseline_wrong = np.any(baseline != labels, axis=1)
        candidate_wrong = np.any(candidate != labels, axis=1)
        records.append(dict(case_id=spec["case_id"], shots=len(labels), baseline_failures=int(baseline_wrong.sum()),
                            candidate_failures=int(candidate_wrong.sum()), corrected=int((baseline_wrong & ~candidate_wrong).sum()),
                            spoiled=int((~baseline_wrong & candidate_wrong).sum()), cpu_seconds=time.process_time() - started,
                            outcomes=outcomes))
        report = dict(kind="independent_builder_pilot_not_challenge", method="bounded-time physical-MAP MILP; baseline fallback when no feasible incumbent",
                      caveat="Not logical Bayes and not a full-suite/runtime-qualified passing reference. Tiny pilot intervals are broad.", cases=records)
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: value for key, value in records[-1].items() if key != "outcomes"}), flush=True)


if __name__ == "__main__":
    main()
