import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from predict import fit_markov_maps, load_data, predict as baseline_predict
from evaluate import score_predictions
from simulator import predict, predict_devices
from build_data import FAMILIES, make_records, pack


def summary(predictions, truth, families):
    return {"rmse": float(np.sqrt(np.mean((predictions - truth) ** 2))),
            "family_rmse": {str(family): float(np.sqrt(np.mean((predictions[families == family] - truth[families == family]) ** 2)))
                            for family in np.unique(families)}}


def join_rows(first, second):
    maximum = max(first["gates"].shape[1], second["gates"].shape[1])
    output = {}
    for key in first:
        if key == "gates":
            output[key] = np.concatenate([np.pad(data[key], ((0, 0), (0, maximum - data[key].shape[1])), constant_values=-1)
                                          for data in [first, second]])
        else:
            output[key] = np.concatenate([first[key], second[key]])
    return output


def local_information(parameters, training, development, queries):
    device = 2
    generator = np.random.default_rng(213752)
    train_indices = generator.choice(np.flatnonzero(training["device"] == device), 768, replace=False)
    dev_indices = generator.choice(np.flatnonzero(development["device"] == device), 128, replace=False)
    query_indices = generator.choice(np.flatnonzero(queries["device"] == device), 128, replace=False)
    training_subset = {key: value[train_indices] for key, value in training.items()}
    development_subset = {key: value[dev_indices] for key, value in development.items()}
    observations = join_rows(training_subset, development_subset)
    query_subset = {key: value[query_indices] for key, value in queries.items()}
    parameters = parameters[device]
    observation_truth = predict(parameters, observations)
    jacobian = np.empty((len(observation_truth), 54))
    query_jacobian = np.empty((len(query_indices), 54))
    scales = np.array([0.018] * 15 + [0.008, 0.008, 0.04] + [0.03] * 4 + [0.07] * 2
                      + [0.1] * 2 + [0.009, 0.009, 0.018] * 2 + [0.7]
                      + [1., 0.8, 1.1, 0.5] * 2 + [0.8, 1., 0.7] + [0.001] * 5 + [0.0008] * 5)
    for index in range(54):
        change = np.zeros(54)
        change[index] = scales[index] * 1e-4
        jacobian[:, index] = (predict(parameters + change, observations) - predict(parameters - change, observations)) / 2e-4
        query_jacobian[:, index] = (predict(parameters + change, query_subset) - predict(parameters - change, query_subset)) / 2e-4
    weights = np.sqrt(observations["shots"] / (observation_truth * (1. - observation_truth)))
    left, singular, right = np.linalg.svd(jacobian * weights[:, None], full_matrices=False)
    retained = singular > singular[0] * 1e-8
    covariance = (right[retained].T / singular[retained] ** 2) @ right[retained]
    variance = np.einsum("ni,ij,nj->n", query_jacobian, covariance, query_jacobian)
    return {"device": device, "parameter_count": 54, "labeled_records_used": len(observation_truth),
            "query_records_used": len(query_indices), "scaled_local_jacobian_rank": int(np.sum(retained)),
            "singular_value_range": [float(singular[-1]), float(singular[0])],
            "local_fisher_predictive_rmse_proxy": float(np.sqrt(np.mean(np.maximum(variance, 0.)))),
            "interpretation": "Local sensitivity at true parameters, using only a subset of available labeled observations. This is neither a recovered solution nor a global identifiability or achievability proof; it tests for obvious local information starvation."}


def main():
    started = time.perf_counter()
    training = load_data(ROOT / "participant" / "input" / "train.npz")
    development = load_data(ROOT / "participant" / "input" / "development.npz")
    queries = load_data(ROOT / "participant" / "input" / "queries.npz")
    parameters = load_data(ROOT / "evaluator" / "hidden" / "parameters.npz")["parameters"]
    maps, offsets = fit_markov_maps(training)
    generalization = {}
    for name, data in [("train", training), ("development", development)]:
        truth = load_data(ROOT / "evaluator" / "hidden" / (name + "_truth.npz"))["p1"]
        generalization[name] = summary(baseline_predict(maps, offsets, data), truth, data["family"])
    challenge = pack(make_records(np.random.default_rng(98211283), "test", set(), per_cell=64))
    truth = predict_devices(parameters, challenge)
    baseline = baseline_predict(maps, offsets, challenge)
    counterexamples = summary(baseline, truth, challenge["family"])
    counterexamples["private_challenge_rows"] = len(truth)
    counterexamples["absolute_error_over_0_1"] = int(np.sum(np.abs(baseline - truth) > 0.1))
    counterexamples["largest_absolute_error"] = float(np.max(np.abs(baseline - truth)))
    ablations = {}
    for name, start, stop in [("omit_environment_coupling", 15, 18), ("omit_pulse_memory", 18, 24), ("omit_drift", 26, 32)]:
        altered = parameters.copy()
        altered[:, start:stop] = 0.
        ablations[name] = summary(predict_devices(altered, challenge), truth, challenge["family"])
    result = {"baseline_generalization": generalization, "private_counterexample_search": counterexamples,
              "physical_counterfactuals": ablations,
              "counterfactual_interpretation": "Known-parameter ablations isolate substantive omitted physical mechanisms; they are diagnostics, not fitted challengers or evidence of participant solvability.",
              "ratchet_generations": 0}
    print(json.dumps(result, indent=2), flush=True)
    result["local_information"] = local_information(parameters, training, development, queries)
    result["runtime_seconds"] = time.perf_counter() - started
    (ROOT / "adversary" / "diagnostics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["local_information"], indent=2), flush=True)


if __name__ == "__main__":
    main()
