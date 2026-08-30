import argparse
import gzip
import json
import os
from pathlib import Path
import pickle
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "4"

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

from descriptors import feature_matrix
from predict import read_cases


def metrics(cases, predictions):
    residuals = predictions - np.array([case["f"] for case in cases])
    result = {"overall_rmse": float(np.sqrt(np.mean(residuals ** 2))), "by_family": {}, "by_length": {}}
    for family in sorted({case["family"] for case in cases}):
        selected = [index for index, case in enumerate(cases) if case["family"] == family]
        result["by_family"][family] = float(np.sqrt(np.mean(residuals[selected] ** 2)))
    for length in sorted({case["L"] for case in cases}):
        selected = [index for index, case in enumerate(cases) if case["L"] == length]
        result["by_length"][str(length)] = float(np.sqrt(np.mean(residuals[selected] ** 2)))
    result["worst_family_rmse"] = max(result["by_family"].values())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default=str(Path(__file__).parent.parent / "input" / "train.jsonl"))
    parser.add_argument("--validation", default=str(Path(__file__).parent.parent / "input" / "validation.jsonl"))
    parser.add_argument("--model", default=str(Path(__file__).with_name("baseline.pkl.gz")))
    parser.add_argument("--metrics")
    parser.add_argument("--trees", type=int, default=200)
    args = parser.parse_args()
    training = read_cases(args.train)
    validation = read_cases(args.validation)
    started = time.monotonic()
    features = feature_matrix(training)
    model = ExtraTreesRegressor(n_estimators=args.trees, max_features=0.85,
                               min_samples_leaf=1, n_jobs=4, random_state=10101992)
    model.fit(features, [case["f"] for case in training])
    with gzip.open(args.model, "wb", compresslevel=3) as stream:
        pickle.dump(model, stream, protocol=4)
    fit_seconds = time.monotonic() - started
    started = time.monotonic()
    predictions = model.predict(feature_matrix(validation))
    result = metrics(validation, predictions)
    result.update({"training_records": len(training), "validation_records": len(validation),
                   "descriptor_count": features.shape[1], "trees": args.trees,
                   "fit_seconds": fit_seconds,
                   "warm_batch_seconds": time.monotonic() - started,
                   "training_split_only": True})
    print(json.dumps(result, indent=2))
    if args.metrics:
        Path(args.metrics).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
