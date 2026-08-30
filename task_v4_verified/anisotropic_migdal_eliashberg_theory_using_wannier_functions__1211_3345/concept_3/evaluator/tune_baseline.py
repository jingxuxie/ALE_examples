"""Validation-only bounded ridge sweep for the fixed v2 distribution."""

import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
import solve as baseline
from evaluate import score, target_configuration


def main():
    public = ROOT / "participant" / "input"
    data = {}
    for split in ("train", "validation"):
        with np.load(public / f"{split}_features.npz", allow_pickle=False) as archive:
            data[split] = {key: archive[key] for key in archive.files}
        with np.load(public / f"{split}_labels.npz", allow_pickle=False) as archive:
            data[split].update({key: archive[key] for key in archive.files})
    configuration, target_hash = target_configuration()
    records = []
    for strength in (.25, 1., 4., 12., 24., 64.):
        prediction = np.zeros_like(data["validation"]["spectral_mass"])
        for bands in (2, 3):
            train_mask = data["train"]["sheet_count"] == bands
            validation_mask = data["validation"]["sheet_count"] == bands
            raw = baseline.fit_predict(data["train"]["observed"][train_mask],
                                       data["train"]["spectral_mass"][train_mask, :bands].reshape(train_mask.sum(), -1),
                                       data["validation"]["observed"][validation_mask],
                                       np.median(data["train"]["sigma"][train_mask], axis=0), .4, strength)
            prediction[validation_mask, :bands] = baseline.simplex(raw.reshape(validation_mask.sum(), bands, 14))
        metrics = score(prediction, data["validation"]["spectral_mass"], data["validation"]["family"], configuration)
        objective = max(metrics["core"], metrics["worst_family"] / 1.25, metrics["case_p90"] / 1.75)
        records.append(dict(ridge_strength=strength, selection_objective=objective, score=metrics))
        print(strength, metrics["core"], metrics["worst_family"], flush=True)
    selected = min(records, key=lambda record: record["selection_objective"])
    report = dict(target_sha256=target_hash, selection="min max(core, worst/1.25, p90/1.75) on public validation only",
                  selected=selected, records=records, hidden_labels_accessed=False)
    (ROOT / "evaluator" / "hidden" / "baseline_tuning_v2.json").write_text(json.dumps(report, indent=2) + "\n")
    print("SELECTED", selected["ridge_strength"], flush=True)


if __name__ == "__main__":
    main()
