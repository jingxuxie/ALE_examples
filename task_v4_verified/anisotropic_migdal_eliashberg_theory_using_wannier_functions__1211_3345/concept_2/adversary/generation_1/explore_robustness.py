import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, minimize, root


PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
POOL = ROOT / "adversary" / "ratchet_pool"
sys.path.insert(0, str(POOL))
from generate_pool import InstanceSearch, make_directions
from pool_common import EliashbergSolver, audit_pair, constraint_report, json_write, load_instance, logical_hash, physics_report, read_artifact


def write_instance(directory, instance):
    directory.mkdir(parents=True, exist_ok=True)
    json_write(directory / "config.json", instance["config"])
    with (directory / "reference.npz").open("wb") as stream:
        np.savez_compressed(stream, **{name: value for name, value in instance.items() if name not in ("config", "input_sha256")})


def anti_instance(name, first_rows, middle_rows, total_rows, energies, base_config, seed):
    generator = np.random.RandomState(seed)
    desired = np.stack([first_rows, middle_rows, np.asarray(total_rows) - first_rows - middle_rows])
    matrices = []
    profiles = np.linspace(-1, 1, 8)
    for mode, rows in enumerate(desired):
        noise = generator.normal(size=(8, 8))
        noise = (noise + noise.T) / np.sqrt(2)
        structure = np.outer(profiles, profiles) if mode != 1 else np.outer(np.sin(2 * np.pi * np.arange(8) / 3), np.sin(2 * np.pi * np.arange(8) / 3))
        affinity = np.exp(.45 * structure + .2 * noise)
        np.fill_diagonal(affinity, 0)
        diagonal = .12
        diffuse = .0051
        degrees = 8 * rows - diagonal - 7 * diffuse
        if degrees.min() <= 0:
            raise ValueError("mode row profile incompatible with positive diagonal")
        solution = root(lambda logs: np.exp(logs) * (affinity @ np.exp(logs)) - degrees, np.log(np.sqrt(degrees / 7)), tol=1e-11)
        if np.max(np.abs(solution.fun)) > 1e-8:
            raise ValueError("anticorrelated mode balancing failed")
        scale = np.exp(solution.x)
        matrices.append(affinity * np.outer(scale, scale) + diffuse * (np.ones((8, 8)) - np.eye(8)) + diagonal * np.eye(8))
    reference = np.stack(matrices)
    weights = np.full(8, 1 / 8)
    config = json.loads(json.dumps(base_config))
    config["dataset_id"] = name
    instance = {"reference": reference, "weights": weights, "energies_mev": np.asarray(energies), "row_sums": reference @ weights,
                "diagonal": np.diagonal(reference, axis1=1, axis2=2), "static": reference.sum(axis=0), "config": config}
    feasible, canonical = constraint_report(np.stack([reference, reference]), instance)
    if not feasible["admissible"]:
        raise ValueError(str(feasible))
    return instance


def select_target(private_score):
    return 1 + math.floor((private_score - 1 - .003) * 100 + 1e-10) / 100


def retain_if_meaningful(name, instance, pair, output, provenance):
    physics = physics_report(pair, instance)
    private_score = physics["score"]
    target = select_target(private_score)
    record = {"name": name, "private_score": private_score, "private_only_target_rule": "largest 0.01-spaced ratio at least 0.003 below the private witnessed score; require target >=1.08", "selected_target": target, "retained": False, **provenance}
    if target < 1.08:
        record["reason"] = "No meaningful >=1.08 target under the predeclared private-only margin rule."
        return record
    instance["config"]["target_ratio"] = target
    audit = audit_pair(pair, instance)
    if not audit["valid"]:
        record["reason"] = "Independent audit did not pass."
        return record
    directory = output / "candidates" / name
    write_instance(directory / "input", instance)
    with (directory / "witness.npz").open("wb") as stream:
        np.savez_compressed(stream, kernels=pair)
    loaded = load_instance(directory / "input")
    read_artifact(directory / "witness.npz", loaded["config"])
    audit["input_sha256"] = loaded["input_sha256"]
    record.update(retained=True, path=str(directory), private_score=audit["score"], logical_instance_sha256=logical_hash(instance), reason="Private passing witness independently audited; not yet a demonstrated champion failure.")
    json_write(directory / "audit.json", audit)
    json_write(directory / "provenance.json", record)
    return record


class RobustPairSearch:
    def __init__(self, instance, initial_pair, deadline):
        self.instance = instance
        self.reference = instance["reference"]
        self.basis = make_directions()
        self.flat = self.basis.reshape(40, -1).T
        self.deadline = deadline
        self.calls = 0
        self.last = None
        self.last_value = None
        coarse = dict(instance["config"])
        coarse.update(root_xtol_kelvin=.0002, eigenvalue_tolerance=1e-9)
        self.solvers = [EliashbergSolver(instance["weights"], instance["row_sums"], instance["energies_mev"] * np.asarray(family["energy_factors"]), coarse) for family in coarse["families"]]
        self.initial = np.concatenate([np.linalg.lstsq(self.flat, (modes - self.reference).ravel(), rcond=None)[0] for modes in initial_pair])
        self.initial = self.retreat(self.initial)

    def materialize(self, coordinates):
        return np.stack([self.reference + np.einsum("a,asij->sij", section, self.basis) for section in coordinates.reshape(2, 40)])

    def retreat(self, coordinates):
        result = coordinates.copy()
        lower = self.instance["config"]["entry_lower"] + 2e-7
        upper = self.instance["config"]["entry_upper"] - 2e-7
        for index in range(2):
            section = result[40 * index:40 * (index + 1)]
            difference = (self.flat @ section).reshape(3, 8, 8)
            fraction = 1.
            decreasing = difference < 0
            increasing = difference > 0
            if decreasing.any():
                fraction = min(fraction, float(np.min((self.reference[decreasing] - lower) / -difference[decreasing])))
            if increasing.any():
                fraction = min(fraction, float(np.min((upper - self.reference[increasing]) / difference[increasing])))
            section *= max(0., min(1., fraction)) * (1 - 1e-10)
        return result

    def values(self, coordinates):
        if self.last is not None and np.array_equal(self.last, coordinates):
            return self.last_value
        if time.process_time() > self.deadline:
            raise TimeoutError("private minimax CPU budget reached")
        self.calls += 1
        pair = self.materialize(coordinates)
        values = []
        gradients = []
        for solver in self.solvers:
            temperatures = []
            derivatives = []
            for modes in pair:
                temperature = solver.critical_temperature(modes, 64)["tc_kelvin"]
                data = solver.eigenpair(modes, temperature, 64, gradient=True)
                step = temperature * 1e-4
                slope = (solver.eigenpair(modes, temperature + step, 64)["eigenvalue"] - solver.eigenpair(modes, temperature - step, 64)["eigenvalue"]) / (2 * step)
                derivatives.append(-np.einsum("sij,asij->a", data["gradient"], self.basis) / (temperature * slope))
                temperatures.append(temperature)
            values.append(np.log(temperatures[0] / temperatures[1]))
            gradients.append(np.concatenate((derivatives[0], -derivatives[1])))
        self.last = coordinates.copy()
        self.last_value = np.asarray(values), np.asarray(gradients)
        return self.last_value

    def run(self):
        rows, columns = np.triu_indices(8, 1)
        edge_matrix = np.transpose(self.basis[:, :, rows, columns], (1, 2, 0)).reshape(84, 40)
        block = np.zeros((168, 81))
        block[:84, :40] = edge_matrix
        block[84:, 40:80] = edge_matrix
        base_edges = np.tile(self.reference[:, rows, columns].ravel(), 2)
        lower = self.instance["config"]["entry_lower"] + 2e-7 - base_edges
        upper = self.instance["config"]["entry_upper"] - 2e-7 - base_edges
        linear = LinearConstraint(block, lower, upper)
        initial_values, initial_gradient = self.values(self.initial)
        initial = np.concatenate((self.initial, [float(initial_values.min())]))
        objective_gradient = np.zeros(81)
        objective_gradient[-1] = -1
        nonlinear = {"type": "ineq", "fun": lambda variables: self.values(variables[:80])[0] - variables[-1],
                     "jac": lambda variables: np.column_stack((self.values(variables[:80])[1], -np.ones(len(self.solvers))))}
        result = minimize(lambda variables: (-variables[-1], objective_gradient), initial, jac=True, method="SLSQP", constraints=[linear, nonlinear], options={"ftol": 2e-9, "maxiter": 140})
        coordinates = self.retreat(result.x[:80])
        return self.materialize(coordinates), {"optimizer_success": bool(result.success), "optimizer_message": str(result.message), "iterations": result.nit, "calls": self.calls, "coarse_robust_ratio": float(np.exp(self.values(coordinates)[0].min()))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu-seconds", type=float, default=480.)
    arguments = parser.parse_args()
    if not 0 < arguments.cpu_seconds <= 600:
        parser.error("private follow-up budget must be <=600 CPU seconds")
    output = PENDING / "robustness_exploration"
    output.mkdir(exist_ok=True)
    base = load_instance(PENDING / "archived_originals" / "participant" / "input")
    started = time.process_time()
    records = []
    specs = [
        ("anti_constant_1p4", np.array([.12, .20, .32, .48, .72, .88, 1., 1.08]), np.full(8, .2), np.full(8, 1.4), [3., 24., 100.]),
        ("anti_constant_2p2", np.array([.1, .25, .45, .65, 1.25, 1.45, 1.65, 1.8]), np.full(8, .3), np.full(8, 2.2), [2.5, 32., 120.]),
        ("anti_variable_total", np.array([.1, .2, .35, .55, .85, 1.1, 1.2, 1.1]), np.array([.15, .05, .1, .25, .25, .1, .05, .15]), np.array([1.35, 1.45, 1.55, 1.65, 1.65, 1.55, 1.45, 1.35]), [3., 35., 110.]),
        ("anti_constant_1p0", np.array([.08, .14, .22, .32, .58, .68, .76, .82]), np.full(8, .1), np.ones(8), [2.5, 20., 100.]),
    ]
    for index, (name, first, middle, total, energies) in enumerate(specs):
        try:
            instance = anti_instance(name, first, middle, total, energies, base["config"], 290800 + index)
            deadline = min(started + arguments.cpu_seconds - 30, time.process_time() + 24)
            search = InstanceSearch(instance, 290900 + index, output / (name + ".jsonl"), deadline)
            pair, landscape = search.run(24)
            correlation = float(np.corrcoef(instance["row_sums"][[0, 2]])[0, 1])
            record = retain_if_meaningful(name, instance, pair, output, {"kind": "anticorrelated_mode_rows", "mode_0_2_row_correlation": correlation, "total_row_range": float(np.ptp(instance["row_sums"].sum(axis=0))), "landscape": landscape})
        except Exception as error:
            record = {"name": name, "retained": False, "reason": type(error).__name__ + ": " + str(error)}
        records.append(record)
        print(json.dumps({key: record.get(key) for key in ("name", "private_score", "selected_target", "retained", "mode_0_2_row_correlation", "reason")}), flush=True)
    with np.load(ROOT / "champions" / "generation_1" / "frozen_submission" / "witness.npz", allow_pickle=False) as archive:
        initial_pair = np.asarray(archive["kernels"])[[1, 0]]
    stresses = [
        ("middle_cross_60", [[4., 80., 60.]]),
        ("middle_cross_45", [[4., 100., 45.]]),
        ("middle_cross_35", [[4., 110., 35.]]),
        ("soft_up_middle_cross", [[12., 100., 45.]]),
        ("independent_pair", [[3., 100., 45.], [12., 35., 80.]]),
        ("moderate_independent", [[10., 55., 65.], [3., 15., 120.]]),
        ("middle_below_soft", [[18., 12., 90.]]),
        ("cross_both", [[12., 100., 45.], [18., 12., 90.]]),
    ]
    for index, (name, energy_sets) in enumerate(stresses):
        if time.process_time() - started > arguments.cpu_seconds - 20:
            break
        try:
            instance = {key: value.copy() if isinstance(value, np.ndarray) else json.loads(json.dumps(value)) for key, value in base.items() if key != "input_sha256"}
            instance["config"]["dataset_id"] = "robust_" + name
            for family_index, energies in enumerate(energy_sets):
                instance["config"]["families"].append({"name": "independent_branch_" + str(family_index), "energy_factors": (np.asarray(energies) / instance["energies_mev"]).tolist()})
            deadline = min(started + arguments.cpu_seconds - 15, time.process_time() + 36)
            search = RobustPairSearch(instance, initial_pair, deadline)
            pair, diagnostics = search.run()
            initial_physics = physics_report(initial_pair, instance)
            record = retain_if_meaningful(name, instance, pair, output, {"kind": "independent_frequency_minimax", "added_energy_sets_mev": energy_sets,
                "private_optimizer": diagnostics, "old_witness_robustness_screen_only": initial_physics["score"],
                "actual_champion_search_replay_required": True})
        except Exception as error:
            record = {"name": name, "retained": False, "reason": type(error).__name__ + ": " + str(error)}
        records.append(record)
        print(json.dumps({key: record.get(key) for key in ("name", "private_score", "selected_target", "old_witness_robustness_screen_only", "retained", "reason")}), flush=True)
    summary = {"cpu_seconds": time.process_time() - started, "cpu_budget_seconds": arguments.cpu_seconds, "records": records,
               "target_selection_uses_private_evidence_only": True, "new_fresh_launches": 0, "active_package_unchanged": True}
    json_write(output / "summary.json", summary)
    print(json.dumps({"finished": True, "cpu_seconds": summary["cpu_seconds"], "retained": sum(record["retained"] for record in records)}), flush=True)


if __name__ == "__main__":
    main()
