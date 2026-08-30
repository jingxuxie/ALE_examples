"""Public-data-only fitting. This program never imports or reads an evaluator."""

import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

import numpy as np


SIDE = Path(__file__).resolve().parent
PUBLIC = SIDE.parents[1] / "participant"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def public_module():
    specification = importlib.util.spec_from_file_location("public_strip_transfer", PUBLIC / "transfer.py")
    result = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(result)
    return result


def save_predictions(name, probabilities, identifiers, metadata, parameters=None):
    directory = SIDE / name
    directory.mkdir(exist_ok=True)
    probabilities = np.maximum(np.asarray(probabilities, dtype="<f8"), 1e-15)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    assert probabilities.shape == (24, 64) and np.isfinite(probabilities).all()
    np.savez(directory / "predictions.npz", probabilities=probabilities, query_ids=identifiers)
    if parameters is not None:
        np.savez(directory / "fitted_parameters.npz", magnitudes=parameters[0], fields=parameters[1])
    write_json(directory / "fit_report.json", metadata)


def model_predictions(transfer, spec, queries, magnitudes, fields):
    model = transfer.model_from_edges(spec, np.asarray(spec["edge_signs"]) * magnitudes, fields)
    output = []
    for query in queries:
        delta = np.zeros((spec["columns"], spec["height"]))
        delta.flat[query["field_indices"]] = query["field_values"]
        output.append(model.joint(query["beta"], query["readout"], delta))
    return np.asarray(output)


def empirical_bridge(spec, queries, configurations, betas):
    lookup = {spin: index for index, spin in enumerate(spec["visible_indices"])}
    outcome_spins = 2 * ((np.arange(64)[:, None] >> np.arange(6)) & 1) - 1
    output = []
    for query in queries:
        log_histograms = []
        for condition in range(2):
            observed = configurations[condition][:, [lookup[spin] for spin in query["readout"]]]
            codes = ((observed + 1) // 2) @ (1 << np.arange(6))
            counts = np.bincount(codes, minlength=64).astype(float) + 0.5
            log_histograms.append(np.log(counts / counts.sum()))
        fraction = (query["beta"] - betas[0]) / (betas[1] - betas[0])
        logits = (1 - fraction) * log_histograms[0] + fraction * log_histograms[1]
        for spin, amplitude in zip(query["field_indices"], query["field_values"]):
            logits += query["beta"] * amplitude * outcome_spins[:, query["readout"].index(spin)]
        weights = np.exp(logits - logits.max())
        output.append(weights / weights.sum())
    return np.asarray(output)


class FitTimeout(Exception):
    pass


class LatentLikelihood:
    def __init__(self, torch, spec, configurations, betas):
        self.torch = torch
        self.spec = spec
        self.height, self.columns = spec["height"], spec["columns"]
        self.edge_count = len(spec["edges"])
        self.vertical_count = self.columns * (self.height - 1)
        self.signs = torch.tensor(spec["edge_signs"], dtype=torch.float64)
        states = 2 * ((np.arange(1 << self.height)[:, None] >> np.arange(self.height)) & 1) - 1
        self.states = torch.tensor(states, dtype=torch.float64)
        self.vertical_features = self.states[:, :-1] * self.states[:, 1:]
        self.betas = [float(value) for value in betas]
        self.observed_states = []
        visible = spec["visible_indices"]
        hidden = set(spec["hidden_indices"])
        for condition in range(2):
            base = np.zeros((configurations.shape[1], self.columns * self.height))
            base[:, visible] = configurations[condition]
            base = base.reshape(-1, self.columns, self.height)
            condition_states = []
            for column in range(self.columns):
                hidden_rows = [row for row in range(self.height) if column * self.height + row in hidden]
                hidden_states = 2 * ((np.arange(1 << len(hidden_rows))[:, None] >> np.arange(len(hidden_rows))) & 1) - 1
                compatible = np.repeat(base[:, column, None, :], len(hidden_states), axis=1)
                compatible[:, :, hidden_rows] = hidden_states[None, :, :]
                condition_states.append(torch.tensor(compatible, dtype=torch.float64))
            self.observed_states.append(condition_states)
        self.observed_vertical = [[states[:, :, :-1] * states[:, :, 1:] for states in condition]
                                  for condition in self.observed_states]
        magnitude_bounds = spec["parameter_prior"]["coupling_magnitudes"]["bounds"]
        field_bounds = spec["parameter_prior"]["fields"]["bounds"]
        self.midpoint = np.r_[np.full(self.edge_count, np.mean(magnitude_bounds)),
                              np.full(self.columns * self.height, np.mean(field_bounds))]
        self.scale = np.r_[np.full(self.edge_count, np.ptp(magnitude_bounds) / 2),
                           np.full(self.columns * self.height, np.ptp(field_bounds) / 2)]
        self.midpoint_tensor = torch.tensor(self.midpoint, dtype=torch.float64)
        self.scale_tensor = torch.tensor(self.scale, dtype=torch.float64)
        self.bounds = [tuple(magnitude_bounds)] * self.edge_count + [tuple(field_bounds)] * (self.columns * self.height)

    def unpack(self, parameters):
        couplings = parameters[:self.edge_count] * self.signs
        vertical = couplings[:self.vertical_count].reshape(self.columns, self.height - 1)
        horizontal = couplings[self.vertical_count:].reshape(self.columns - 1, self.height)
        fields = parameters[self.edge_count:].reshape(self.columns, self.height)
        return vertical, horizontal, fields

    def partitions(self, parameters, condition):
        torch = self.torch
        beta = self.betas[condition]
        vertical, horizontal, fields = self.unpack(parameters)
        unary = beta * (vertical @ self.vertical_features.T + fields @ self.states.T)
        forward = unary[0]
        for column in range(1, self.columns):
            interaction = beta * (self.states * horizontal[column - 1]) @ self.states.T
            forward = unary[column] + torch.logsumexp(forward[:, None] + interaction, dim=0)
        log_partition = torch.logsumexp(forward, dim=0)
        compatible = self.observed_states[condition]
        within_column = self.observed_vertical[condition]
        observed_unary = [beta * ((within_column[column] * vertical[column]).sum(dim=2) +
                                  (compatible[column] * fields[column]).sum(dim=2))
                          for column in range(self.columns)]
        observed_forward = observed_unary[0]
        for column in range(1, self.columns):
            interaction = beta * torch.bmm(compatible[column - 1] * horizontal[column - 1],
                                           compatible[column].transpose(1, 2))
            observed_forward = observed_unary[column] + torch.logsumexp(observed_forward[:, :, None] + interaction, dim=1)
        return log_partition, torch.logsumexp(observed_forward, dim=1)

    def objective(self, values, regularization, gradient=True):
        torch = self.torch
        parameters = torch.tensor(values, dtype=torch.float64, requires_grad=gradient)
        losses = []
        for condition in range(2):
            global_partition, observed_partition = self.partitions(parameters, condition)
            losses.append(global_partition - observed_partition.mean())
        likelihood = 0.5 * (losses[0] + losses[1])
        penalty = 0.5 * regularization * (((parameters - self.midpoint_tensor) / self.scale_tensor) ** 2).sum()
        loss = likelihood + penalty
        if gradient:
            loss.backward()
            derivatives = parameters.grad.detach().numpy().copy()
            assert np.isfinite(derivatives).all()
            return float(loss.detach()), derivatives, float(likelihood.detach())
        return float(loss.detach())


def check_implementation(torch, transfer, spec, configurations, betas):
    small = LatentLikelihood(torch, spec, configurations[:, :8], betas)
    values = small.midpoint.copy()
    loss, derivative, _ = small.objective(values, 0.001)
    maximum_gradient_error = 0.0
    for index in (0, 5, small.vertical_count, small.edge_count - 1, small.edge_count, len(values) - 1):
        increment = 1e-5
        positive, negative = values.copy(), values.copy()
        positive[index] += increment
        negative[index] -= increment
        numeric = (small.objective(positive, 0.001, False) - small.objective(negative, 0.001, False)) / (2 * increment)
        maximum_gradient_error = max(maximum_gradient_error, abs(numeric - derivative[index]))
    model = transfer.model_from_edges(spec, values[:small.edge_count] * np.asarray(spec["edge_signs"]), values[small.edge_count:])
    maximum_partition_error = 0.0
    with torch.no_grad():
        tensor = torch.tensor(values, dtype=torch.float64)
        for condition, beta in enumerate(betas):
            unconditional, conditional = small.partitions(tensor, condition)
            maximum_partition_error = max(maximum_partition_error, abs(float(unconditional) - model.log_partition(float(beta))))
            for sample in range(3):
                evidence = np.zeros(spec["n_spins"], dtype=np.int8)
                evidence[spec["visible_indices"]] = configurations[condition, sample]
                expected = model.log_partition(float(beta), evidence=evidence.reshape(spec["columns"], spec["height"]))
                maximum_partition_error = max(maximum_partition_error, abs(expected - float(conditional[sample])))
    assert maximum_gradient_error < 1e-7 and maximum_partition_error < 1e-10
    return {"finite_difference_max_gradient_error": maximum_gradient_error,
            "public_simulator_max_partition_error": maximum_partition_error,
            "initial_small_batch_objective": loss, "hidden_references_used": False}


def fit_variant(engine, variant):
    from scipy.optimize import minimize
    started = time.monotonic()
    track = {"best_loss": float("inf"), "best": engine.midpoint.copy(), "evaluations": 0, "trace": []}
    def objective(values):
        if time.monotonic() - started > variant["max_fit_seconds"]:
            raise FitTimeout()
        loss, gradient, nll = engine.objective(values, variant["regularization"])
        track["evaluations"] += 1
        if loss < track["best_loss"]:
            track["best_loss"], track["best"], track["best_nll"] = loss, values.copy(), nll
        if track["evaluations"] == 1 or track["evaluations"] % 20 == 0:
            record = {"evaluation": track["evaluations"], "objective": loss, "nll": nll,
                      "seconds": time.monotonic() - started}
            track["trace"].append(record)
            print(json.dumps({"variant": variant["name"], **record}), flush=True)
        return loss, gradient
    try:
        result = minimize(objective, engine.midpoint.copy(), jac=True, method="L-BFGS-B", bounds=engine.bounds,
                          options={"maxiter": variant["max_iterations"], "maxfun": variant["max_function_evaluations"],
                                   "ftol": 1e-10, "gtol": 1e-5, "maxls": 20, "maxcor": 15})
        stop_reason = str(result.message)
        iterations = int(result.nit)
    except FitTimeout:
        stop_reason, iterations = "predeclared wall-time cap", None
    if not np.isfinite(track["best_loss"]):
        raise RuntimeError("no completed objective evaluation")
    report = {"algorithm": variant, "runtime_seconds": time.monotonic() - started,
              "objective_evaluations": track["evaluations"], "optimizer_iterations": iterations,
              "stop_reason": stop_reason, "best_regularized_objective": track["best_loss"],
              "best_mean_negative_log_likelihood": track["best_nll"], "trace": track["trace"],
              "training_configurations": 16384, "initialization": "public prior midpoint",
              "hidden_scores_used": False}
    return track["best"], report


def run():
    if (SIDE / "OUTPUTS_FROZEN.json").exists():
        raise SystemExit("Outputs already frozen; no refitting is permitted.")
    started = time.monotonic()
    protocol = json.loads((SIDE / "PREREGISTRATION.json").read_text())
    public_paths = [PUBLIC / "input" / name for name in ("model.json", "train.npz", "queries.json")]
    public_paths.append(PUBLIC / "transfer.py")
    source_hashes = {str(path.relative_to(PUBLIC)): hashlib.sha256(path.read_bytes()).hexdigest() for path in public_paths}
    write_json(SIDE / "STARTED.json", {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                      "protocol_sha256": hashlib.sha256((SIDE / "PREREGISTRATION.json").read_bytes()).hexdigest(),
                                      "fitting_inputs_sha256": source_hashes, "hidden_reads_by_fitter": 0})
    spec = json.loads((PUBLIC / "input" / "model.json").read_text())
    queries = json.loads((PUBLIC / "input" / "queries.json").read_text())
    with np.load(PUBLIC / "input" / "train.npz", allow_pickle=False) as training:
        configurations, betas = training["visible_spins"], training["betas"]
    identifiers = np.asarray([query["id"] for query in queries], dtype="<U24")
    transfer = public_module()
    magnitudes = np.full(len(spec["edges"]), np.mean(spec["parameter_prior"]["coupling_magnitudes"]["bounds"]))
    fields = np.full(spec["n_spins"], np.mean(spec["parameter_prior"]["fields"]["bounds"]))
    control_started = time.monotonic()
    save_predictions("midpoint_prior", model_predictions(transfer, spec, queries, magnitudes, fields), identifiers,
                     {"algorithm": protocol["variants"][0], "runtime_seconds": time.monotonic() - control_started,
                      "fitted": False, "hidden_scores_used": False})
    control_started = time.monotonic()
    bridge = empirical_bridge(spec, queries, configurations, betas)
    save_predictions("empirical_log_bridge", bridge, identifiers,
                     {"algorithm": protocol["variants"][1], "runtime_seconds": time.monotonic() - control_started,
                      "fitted": True, "hidden_scores_used": False})
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-4:])
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    validation = check_implementation(torch, transfer, spec, configurations, betas)
    validation.update({"torch_version": torch.__version__, "cpu_affinity": sorted(os.sched_getaffinity(0))})
    write_json(SIDE / "implementation_checks.json", validation)
    engine = LatentLikelihood(torch, spec, configurations, betas)
    for variant in protocol["variants"][2:]:
        try:
            fitted, report = fit_variant(engine, variant)
            predictions = model_predictions(transfer, spec, queries, fitted[:engine.edge_count], fitted[engine.edge_count:])
            save_predictions(variant["name"], predictions, identifiers, report,
                             (fitted[:engine.edge_count], fitted[engine.edge_count:]))
        except Exception as error:
            directory = SIDE / variant["name"]
            directory.mkdir(exist_ok=True)
            write_json(directory / "FAILED.json", {"exception": type(error).__name__, "message": str(error),
                                                    "hidden_scores_used": False})
    for path in public_paths:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source_hashes[str(path.relative_to(PUBLIC))]
    hashes = {str(path.relative_to(SIDE)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(SIDE.rglob("*")) if path.is_file() and path.suffix in (".npz", ".json", ".py")}
    write_json(SIDE / "OUTPUTS_FROZEN.json", {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                             "files_sha256": hashes, "runtime_seconds": time.monotonic() - started,
                                             "first_trusted_evaluation_has_occurred": False,
                                             "public_input_hashes_unchanged": True,
                                             "policy": "No further fitting or prediction edits; evaluation only"})
    print(json.dumps({"outputs_frozen": True, "runtime_seconds": time.monotonic() - started,
                      "variants_with_predictions": [variant["name"] for variant in protocol["variants"]
                                                    if (SIDE / variant["name"] / "predictions.npz").exists()]}), flush=True)


if __name__ == "__main__":
    run()
