"""Select a nontrivial regressor on validation and write static predictions."""

import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
try:
    from sklearn.experimental import enable_hist_gradient_boosting
except ImportError:
    pass
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from threadpoolctl import threadpool_limits

from features import featurize, metrics


def candidates():
    return {
        "extra_trees": ExtraTreesRegressor(n_estimators=700, max_features=.90,
                                            min_samples_leaf=1, random_state=1041, n_jobs=2),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=600, max_leaf_nodes=15, learning_rate=.045,
            l2_regularization=1.0, early_stopping=False, random_state=1042),
        "quadratic_ridge": make_pipeline(StandardScaler(),
                                          PolynomialFeatures(degree=2, include_bias=False),
                                          StandardScaler(),
                                          RidgeCV(alphas=np.logspace(-3, 3, 13))),
    }


def model_input(name, features):
    return features[:, :13] if name == "quadratic_ridge" else features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    parser.add_argument("--output", type=Path, default=Path("predictions.npz"))
    parser.add_argument("--report", type=Path, default=Path("baseline_report.json"))
    args = parser.parse_args()
    started = time.perf_counter()
    with np.load(args.data / "train.npz", allow_pickle=False) as archive:
        train = dict(archive)
    with np.load(args.data / "validation.npz", allow_pickle=False) as archive:
        validation = dict(archive)
    with np.load(args.data / "test_features.npz", allow_pickle=False) as archive:
        test = dict(archive)
    with threadpool_limits(limits=1):
        train_features, train_scale = featurize(train)
        validation_features, validation_scale = featurize(validation)
        test_features, test_scale = featurize(test)
        reports = {}
        models = candidates()
        for name, model in models.items():
            model.fit(model_input(name, train_features), train["tail"] / train_scale)
            prediction = model.predict(model_input(name, validation_features)) * validation_scale
            reports[name] = metrics(validation["tail"], prediction, validation["family"])
            print(name, json.dumps(reports[name]), flush=True)
        selected = min(reports, key=lambda name: reports[name]["core_score"])
        model = models[selected]
        combined_features = np.concatenate((train_features, validation_features))
        combined_target = np.concatenate((train["tail"] / train_scale,
                                          validation["tail"] / validation_scale))
        model.fit(model_input(selected, combined_features), combined_target)
        prediction = model.predict(model_input(selected, test_features)) * test_scale
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, ids=test["ids"], tail=prediction.astype(np.float64))
    report = {"selected": selected, "selection": "minimum validation RMSE; refit train+validation",
              "validation": reports, "runtime_seconds": time.perf_counter() - started,
              "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
              "seed_role": "public model random states only; not dataset seeds",
              "prediction_rows": len(prediction)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
