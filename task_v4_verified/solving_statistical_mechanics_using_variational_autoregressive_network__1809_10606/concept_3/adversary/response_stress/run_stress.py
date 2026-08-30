"""Frozen-grid response audit; private parameters are used only for exact labels."""

import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


SIDE = Path(__file__).resolve().parent
CONCEPT = SIDE.parents[1]
PUBLIC = CONCEPT / "participant"
PORTFOLIO = SIDE.parent / "public_data_portfolio"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(result)
    return result


def generate_queries(spec, protocol):
    rng = np.random.default_rng(protocol["seed"])
    height = spec["height"]
    visible_by_column = {column: [spin for spin in spec["visible_indices"] if spin // height == column]
                         for column in range(spec["columns"])}
    eligible = [column for column, spins in visible_by_column.items() if len(spins) >= 6]
    order = rng.permutation(eligible).tolist()
    queries = []
    for beta_index, beta in enumerate(protocol["betas"]):
        for family_index, family in enumerate(protocol["families"]):
            for replicate in range(protocol["replicates_per_beta_family"]):
                column = order[(replicate + 2 * beta_index + family_index) % len(order)]
                readout = visible_by_column[column][:6]
                field_indices, field_values, field_column = [], [], None
                if family != "zero_field":
                    if family == "readout_field":
                        field_column = column
                    elif family == "neighbor_field":
                        choices = [other for other in (column - 1, column + 1) if other in visible_by_column]
                        field_column = int(rng.choice(choices))
                    else:
                        choices = [other for other in visible_by_column if abs(other - column) >= 4]
                        field_column = int(rng.choice(choices))
                    count = protocol["field_counts_by_replicate"][replicate]
                    amplitude = protocol["field_amplitudes_by_replicate"][replicate]
                    field_indices = sorted(rng.choice(visible_by_column[field_column], count, replace=False).tolist())
                    sign = int(rng.choice([-1, 1]))
                    alternating = protocol["field_patterns_by_replicate"][replicate] == "alternating"
                    field_values = [float(sign * amplitude * (-1 if alternating and index % 2 else 1))
                                    for index in range(count)]
                queries.append({"id": "stress_%03d" % len(queries), "family": family, "beta": float(beta),
                                "readout": readout, "field_indices": field_indices, "field_values": field_values,
                                "readout_column": column, "field_column": field_column,
                                "field_distance": None if field_column is None else abs(field_column - column),
                                "pattern": "none" if not field_indices else protocol["field_patterns_by_replicate"][replicate]})
    assert len(queries) == 120
    assert len({query["readout_column"] for query in queries}) == len(eligible)
    for query in queries:
        assert len(query["readout"]) == 6 and len(set(query["readout"])) == 6
        assert all(spin in spec["visible_indices"] for spin in query["readout"] + query["field_indices"])
        assert len(query["field_indices"]) <= 4 and all(abs(value) <= 1 for value in query["field_values"])
        assert all(spin // height == query["readout_column"] for spin in query["readout"])
    return queries


def model_predictions(model, queries):
    predictions, zero_predictions, zero_cache = [], [], {}
    for query in queries:
        key = (query["beta"], tuple(query["readout"]))
        if key not in zero_cache:
            zero_cache[key] = model.joint(query["beta"], query["readout"])
        delta = np.zeros_like(model.fields)
        delta.flat[query["field_indices"]] = query["field_values"]
        predictions.append(model.joint(query["beta"], query["readout"], delta))
        zero_predictions.append(zero_cache[key])
    return np.asarray(predictions), np.asarray(zero_predictions)


def importance_weights(query, configurations, lookup):
    energy = np.zeros(configurations.shape[0])
    for spin, amplitude in zip(query["field_indices"], query["field_values"]):
        energy += amplitude * configurations[:, lookup[spin]]
    logarithms = query["beta"] * energy
    weights = np.exp(logarithms - logarithms.max())
    effective_size = weights.sum() ** 2 / np.sum(weights ** 2)
    return weights / weights.mean(), float(effective_size)


def bridge_predictions(frozen, spec, queries, configurations, betas):
    lookup = {spin: index for index, spin in enumerate(spec["visible_indices"])}
    predictions, zero_predictions, supports, extensions = [], [], [], []
    for query in queries:
        zero_query = dict(query, field_indices=[], field_values=[])
        zero_prediction = frozen.empirical_bridge(spec, [zero_query], configurations, betas)[0]
        nonlocal_field = any(spin not in query["readout"] for spin in query["field_indices"])
        weighted_logs, support = [], []
        for condition in range(2):
            weights, effective_size = importance_weights(query, configurations[condition], lookup)
            support.append(effective_size)
            if nonlocal_field:
                observed = configurations[condition][:, [lookup[spin] for spin in query["readout"]]]
                codes = ((observed + 1) // 2) @ (1 << np.arange(6))
                counts = np.bincount(codes, weights=weights, minlength=64) + 0.5
                weighted_logs.append(np.log(counts / counts.sum()))
        if nonlocal_field:
            fraction = (query["beta"] - betas[0]) / (betas[1] - betas[0])
            logits = (1 - fraction) * weighted_logs[0] + fraction * weighted_logs[1]
            prediction = np.exp(logits - logits.max())
            prediction /= prediction.sum()
        else:
            prediction = frozen.empirical_bridge(spec, [query], configurations, betas)[0]
        predictions.append(prediction)
        zero_predictions.append(zero_prediction)
        supports.append(support)
        extensions.append(nonlocal_field)
    return np.asarray(predictions), np.asarray(zero_predictions), np.asarray(supports), extensions


def dense_marginal(model, query):
    states = model.states.astype(float)
    delta = np.zeros_like(model.fields)
    delta.flat[query["field_indices"]] = query["field_values"]
    beta = query["beta"]
    logits = beta * (model.vertical @ (states[:, :-1] * states[:, 1:]).T + (model.fields + delta) @ states.T)
    unary = np.exp(logits - logits.max(axis=1, keepdims=True))
    matrices = []
    for column in range(model.columns - 1):
        interaction = beta * (states * model.horizontal[column]) @ states.T
        matrices.append(np.exp(interaction - interaction.max()))
    forward = [unary[0] / unary[0].sum()]
    for column, matrix in enumerate(matrices):
        weights = (forward[-1] @ matrix) * unary[column + 1]
        forward.append(weights / weights.sum())
    backward = np.ones_like(unary)
    for column in range(model.columns - 2, -1, -1):
        weights = matrices[column] @ (unary[column + 1] * backward[column + 1])
        backward[column] = weights / weights.max()
    selected = query["readout_column"]
    marginal = forward[selected] * backward[selected]
    marginal /= marginal.sum()
    readout_rows = np.asarray(query["readout"]) % model.height
    codes = ((model.states[:, readout_rows] + 1) // 2) @ (1 << np.arange(6))
    result = np.bincount(codes, weights=marginal, minlength=64)
    return result / result.sum()


def metrics(truth, prediction, true_zero, predicted_zero):
    assert np.isfinite(prediction).all() and np.all(prediction > 0)
    assert np.max(abs(prediction.sum(axis=1) - 1)) < 1e-12
    divergence = np.maximum(0.0, np.sum(truth * (np.log(truth) - np.log(prediction)), axis=1))
    variation = 0.5 * np.sum(abs(truth - prediction), axis=1)
    response_error = 0.5 * np.sum(abs((prediction - predicted_zero) - (truth - true_zero)), axis=1)
    return divergence, variation, response_error


def summarize(divergence, variation, response_error, selection):
    selected = np.asarray(selection, dtype=int)
    return {"count": int(len(selected)), "mean_kl": float(divergence[selected].mean()),
            "max_kl": float(divergence[selected].max()), "max_tv": float(variation[selected].max()),
            "mean_tv": float(variation[selected].mean()), "kl_above_0_02": int(np.sum(divergence[selected] > 0.02)),
            "tv_above_0_12": int(np.sum(variation[selected] > 0.12)),
            "mean_response_error_tv": float(response_error[selected].mean())}


def main():
    if (SIDE / "RESULTS.json").exists() or (SIDE / "QUERIES_FROZEN.json").exists():
        raise SystemExit("Already generated/frozen: no score-driven query revisions permitted.")
    started = time.monotonic()
    SIDE.chmod(0o700)
    protocol = json.loads((SIDE / "PREREGISTRATION.json").read_text())
    spec = json.loads((PUBLIC / "input/model.json").read_text())
    queries = generate_queries(spec, protocol)
    write_json(SIDE / "queries.json", queries)
    write_json(SIDE / "QUERIES_FROZEN.json", {
        "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "query_sha256": hashlib.sha256((SIDE / "queries.json").read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((SIDE / "PREREGISTRATION.json").read_bytes()).hexdigest(),
        "material_parameters_opened": False, "stress_scores_observed": False, "cases": len(queries)})
    portfolio_seal = json.loads((PORTFOLIO / "OUTPUTS_FROZEN.json").read_text())
    frozen_files = [PORTFOLIO / "run_portfolio.py"] + [PORTFOLIO / name / "fitted_parameters.npz"
                    for name in ("latent_fit_weak", "latent_fit_strong")]
    for path in frozen_files:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == portfolio_seal["files_sha256"][str(path.relative_to(PORTFOLIO))]
    input_files = [PUBLIC / "input/model.json", PUBLIC / "input/train.npz", PUBLIC / "transfer.py"]
    input_hashes = {str(path.relative_to(CONCEPT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in input_files}
    transfer = module("stress_public_transfer", PUBLIC / "transfer.py")
    frozen = module("stress_frozen_predictors", PORTFOLIO / "run_portfolio.py")
    with np.load(PUBLIC / "input/train.npz", allow_pickle=False) as training:
        configurations, betas = training["visible_spins"], training["betas"]
    models = {}
    for name in ("latent_fit_weak", "latent_fit_strong"):
        with np.load(PORTFOLIO / name / "fitted_parameters.npz", allow_pickle=False) as parameters:
            couplings = np.asarray(spec["edge_signs"]) * parameters["magnitudes"]
            models[name] = transfer.model_from_edges(spec, couplings, parameters["fields"])
    material_path = CONCEPT / "evaluator/hidden/model.npz"
    with np.load(material_path, allow_pickle=False) as material:
        truth_model = transfer.model_from_edges(spec, material["couplings"], material["fields"])
    truth, true_zero = model_predictions(truth_model, queries)
    identifiers = np.asarray([query["id"] for query in queries], dtype="<U24")
    np.savez(SIDE / "true_probabilities.npz", query_ids=identifiers, probabilities=truth, zero_field_probabilities=true_zero)
    (SIDE / "true_probabilities.npz").chmod(0o600)
    assert truth.shape == (120, 64) and np.all(truth > 0) and np.max(abs(truth.sum(axis=1) - 1)) < 1e-12
    predictions, zeros, durations = {}, {}, {}
    for name, model in models.items():
        model_started = time.monotonic()
        predictions[name], zeros[name] = model_predictions(model, queries)
        durations[name] = time.monotonic() - model_started
    model_started = time.monotonic()
    predictions["empirical_log_bridge"], zeros["empirical_log_bridge"], supports, extensions = bridge_predictions(
        frozen, spec, queries, configurations, betas)
    durations["empirical_log_bridge"] = time.monotonic() - model_started
    numerical_residual = 0.0
    for query_index in (0, 23, 47, 71, 95, 119):
        query = queries[query_index]
        for name, model in [("truth", truth_model)] + list(models.items()):
            expected = truth[query_index] if name == "truth" else predictions[name][query_index]
            numerical_residual = max(numerical_residual, float(np.max(abs(dense_marginal(model, query) - expected))))
    assert numerical_residual < 1e-11
    disagreement = 0.5 * np.sum(abs(predictions["latent_fit_weak"] - predictions["latent_fit_strong"]), axis=1)
    true_response = 0.5 * np.sum(abs(truth - true_zero), axis=1)
    outcomes = 2 * ((np.arange(64)[:, None] >> np.arange(6)) & 1) - 1
    majority = (outcomes.sum(axis=1) > 0).astype(float)
    results = {"case_count": len(queries), "seed": protocol["seed"], "betas": protocol["betas"],
               "limits_are_diagnostic_not_live_target_changes": True,
               "empirical_original_recipe_cases": int(np.sum(np.logical_not(extensions))),
               "empirical_nonlocal_extension_cases": int(np.sum(extensions)), "models": {},
               "numerical_checks": {"dense_comparisons": 18, "max_probability_residual": numerical_residual},
               "input_hashes": input_hashes}
    rows = []
    for name, prediction in predictions.items():
        np.savez(SIDE / (name + ".npz"), probabilities=prediction, query_ids=identifiers,
                 zero_field_probabilities=zeros[name])
        divergence, variation, response_error = metrics(truth, prediction, true_zero, zeros[name])
        families = {family: summarize(divergence, variation, response_error,
                                     [index for index, query in enumerate(queries) if query["family"] == family])
                    for family in protocol["families"]}
        temperatures = {str(beta): summarize(divergence, variation, response_error,
                                            [index for index, query in enumerate(queries) if query["beta"] == beta])
                        for beta in protocol["betas"]}
        cells = {str(beta) + "/" + family: summarize(divergence, variation, response_error,
                 [index for index, query in enumerate(queries) if query["beta"] == beta and query["family"] == family])
                 for beta in protocol["betas"] for family in protocol["families"]}
        overall = summarize(divergence, variation, response_error, range(len(queries)))
        overall["worst_family_mean_kl"] = max(family["mean_kl"] for family in families.values())
        overall["meets_original_limits_on_stress_set"] = (overall["mean_kl"] <= 0.02 and
            overall["worst_family_mean_kl"] <= 0.035 and overall["max_tv"] <= 0.12)
        records = []
        for index, query in enumerate(queries):
            record = {"id": query["id"], "family": query["family"], "beta": query["beta"],
                      "kl": float(divergence[index]), "tv": float(variation[index]),
                      "field_response_error_tv": float(response_error[index]),
                      "true_field_response_tv": float(true_response[index]),
                      "weak_strong_disagreement_tv": float(disagreement[index]),
                      "importance_ess_beta_0_65": float(supports[index, 0]),
                      "importance_ess_beta_1_0": float(supports[index, 1]),
                      "true_positive_majority_probability": float(truth[index] @ majority),
                      "predicted_positive_majority_probability": float(prediction[index] @ majority),
                      "empirical_extension_used": bool(extensions[index]) if name == "empirical_log_bridge" else False}
            records.append(record)
            rows.append(dict(model=name, **record))
        top = sorted(records, key=lambda record: record["tv"], reverse=True)[:12]
        results["models"][name] = {"overall": overall, "families": families, "betas": temperatures,
                                  "beta_family": cells, "top_tv_cases": top,
                                  "runtime_seconds": durations[name]}
    write_json(SIDE / "per_query_scores.json", rows)
    results["uncertainty_assessment"] = {
        "max_weak_strong_tv": float(disagreement.max()),
        "cases_disagreement_above_0_12": int(np.sum(disagreement > 0.12)),
        "minimum_importance_ess": float(supports.min()),
        "cases_any_importance_ess_below_128": int(np.sum(np.min(supports, axis=1) < 128)),
        "inference": "Prediction sensitivity to regularization and cold/nonlocal extrapolation can suggest weak identification from finite warm-temperature observations. It is not proof of irreducible finite-data uncertainty; neither estimator has been refitted or bootstrapped.",
        "numerical_error": "Independent dense-transfer comparisons agree to the recorded residual; observed macroscopic failures are not explained by transfer numerical error.",
        "ess_limit": "Importance ESS diagnoses field-tilt support at the two observed ensembles, not temperature-extrapolation support or a posterior confidence interval."}
    for path in frozen_files:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == portfolio_seal["files_sha256"][str(path.relative_to(PORTFOLIO))]
    for path in input_files:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == input_hashes[str(path.relative_to(CONCEPT))]
    results["runtime_seconds"] = time.monotonic() - started
    results["no_refitting_or_scientific_file_changes"] = True
    write_json(SIDE / "RESULTS.json", results)
    lines = ["# Frozen-model response stress audit", "", "120 cases, seed 20260828, preregistered before opening material parameters or observing stress scores.",
             "Betas: 1.3, 1.6, 2, 2.5, 3. Each beta has six cases each of zero field, readout-local field, neighboring-column field, and remote-column field (distance >=4).",
             "At most four visible sites are perturbed, with amplitudes <=1. All eight columns eligible for six-visible-spin readouts are covered.", "",
             "| Frozen predictor | Mean KL | Worst family mean KL | Max TV | Cases KL>.02 | Cases TV>.12 | Meets original limits on stress set |",
             "|---|---:|---:|---:|---:|---:|---|"]
    for name, result in results["models"].items():
        values = result["overall"]
        lines.append("| {} | {:.6f} | {:.6f} | {:.6f} | {} | {} | {} |".format(name, values["mean_kl"], values["worst_family_mean_kl"],
                     values["max_tv"], values["kl_above_0_02"], values["tv_above_0_12"], values["meets_original_limits_on_stress_set"]))
    lines.extend(["", "## Failure families", ""])
    for name, result in results["models"].items():
        lines.append("### " + name)
        for family, values in result["families"].items():
            lines.append("- {}: mean KL {:.6f}, max TV {:.6f}, {} TV failures / {} cases.".format(
                family, values["mean_kl"], values["max_tv"], values["tv_above_0_12"], values["count"]))
        lines.append("")
    lines.extend(["## Interpretation and limits", "",
                  "The original empirical bridge supports only fields within the readout. Its original frozen recipe is used on the 60 zero/local-field cases; the remaining 60 use the preregistered no-fit importance-reweighting extension, not a newly fitted estimator.",
                  "Single-case KL>.02 is diagnostic only: the live task's KL gate is an average. Stress-set scores do not alter any live task or target.",
                  results["uncertainty_assessment"]["inference"], results["uncertainty_assessment"]["numerical_error"],
                  results["uncertainty_assessment"]["ess_limit"], "",
                  "## Reuse", "",
                  "queries.json contains the exact challenge descriptions in fixed order. true_probabilities.npz contains query_ids (<U24), probabilities (120,64), and zero_field_probabilities (120,64).",
                  "Outcome bit k corresponds to readout[k], with bit 0=-1 and bit 1=+1. The field and beta conventions are identical to the live participant schema.",
                  "Saved model predictions use the same shape and ordering. per_query_scores.json and RESULTS.json include beta/family breakdowns and the twelve worst TV cases per model.",
                  "Only this response_stress directory was written. No fresh submission was inspected; no model was refitted. Parameters were opened only to generate exact labels after the query grid was frozen."])
    (SIDE / "REPORT.md").write_text("\n".join(lines) + "\n")
    file_hashes = {str(path.relative_to(SIDE)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(SIDE.rglob("*")) if path.is_file() and path.name != "run.log"}
    write_json(SIDE / "ARTIFACTS_FROZEN.json", {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                               "files_sha256": file_hashes, "refitting": False,
                                               "queries_selected_before_scores": True})
    print(json.dumps({"models": {name: values["overall"] for name, values in results["models"].items()},
                      "uncertainty_assessment": results["uncertainty_assessment"],
                      "numerical_checks": results["numerical_checks"], "runtime_seconds": results["runtime_seconds"],
                      "root": str(SIDE)}, indent=2))


if __name__ == "__main__":
    main()
