import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import hashlib
import json
import time

import numpy as np
import scipy
from scipy.linalg import null_space
from scipy.optimize import linprog, minimize_scalar, root

from pool_common import POOL, EliashbergSolver, audit_pair, constraint_report, json_write, load_instance, logical_hash, read_artifact, save_instance, verify_snapshot, within_pool


SPECS = [
    {"name": "rough_broad", "rows": [.20, .30, .45, .65, 1., 1.5, 2.1, 2.7], "energies": [4., 25., 100.], "fractions": [.44, .12, .44], "assortativity": 1.15, "community": 0., "roughness": .12, "spectral_tilt": .10, "edge_tilt": .08, "groups": [0, 1, 0, 1, 0, 1, 0, 1]},
    {"name": "rough_assortative", "rows": [.22, .34, .49, .72, 1.08, 1.58, 2.18, 2.75], "energies": [3., 23., 105.], "fractions": [.45, .10, .45], "assortativity": 1.45, "community": .35, "roughness": .28, "spectral_tilt": .18, "edge_tilt": .20, "groups": [0, 1, 1, 0, 0, 1, 0, 1]},
    {"name": "two_hot_groups", "rows": [.25, .40, .70, .90, 1.90, 2.20, 2.45, 2.65], "energies": [3.5, 28., 110.], "fractions": [.44, .12, .44], "assortativity": .85, "community": 1.35, "roughness": .18, "spectral_tilt": .55, "edge_tilt": .35, "groups": [0, 1, 0, 1, 0, 1, 0, 1]},
    {"name": "three_group_frustration", "rows": [.30, .50, .75, 1.05, 1.70, 2., 2.45, 2.75], "energies": [4., 32., 120.], "fractions": [.45, .10, .45], "assortativity": .60, "community": 1.30, "roughness": .45, "spectral_tilt": .42, "edge_tilt": .45, "groups": [0, 1, 2, 0, 1, 2, 0, 1]},
    {"name": "balanced_hubs", "rows": [.22, .30, .50, .80, 1.55, 1.65, 2.60, 2.65], "energies": [3., 22., 95.], "fractions": [.45, .10, .45], "assortativity": 1.10, "community": 1.10, "roughness": .30, "spectral_tilt": .38, "edge_tilt": .40, "groups": [0, 1, 0, 1, 0, 1, 0, 1]},
    {"name": "spectral_crossing", "rows": [.24, .36, .55, .78, 1.10, 1.70, 2.35, 2.90], "energies": [5., 20., 110.], "fractions": [.43, .14, .43], "assortativity": 1.50, "community": .50, "roughness": .35, "spectral_tilt": .70, "edge_tilt": .35, "groups": [0, 1, 1, 0, 0, 1, 0, 1]},
    {"name": "broad_two_channels", "rows": [.20, .33, .50, .70, 1.15, 1.65, 2.30, 2.85], "energies": [2.5, 18., 115.], "fractions": [.45, .10, .45], "assortativity": 1.80, "community": .90, "roughness": .35, "spectral_tilt": .30, "edge_tilt": .30, "groups": [0, 1, 0, 1, 0, 1, 0, 1]},
    {"name": "near_degenerate_groups", "rows": [.28, .45, .80, 1., 1.85, 1.90, 2.50, 2.55], "energies": [3.5, 26., 105.], "fractions": [.44, .12, .44], "assortativity": .90, "community": 2., "roughness": .12, "spectral_tilt": .40, "edge_tilt": .25, "groups": [0, 1, 0, 1, 0, 1, 0, 1]},
]


def make_directions():
    edges = list(zip(*np.triu_indices(8, 1)))
    incidence = np.zeros((8, len(edges)))
    for edge, (left, right) in enumerate(edges):
        incidence[left, edge] = incidence[right, edge] = 1
    edge_basis = null_space(incidence)
    basis = np.zeros((edge_basis.shape[1], 8, 8))
    for edge, (left, right) in enumerate(edges):
        basis[:, left, right] = basis[:, right, left] = edge_basis[edge]
    return np.stack((np.concatenate((basis, np.zeros_like(basis))), np.concatenate((np.zeros_like(basis), basis)), np.concatenate((-basis, -basis))), axis=1)


def bounded_allocation(total, preference, lower, upper):
    if not 3 * lower < total < 3 * upper:
        raise ValueError("static edge cannot be split into three bounded modes")
    left = 0.
    right = total / preference.min()
    for iteration in range(70):
        middle = (left + right) / 2
        values = np.clip(middle * preference, lower, upper)
        if values.sum() < total:
            left = middle
        else:
            right = middle
    return np.clip((left + right) / 2 * preference, lower, upper)


def generate_instance(specification, seed, base_config):
    generator = np.random.RandomState(seed)
    rows = np.asarray(specification["rows"])
    fractions = np.asarray(specification["fractions"])
    groups = np.asarray(specification["groups"])
    features = np.linspace(-1, 1, 8)
    noise = generator.normal(size=(8, 8))
    noise = (noise + noise.T) / np.sqrt(2)
    same_group = (groups[:, None] == groups[None]).astype(float)
    affinity = np.exp(specification["assortativity"] * np.outer(features, features) + specification["community"] * same_group + specification["roughness"] * noise)
    np.fill_diagonal(affinity, 0)
    diagonal = np.full(8, .4)
    degrees = 8 * rows - diagonal
    solution = root(lambda logscale: np.exp(logscale) * (affinity @ np.exp(logscale)) - degrees, np.log(np.sqrt(degrees / 7)), tol=1e-11)
    if np.max(np.abs(solution.fun)) > 1e-8:
        raise ValueError("symmetric degree scaling did not converge")
    scale = np.exp(solution.x)
    aggregate = affinity * np.outer(scale, scale) + np.diag(diagonal)
    profile = np.cos(2 * np.pi * groups / (groups.max() + 1))
    profile += .15 * generator.normal(size=8)
    profile /= np.max(np.abs(profile))
    node_profile = (profile[:, None] + profile[None]) / 2
    edge_profile = generator.normal(size=(8, 8))
    edge_profile = (edge_profile + edge_profile.T) / np.sqrt(2)
    log_preferences = np.log(fractions)[:, None, None] + np.zeros((3, 8, 8))
    contrast = specification["spectral_tilt"] * node_profile + specification["edge_tilt"] * edge_profile
    log_preferences[0] += contrast
    log_preferences[2] -= contrast
    log_preferences[1] += .12 * specification["edge_tilt"] * noise
    preference = np.exp(log_preferences - log_preferences.max(axis=0))
    preference /= preference.sum(axis=0)
    reference = np.zeros((3, 8, 8))
    lower = base_config["entry_lower"] + 1e-5
    upper = base_config["entry_upper"] - 1e-5
    for left in range(8):
        for right in range(left, 8):
            probabilities = fractions if left == right else preference[:, left, right]
            values = bounded_allocation(aggregate[left, right], probabilities, lower, upper)
            reference[:, left, right] = reference[:, right, left] = values
    config = json.loads(json.dumps(base_config))
    config["dataset_id"] = "ratchet_" + specification["name"] + "_v1"
    config["target_ratio"] = 1.12
    weights = np.full(8, 1 / 8)
    instance = {
        "reference": reference, "weights": weights, "energies_mev": np.asarray(specification["energies"]),
        "row_sums": reference @ weights, "diagonal": np.diagonal(reference, axis1=1, axis2=2),
        "static": reference.sum(axis=0), "config": config,
    }
    feasible, canonical = constraint_report(np.stack([reference, reference]), instance)
    if not feasible["admissible"]:
        raise ValueError("generated reference is not feasible")
    if np.max(np.abs(instance["static"] @ weights - rows)) > 1e-8:
        raise ValueError("static degrees were not preserved by allocation")
    normalized = instance["static"] * np.outer(np.sqrt(weights / (1 + rows)), np.sqrt(weights / (1 + rows)))
    eigenvalues = np.linalg.eigvalsh(normalized)
    metadata = {
        "specification": specification, "generation_seed": seed,
        "logical_instance_sha256": logical_hash(instance), "lambda_i": rows.tolist(),
        "minimum_entry": float(reference.min()), "maximum_entry": float(reference.max()),
        "nonproportional_row_fraction_spread": float(np.max(np.ptp(instance["row_sums"] / rows[None], axis=1))),
        "static_normalized_top_eigenvalues": eigenvalues[-3:].tolist(),
        "static_relative_leading_gap": float((eigenvalues[-1] - eigenvalues[-2]) / eigenvalues[-1]),
        "electronic_scale_mev": 20000.,
        "largest_lambda_omega_over_electronic_scale": float(rows.max() * instance["energies_mev"].max() * 1.05 / 20000),
    }
    return instance, metadata


class InstanceSearch:
    def __init__(self, instance, seed, log_path, deadline):
        self.instance = instance
        self.reference = instance["reference"]
        self.basis = make_directions()
        self.generator = np.random.RandomState(seed)
        self.log_path = log_path
        self.deadline = deadline
        self.started = time.process_time()
        flat = self.basis.reshape(len(self.basis), -1).T
        self.inequalities = np.concatenate((flat, -flat))
        margin = 2e-6
        self.bound = np.concatenate(((instance["config"]["entry_upper"] - margin - self.reference).ravel(), (self.reference - instance["config"]["entry_lower"] - margin).ravel()))
        coarse_config = dict(instance["config"])
        coarse_config.update(root_xtol_kelvin=.0004, eigenvalue_tolerance=1e-9, temperature_bracket_kelvin=[10., 180.])
        self.coarse = []
        self.fine = []
        for family in instance["config"]["families"]:
            energies = instance["energies_mev"] * np.asarray(family["energy_factors"])
            self.coarse.append(EliashbergSolver(instance["weights"], instance["row_sums"], energies, coarse_config))
            self.fine.append(EliashbergSolver(instance["weights"], instance["row_sums"], energies, instance["config"]))
        self.highs = []
        self.lows = []
        self.best_score = 1.
        self.best_pair_indices = None

    def materialize(self, coordinates):
        return self.reference + np.einsum("a,asij->sij", coordinates, self.basis)

    def linear(self, objective):
        solution = linprog(objective, A_ub=self.inequalities, b_ub=self.bound, bounds=[(None, None)] * len(self.basis), method="highs")
        if not solution.success:
            raise RuntimeError(solution.message)
        return solution.x

    def initial(self, restart, endpoint):
        if restart == 0:
            return np.zeros(len(self.basis))
        if endpoint == "low" and restart >= 8 and restart % 4 != 0:
            return min(self.lows, key=lambda item: item["temperatures"][restart % 3])["coordinates"].copy()
        vertex = self.linear(self.generator.normal(size=len(self.basis)))
        if restart % 4 == 1:
            return vertex
        if restart % 4 == 2:
            other = self.linear(self.generator.normal(size=len(self.basis)))
            return .4 * vertex + .6 * other
        if restart % 4 == 3 and self.highs and endpoint == "high":
            incumbent = max(self.highs, key=lambda item: item["temperatures"][restart % 3])["coordinates"]
            return .55 * incumbent + .45 * vertex
        return .7 * vertex

    def optimize(self, initial, direction, solver):
        coordinates = initial.copy()
        iterations = 0
        directional_gap = None
        stop_reason = "iteration_limit"
        limit = 20 if direction == 1 else 32
        for iteration in range(limit):
            if time.process_time() >= self.deadline:
                stop_reason = "cpu_budget"
                break
            modes = self.materialize(coordinates)
            temperature = solver.critical_temperature(modes, 64)["tc_kelvin"]
            matrix_gradient = solver.eigenpair(modes, temperature, 64, gradient=True)["gradient"]
            gradient = np.einsum("sij,asij->a", matrix_gradient, self.basis)
            proposal = self.linear(-direction * gradient)
            displacement = proposal - coordinates
            directional_gap = float(max(0., direction * np.dot(gradient, displacement)))
            iterations = iteration + 1
            if directional_gap < 2e-9 or np.linalg.norm(displacement) < 1e-8:
                stop_reason = "directional_stationarity"
                break
            if direction == 1:
                amount = 1.
            else:
                amount = minimize_scalar(lambda fraction: solver.eigenpair(self.materialize(coordinates + fraction * displacement), temperature, 64)["eigenvalue"], bounds=(0, 1), method="bounded", options={"xatol": .001}).x
            coordinates += amount * displacement
        modes = self.materialize(coordinates)
        temperatures = [family.critical_temperature(modes, 96)["tc_kelvin"] for family in self.fine]
        return {"coordinates": coordinates, "temperatures": temperatures, "directional_gap64": directional_gap, "iterations": iterations, "stop_reason": stop_reason}

    def emit(self, record):
        record["cpu_seconds"] = time.process_time() - self.started
        with self.log_path.open("a") as stream:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")

    def run(self, max_restarts):
        last_improvement = 0
        for restart in range(max_restarts):
            if time.process_time() >= self.deadline:
                break
            solver = self.coarse[restart % 3]
            high = self.optimize(self.initial(restart, "high"), 1, solver)
            low = self.optimize(self.initial(restart, "low"), -1, solver)
            self.highs.append(high)
            self.lows.append(low)
            high_temperatures = np.array([item["temperatures"] for item in self.highs])
            low_temperatures = np.array([item["temperatures"] for item in self.lows])
            ratios = np.min(high_temperatures[:, None, :] / low_temperatures[None, :, :], axis=2)
            best_indices = np.unravel_index(np.argmax(ratios), ratios.shape)
            score = float(ratios[best_indices])
            if score > self.best_score + 1e-7:
                last_improvement = restart
            self.best_score = score
            self.best_pair_indices = best_indices
            self.emit({
                "restart": restart, "optimization_family": restart % 3,
                "high": {key: value for key, value in high.items() if key != "coordinates"},
                "low": {key: value for key, value in low.items() if key != "coordinates"},
                "best_observed_robust_ratio96": score,
                "paired_restart_ratio96": float(np.min(np.asarray(high["temperatures"]) / low["temperatures"])),
            })
            if restart >= 63 and restart - last_improvement >= 40:
                stationary = [item["temperatures"][0] for item in self.highs if item["stop_reason"] == "directional_stationarity"]
                if stationary and max(stationary) - min(stationary) < .025:
                    break
        if not self.highs:
            raise RuntimeError("CPU budget expired before the first restart")
        high_index, low_index = self.best_pair_indices
        pair = np.stack([self.materialize(self.highs[high_index]["coordinates"]), self.materialize(self.lows[low_index]["coordinates"])])
        return pair, self.landscape()

    def landscape(self):
        high_temperatures = np.array([item["temperatures"] for item in self.highs])
        low_temperatures = np.array([item["temperatures"] for item in self.lows])
        ratio_grid = np.min(high_temperatures[:, None, :] / low_temperatures[None, :, :], axis=2)
        common_low_scores = np.max(ratio_grid, axis=1)
        paired_scores = np.diag(ratio_grid)
        clusters = []
        for index in np.argsort(high_temperatures[:, 0]):
            endpoint = self.highs[int(index)]
            if endpoint["stop_reason"] != "directional_stationarity":
                continue
            temperature = float(high_temperatures[index, 0])
            if not clusters or temperature - clusters[-1]["maximum_tc96"] > .025:
                clusters.append({"minimum_tc96": temperature, "maximum_tc96": temperature, "count": 0, "best_common_low_ratio96": 0.})
            cluster = clusters[-1]
            cluster["maximum_tc96"] = temperature
            cluster["count"] += 1
            cluster["best_common_low_ratio96"] = max(cluster["best_common_low_ratio96"], float(common_low_scores[index]))
        cluster_maxima = sorted([cluster["maximum_tc96"] for cluster in clusters], reverse=True)
        return {
            "restarts": len(self.highs), "cpu_seconds": time.process_time() - self.started,
            "best_observed_robust_ratio96": self.best_score,
            "paired_restart_success_fraction": float(np.mean(paired_scores >= 1.12)),
            "high_restart_success_fraction_with_best_observed_low": float(np.mean(common_low_scores >= 1.12)),
            "high_nominal_tc96_range": [float(high_temperatures[:, 0].min()), float(high_temperatures[:, 0].max())],
            "low_nominal_tc96_range": [float(low_temperatures[:, 0].min()), float(low_temperatures[:, 0].max())],
            "common_low_ratio96_quantiles": np.quantile(common_low_scores, [0, .1, .5, .9, 1]).tolist(),
            "worst_high_search_gap_fraction": float((high_temperatures[:, 0].max() - high_temperatures[:, 0].min()) / high_temperatures[:, 0].max()),
            "stationary_high_clusters_0p025K": clusters,
            "competing_stationary_high_clusters_observed": len(clusters) > 1,
            "best_vs_runnerup_stationary_gap_kelvin": float(cluster_maxima[0] - cluster_maxima[1]) if len(cluster_maxima) > 1 else None,
            "best_pair_restart_indices": [int(index) for index in self.best_pair_indices],
            "interpretation": "Finite-cutoff multistart observations, not certified extrema or demonstrated model failures. High endpoints are compared against the best observed low endpoint to separate maximization difficulty from incomplete minimization.",
        }


def save_retained(output, name, instance, metadata, pair, audit, landscape):
    directory = output / "instances" / name
    save_instance(directory / "input", instance)
    with (directory / "witness.npz").open("xb") as stream:
        np.savez_compressed(stream, kernels=pair)
    reloaded = load_instance(directory / "input")
    artifact, digest = read_artifact(directory / "witness.npz", reloaded["config"], with_digest=True)
    if logical_hash(reloaded) != logical_hash(instance) or not np.array_equal(artifact, pair):
        raise RuntimeError("saved instance or witness failed roundtrip")
    audit["artifact_sha256"] = digest
    audit["input_sha256"] = reloaded["input_sha256"]
    json_write(directory / "audit.json", audit)
    json_write(directory / "metadata.json", metadata)
    json_write(directory / "landscape.json", landscape)
    return str(directory.relative_to(output))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu-seconds", type=float, default=900.)
    parser.add_argument("--max-restarts", type=int, default=160)
    parser.add_argument("--seed", type=int, default=121133450)
    parser.add_argument("--output-subdir", default=".")
    arguments = parser.parse_args()
    if not 0 < arguments.cpu_seconds <= 900 or not 1 <= arguments.max_restarts <= 256:
        parser.error("budget must be at most 900 CPU seconds and restarts at most 256")
    output = within_pool(arguments.output_subdir)
    if (output / "pool_summary.json").exists() or (output / "instances").exists():
        parser.error("output already contains a run; use a fresh sidecar subdirectory")
    output.mkdir(parents=True, exist_ok=True)
    logs = output / "search_logs"
    logs.mkdir(exist_ok=True)
    snapshot = verify_snapshot()
    base_config = json.loads((POOL / "base_config.json").read_text())
    started = time.process_time()
    records = []
    json_write(output / "specifications.json", {"specifications": SPECS, "seed": arguments.seed, "target_ratio": 1.12})
    for index, specification in enumerate(SPECS):
        remaining = arguments.cpu_seconds - (time.process_time() - started)
        if remaining < 12:
            records.append({"name": specification["name"], "retained": False, "reason": "CPU budget exhausted before search"})
            continue
        record = {"name": specification["name"], "retained": False}
        try:
            instance, metadata = generate_instance(specification, arguments.seed + 1000 * index, base_config)
            share = max(1., (remaining - 5 * (len(SPECS) - index)) / (len(SPECS) - index))
            search = InstanceSearch(instance, arguments.seed + 1000 * index + 1, logs / (specification["name"] + ".jsonl"), time.process_time() + share)
            pair, landscape = search.run(arguments.max_restarts)
            audit = audit_pair(pair, instance)
            record.update({"landscape": landscape, "audited_score": audit["score"], "admissible": audit["admissible"], "valid": audit["valid"], "logical_instance_sha256": logical_hash(instance)})
            if audit["valid"]:
                record["path"] = save_retained(output, specification["name"], instance, metadata, pair, audit, landscape)
                record["retained"] = True
            else:
                record["reason"] = "No independently valid witness at the fixed 1.12 target was found within this search budget. This is not an impossibility claim."
            json_write(logs / (specification["name"] + ".summary.json"), {"metadata": metadata, **record})
        except Exception as error:
            record["reason"] = type(error).__name__ + ": " + str(error)
        records.append(record)
        print(json.dumps({"instance": record["name"], "retained": record["retained"], "audited_score": record.get("audited_score"), "clusters": len(record.get("landscape", {}).get("stationary_high_clusters_0p025K", [])), "cpu_seconds": time.process_time() - started, "reason": record.get("reason")}), flush=True)
    summary = {
        "scope": "private sidecar only; no active package edits or model launches", "target_ratio": 1.12,
        "cpu_budget_seconds": arguments.cpu_seconds, "cpu_seconds": time.process_time() - started,
        "numpy": np.__version__, "scipy": scipy.__version__, "snapshot": snapshot,
        "generator_sha256": hashlib.sha256((POOL / "generate_pool.py").read_bytes()).hexdigest(),
        "retained_count": sum(record["retained"] for record in records), "attempted_specifications": len(SPECS),
        "records": records, "fresh_model_failure_demonstrated": False,
    }
    json_write(output / "pool_summary.json", summary)
    lines = ["# Private pool search landscape", "", "Target 1.12 throughout. Only independently passing witnesses are retained. No fresh model was tested.", "", "| Instance | Retained | Audited ratio | High clusters | Paired restart target rate |", "|---|---:|---:|---:|---:|"]
    for record in records:
        landscape = record.get("landscape", {})
        score = format(record["audited_score"], ".12f") if "audited_score" in record else "not evaluated"
        hit_rate = format(landscape.get("paired_restart_success_fraction", 0.), ".3f")
        lines.append("| " + record["name"] + " | " + str(record["retained"]) + " | " + score + " | " + str(len(landscape.get("stationary_high_clusters_0p025K", []))) + " | " + hit_rate + " |")
    lines += ["", "Clusters are separated by 0.025 K among endpoints reaching the directional-stationarity criterion on the 64-frequency search grid; listed temperatures and search ratios use 96 frequencies. Final scores use all required families/refinements and the independent audit. These observations do not certify local or global optimality.", "", "The parent must test an actual fresh solution's search before choosing a ratchet. An alternative instance, an unobserved optimum, or a low scout hit rate alone is not a genuine model failure."]
    (output / "LANDSCAPE.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"finished": True, "retained_count": summary["retained_count"], "cpu_seconds": summary["cpu_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
