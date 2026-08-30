"""Seal the validation-selected baseline without changing preregistered limits."""

import json
from datetime import datetime, timezone

import numpy as np

from evaluate import ROOT, digest, read_prediction, scores


def main():
    hidden = ROOT / "evaluator/hidden"
    destination = hidden / "target_freeze.json"
    if destination.exists():
        raise RuntimeError("Already sealed; targets and baseline are immutable")
    criteria = json.loads((ROOT / "evaluator/criteria.json").read_text())
    generation = json.loads((hidden / "generation_freeze.json").read_text())
    if digest(ROOT / "evaluator/criteria.json") != generation["criteria_sha256"]:
        raise RuntimeError("Pre-generation target changed")
    if digest(ROOT / "participant/input/workspace/generator.py") != generation["generator_sha256"]:
        raise RuntimeError("Pre-generation generator changed")
    compatibility = json.loads((hidden / "baseline_compatibility_amendment.json").read_text())
    if (compatibility["old_sha256"] != generation["baseline_sha256"] or
            compatibility["new_sha256"] != digest(ROOT / "participant/input/workspace/baseline/predict.py")):
        raise RuntimeError("Unrecorded baseline change")
    with np.load(hidden / "test_truth.npz", allow_pickle=False) as archive:
        ids, target, family = archive["ids"], archive["tail"], archive["family"]
    prediction = read_prediction(ROOT / "attempts/baseline/predictions.npz", ids,
                                 criteria["maximum_submission_bytes"])
    np.savez_compressed(hidden / "baseline_predictions.npz", ids=ids, tail=prediction)
    baseline = scores(target, prediction, family)
    relative_paths = ["evaluator/criteria.json", "evaluator/evaluate.py",
                      "evaluator/hidden/generation_freeze.json",
                      "evaluator/hidden/baseline_compatibility_amendment.json",
                      "evaluator/hidden/test_truth.npz", "evaluator/hidden/baseline_predictions.npz",
                      "participant/input/workspace/generator.py",
                      "participant/input/workspace/baseline/predict.py",
                      "participant/input/workspace/baseline/features.py",
                      "participant/input/workspace/data/train.npz",
                      "participant/input/workspace/data/validation.npz",
                      "participant/input/workspace/data/test_features.npz"]
    freeze = {"version": criteria["version"], "sealed_utc": datetime.now(timezone.utc).isoformat(),
              "targets_frozen_utc": generation["created_utc"], "criteria": criteria,
              "baseline_hidden_scores": baseline,
              "sha256": {relative: digest(ROOT / relative) for relative in relative_paths},
              "fresh_agents_launched": False,
              "selection_policy": "validation only; hidden evaluation occurs once after selection",
              "known_passing_solution": "unknown", "possible_open": True}
    destination.write_text(json.dumps(freeze, indent=2) + "\n")
    public = {"version": criteria["version"], "baseline_core_score": baseline["core_score"],
              "baseline_worst_family_score": baseline["worst_family_score"],
              "effective_core_limit": min(criteria["absolute_core_limit"], criteria["relative_core_limit"] * baseline["core_score"]),
              "effective_worst_family_limit": min(criteria["absolute_worst_family_limit"], criteria["relative_worst_family_limit"] * baseline["worst_family_score"]),
              "lower_is_better": True, "unit": "synthetic_Eh"}
    (ROOT / "participant/input/workspace/data/baseline_reference.json").write_text(json.dumps(public, indent=2) + "\n")
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
