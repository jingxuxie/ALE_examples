import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

import numpy as np


SIDE = Path(__file__).resolve().parent
CONCEPT = SIDE.parents[1]
PUBLIC = CONCEPT / "participant"
RECOVERED = SIDE.parent / "champion_reproduction/recovered"
PORTFOLIO = SIDE.parent / "public_data_portfolio"
STRESS = SIDE.parent / "response_stress"


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    (SIDE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name].copy() for name in archive.files}


def check(probabilities):
    assert probabilities.shape[-1] == 64 and np.isfinite(probabilities).all()
    assert np.all(probabilities > 0)
    assert np.max(np.abs(probabilities.sum(axis=-1) - 1)) < 2e-12


def exact(model, queries):
    predictions = []
    for query in queries:
        delta = np.zeros_like(model.fields)
        delta.flat[query["field_indices"]] = query["field_values"]
        predictions.append(model.joint(query["beta"], query["readout"], delta))
    result = np.asarray(predictions)
    check(result)
    return result


def summary(queries, divergence, variation, selected):
    indices = np.asarray(selected)
    family_means = {family: float(divergence[[index for index in indices if queries[index]["family"] == family]].mean())
                    for family in sorted({queries[index]["family"] for index in indices})}
    mean_kl = float(divergence[indices].mean())
    worst_family = max(family_means.values())
    max_tv = float(variation[indices].max())
    return {"count": len(indices), "mean_kl": mean_kl, "worst_family_mean_kl": worst_family,
            "max_tv": max_tv, "family_mean_kl": family_means,
            "max_kl": float(divergence[indices].max()), "mean_tv": float(variation[indices].mean()),
            "queries_tv_above_0_12": int(np.sum(variation[indices] > 0.12)),
            "queries_kl_above_0_02_diagnostic": int(np.sum(divergence[indices] > 0.02)),
            "meets_reference_gates": mean_kl <= 0.02 and worst_family <= 0.035 and max_tv <= 0.12}


def main():
    started = time.monotonic()
    assert not (SIDE / "QUERIES_FROZEN.json").exists(), "No query or score-driven reruns"
    SIDE.chmod(0o700)
    protocol = read(SIDE / "AMENDMENT48.json")
    spec = read(PUBLIC / "input/model.json")
    source_hashes = read(RECOVERED.parent / "REPLAY_STARTED.json")["source_sha256"]
    for name, expected in source_hashes.items():
        assert sha(RECOVERED / name) == expected, name
    weak_path = PORTFOLIO / "latent_fit_weak/fitted_parameters.npz"
    weak_hash = read(PORTFOLIO / "OUTPUTS_FROZEN.json")["files_sha256"]["latent_fit_weak/fitted_parameters.npz"]
    assert sha(weak_path) == weak_hash
    public_hashes = {str(path): sha(path) for path in [PUBLIC / "input/model.json", PUBLIC / "input/train.npz", PUBLIC / "transfer.py"]}
    rng = np.random.default_rng(protocol["seed"])
    patterns = []
    for family, columns in [("zero_field", protocol["zero_field_columns"]), ("readout_field", protocol["local_field_columns"])]:
        for column in columns:
            readout = sorted(spin for spin in spec["visible_indices"] if spin // 8 == column)
            assert len(readout) == 6
            sites = sorted(rng.choice(readout, 4, replace=False).tolist()) if family != "zero_field" else []
            values = rng.permutation([-1.0, -1.0, 1.0, 1.0]).tolist() if sites else []
            patterns.append({"family": family, "readout_column": column, "readout": readout,
                             "field_indices": sites, "field_values": values})
    cold = [dict(pattern, id=f"cold_{beta_index * 12 + pattern_index:03d}", beta=beta)
            for beta_index, beta in enumerate(protocol["betas"]) for pattern_index, pattern in enumerate(patterns)]
    old = [query for query in read(STRESS / "queries.json") if query["family"] in ["zero_field", "readout_field"]]
    queries = old + cold
    assert len(cold) == 48 and len(old) == 60
    assert all(set(query["field_indices"]).issubset(query["readout"]) for query in queries)
    write("queries.json", cold)
    write("supported_stress_queries.json", old)
    write("commands.json", {"utc": now(), "argv": sys.argv, "cwd": str(Path.cwd()),
                            "affinity": sorted(os.sched_getaffinity(0)),
                            "thread_environment": {name: os.environ.get(name) for name in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONDONTWRITEBYTECODE"]}})
    write("QUERIES_FROZEN.json", {"utc": now(), "no_new_truth_read": True, "no_refitting": True,
          "sha256": {name: sha(SIDE / name) for name in ["AMENDMENT48.json", "run48.py", "queries.json", "supported_stress_queries.json"]},
          "source_sha256": source_hashes, "weak_sha256": weak_hash, "public_sha256": public_hashes,
          "chain_sha256": {str(chain): sha(RECOVERED / f"chain_{chain}.npz") for chain in range(4)}})
    print("FROZEN 48 cold and 60 supported old queries; private truth unopened", flush=True)
    sys.path.insert(0, str(RECOVERED))
    from infer import Likelihood, load_data
    from native import NativeLikelihood
    from transfer import model_from_edges
    configurations, betas, public_spec = load_data()
    native = NativeLikelihood(Likelihood(configurations, betas, public_spec))
    draws = []
    native_error = 0.0
    for chain in range(4):
        theta = load(RECOVERED / f"chain_{chain}.npz")["theta"][::8]
        assert theta.shape == (300, 268)
        draws.append(np.asarray([native.predict(values, queries) for values in theta]))
        selected = [cold[index] for index in [0, 6, 11, 36, 42, 47]]
        model = model_from_edges(spec, theta[0, :172] * np.asarray(spec["edge_signs"]), theta[0, 172:])
        native_error = max(native_error, float(np.max(np.abs(exact(model, selected) - native.predict(theta[0], selected)))))
        print(f"predicted chain {chain}; elapsed {time.monotonic()-started:.1f}s", flush=True)
    draws = np.asarray(draws)
    check(draws)
    posterior = draws.mean(axis=(0, 1))
    posterior /= posterior.sum(axis=1, keepdims=True)
    fitted = load(weak_path)
    weak_model = model_from_edges(spec, fitted["magnitudes"] * np.asarray(spec["edge_signs"]), fitted["fields"])
    weak = exact(weak_model, queries)
    assert native_error < 2e-12
    for name, prediction in [("posterior_replay", posterior), ("weakfit", weak)]:
        check(prediction)
        for prefix, selection in [("supported_stress", slice(0, 60)), ("cold", slice(60, 108))]:
            np.savez(SIDE / f"{prefix}_{name}.npz", query_ids=np.asarray([query["id"] for query in queries[selection]]), probabilities=prediction[selection])
    half_tv = 0.5 * np.abs(draws[:, ::2].mean(axis=(0, 1)) - draws[:, 1::2].mean(axis=(0, 1))).sum(axis=1)
    chain_tv = 0.5 * np.abs(draws.mean(axis=1) - posterior).sum(axis=2).max(axis=0)
    interval = np.quantile(draws.reshape(-1, len(queries), 64), [0.025, 0.975], axis=0)
    posterior_tv95 = np.quantile(0.5 * np.abs(draws - posterior).sum(axis=-1), 0.95, axis=(0, 1))
    np.savez(SIDE / "posterior_uncertainty.npz", query_ids=np.asarray([query["id"] for query in queries]),
             lower=interval[0], upper=interval[1], interleaved_half_mean_tv=half_tv, max_chain_mean_tv=chain_tv, posterior_draw_tv_q95=posterior_tv95)
    write("PREDICTIONS_FROZEN.json", {"utc": now(), "no_new_truth_read": True, "no_refitting": True,
          "draw_count": 1200, "native_vs_generic_max_abs": native_error,
          "sha256": {path.name: sha(path) for path in sorted(SIDE.glob("*.npz"))}})
    print("PREDICTIONS FROZEN; computing exact private labels only now", flush=True)
    parameters = load(CONCEPT / "evaluator/hidden/model.npz")
    true_model = model_from_edges(spec, parameters["couplings"], parameters["fields"])
    truth = exact(true_model, cold)
    helper_spec = importlib.util.spec_from_file_location("frozen_stress_helper", STRESS / "run_stress.py")
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    dense = np.asarray([helper.dense_marginal(true_model, query) for query in cold])
    dense_error = float(np.max(np.abs(truth - dense)))
    flipped_model = model_from_edges(spec, parameters["couplings"], -parameters["fields"])
    flipped_queries = [dict(query, field_values=[-value for value in query["field_values"]]) for query in cold]
    flip_error = float(np.max(np.abs(truth - exact(flipped_model, flipped_queries)[:, ::-1])))
    assert dense_error < 2e-12 and flip_error < 2e-12
    np.savez(SIDE / "true_probabilities.npz", query_ids=np.asarray([query["id"] for query in cold]), probabilities=truth)
    old_truth = load(STRESS / "true_probabilities.npz")
    lookup = {str(query_id): index for index, query_id in enumerate(old_truth["query_ids"])}
    truth = np.concatenate([old_truth["probabilities"][[lookup[query["id"]] for query in old]], truth])
    scores = []
    results = {"label": "deterministic-subset posterior REPLAY, not bitwise archived champion", "gates": protocol["gates"],
               "excluded_nonlocal_cases": 60, "nonlocal_cases_are_not_failures": True, "posterior_draw_count": 1200,
               "checks": {"native_vs_generic_max_abs": native_error, "dense48_max_abs": dense_error, "spin_flip48_max_abs": flip_error}, "models": {}}
    for name, prediction in [("posterior_replay", posterior), ("weakfit", weak)]:
        divergence = np.maximum(0.0, np.sum(truth * (np.log(truth) - np.log(prediction)), axis=1))
        variation = 0.5 * np.abs(truth - prediction).sum(axis=1)
        results["models"][name] = {}
        for label, selected in [("supported_stress", list(range(60))), ("cold", list(range(60, 108)))]:
            report = summary(queries, divergence, variation, selected)
            report["by_beta"] = {str(beta): summary(queries, divergence, variation, [index for index in selected if queries[index]["beta"] == beta]) for beta in sorted({queries[index]["beta"] for index in selected})}
            results["models"][name][label] = report
        for index, query in enumerate(queries):
            scores.append({"model": name, "id": query["id"], "beta": query["beta"], "family": query["family"], "column": query["readout_column"],
                           "forward_kl": float(divergence[index]), "tv": float(variation[index]),
                           "posterior_draw_tv_q95": float(posterior_tv95[index]), "interleaved_half_mean_tv": float(half_tv[index]),
                           "max_chain_mean_tv": float(chain_tv[index]),
                           "truth_mass_inside_marginal_95_intervals": float(truth[index][(truth[index] >= interval[0, index]) & (truth[index] <= interval[1, index])].sum())})
    results["approximation_diagnostics"] = {"cold_max_interleaved_half_mean_tv": float(half_tv[60:].max()), "cold_max_chain_mean_tv": float(chain_tv[60:].max()), "cold_max_posterior_draw_tv_q95": float(posterior_tv95[60:].max())}
    for name, expected in source_hashes.items():
        assert sha(RECOVERED / name) == expected
    assert sha(weak_path) == weak_hash
    assert all(sha(Path(path)) == expected for path, expected in public_hashes.items())
    results["source_and_public_inputs_unchanged"] = True
    results["runtime_seconds"] = time.monotonic() - started
    results["completed_utc"] = now()
    write("per_query_scores.json", scores)
    write("RESULTS.json", results)
    write("ARTIFACTS_FROZEN.json", {"utc": now(), "sha256": {path.name: sha(path) for path in sorted(SIDE.iterdir()) if path.is_file() and path.suffix in [".json", ".npz", ".py"] and path.name != "ARTIFACTS_FROZEN.json"}})
    print(json.dumps(results, indent=2), flush=True)


if __name__ == "__main__":
    main()
