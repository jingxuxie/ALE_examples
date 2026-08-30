"""Public-validation-selected kernel ridge baseline; never opens test assets."""

import argparse
import json
import os
from pathlib import Path
import shutil
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
from sklearn.kernel_ridge import KernelRidge
from sklearn.preprocessing import StandardScaler

from features import features, predict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).resolve().parents[1] / "input")
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    started = time.perf_counter()
    with np.load(arguments.input_dir / "train.npz", allow_pickle=False) as archive:
        training = dict(archive)
    with np.load(arguments.input_dir / "validation.npz", allow_pickle=False) as archive:
        validation = dict(archive)
    train_features = features(training)
    validation_features = features(validation)
    artifact = {}
    selections = []
    for family in range(4):
        for size in (8, 10):
            train_mask = (training["family"] == family) & (training["n_sites"] == size)
            validation_mask = (validation["family"] == family) & (validation["n_sites"] == size)
            scaler = StandardScaler().fit(train_features[train_mask])
            scaler.scale_ = np.maximum(scaler.scale_, 1e-8)
            fitted = scaler.transform(train_features[train_mask])
            heldout = scaler.transform(validation_features[validation_mask])
            targets = training["gaps"][train_mask]
            mean = targets.mean(axis=0)
            best_loss = float("inf")
            best = None
            for gamma in (0.001, 0.003, 0.01, 0.03):
                for alpha in (0.0001, 0.001, 0.01, 0.1):
                    regressor = KernelRidge(alpha=alpha, kernel="rbf", gamma=gamma)
                    regressor.fit(fitted, targets - mean)
                    predicted = regressor.predict(heldout) + mean
                    loss = float(np.mean(((predicted - validation["gaps"][validation_mask]) / [0.03, 0.02]) ** 2))
                    if loss < best_loss:
                        best_loss = loss
                        best = (gamma, alpha, regressor.dual_coef_)
            prefix = f"f{family}_n{size}_"
            artifact.update({prefix + "offset": scaler.mean_, prefix + "scale": scaler.scale_,
                prefix + "train": fitted, prefix + "gamma": best[0],
                prefix + "dual": best[2], prefix + "mean": mean})
            selections.append({"family": family, "n_sites": size, "gamma": best[0],
                               "alpha": best[1], "validation_loss": best_loss})
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(arguments.output_dir / "model.npz", **artifact)
    for filename in ("solver.py", "features.py"):
        source = Path(__file__).resolve().with_name(filename)
        destination = arguments.output_dir.resolve() / filename
        if source != destination:
            shutil.copyfile(source, destination)
    validation_predictions = predict(validation, artifact)
    residuals = validation_predictions - validation["gaps"]
    report = {"method": "per-family-size invariant spectral RBF kernel ridge",
              "training_wall_seconds": time.perf_counter() - started, "selections": selections,
              "validation_charge_rmse": float(np.sqrt(np.mean(residuals[:, 0] ** 2))),
              "validation_spin_rmse": float(np.sqrt(np.mean(residuals[:, 1] ** 2))),
              "training_examples": len(training["gaps"]), "uses_validation_for_selection": True,
              "uses_hidden_test": False}
    (arguments.output_dir / "training_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
