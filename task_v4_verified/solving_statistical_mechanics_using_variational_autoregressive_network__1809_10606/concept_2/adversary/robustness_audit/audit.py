import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import datetime
import hashlib
import json
import math
from pathlib import Path
import signal
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WITNESS = json.loads((ROOT / "adversary/search_run/witness.json").read_text())
SPEC = json.loads((ROOT / "participant/input/spec.json").read_text())
GENERATOR = np.random.default_rng(202608281806)
IDENTIFIERS = np.arange(65536, dtype=np.uint32)
BITS = np.arange(16, dtype=np.uint32)
SPINS = (2 * ((IDENTIFIERS[:, None] >> BITS) & 1).astype(np.int8) - 1).astype(float)
EDGES = []
for site in range(16):
    row, column = divmod(site, 4)
    EDGES.extend([(site, 4 * row + (column + 1) % 4), (site, 4 * ((row + 1) % 4) + column)])
FEATURES = np.column_stack([SPINS[:, first] * SPINS[:, second] for first, second in EDGES])
ORDERED = SPINS[:, WITNESS["order"]]
DISTANCE = np.count_nonzero(SPINS != WITNESS["pattern"], axis=1)
SECTOR = np.minimum(DISTANCE, 16 - DISTANCE) <= WITNESS["radius"]
GATES = {"entropy": ("min", 3.0), "reverse_kl": ("min", 0.4), "reward_variance": ("max", 0.05),
         "gradient_infinity": ("max", 0.003), "energy_error_per_spin": ("max", 0.02),
         "target_sector_mass": ("min", 0.35), "proposal_sector_mass": ("max", 0.001)}


def save(name, document):
    (HERE / name).write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def binary_entropy(probability):
    clipped = np.clip(probability, 1e-300, 1 - np.finfo(float).eps)
    result = -clipped * np.log(clipped) - (1 - clipped) * np.log1p(-clipped)
    return np.where((probability <= 0) | (probability >= 1), 0.0, result)


def target(energy, beta):
    log_weight = -beta * energy
    maximum = float(log_weight.max())
    log_partition = maximum + math.log(float(np.exp(log_weight - maximum).sum()))
    log_probability = log_weight - log_partition
    probability = np.exp(log_probability)
    return probability, log_probability, log_partition


def proposal(weights):
    logits = ORDERED @ weights.T
    log_probability = -np.logaddexp(0, -ORDERED * logits).sum(axis=1)
    probability = np.exp(log_probability)
    residual = 0.5 * (ORDERED - np.tanh(logits / 2))
    return probability, log_probability, residual


def root_residual_correlation(probability, entropy):
    correlation = SPINS.T @ (probability[:, None] * SPINS)
    conditional_entropies = binary_entropy((1 + correlation) / 2).sum(axis=0)
    totals = conditional_entropies - entropy + math.log(2)
    return {"minimum_root_conditional_total_correlation": float(totals.min()),
            "best_root": int(totals.argmin())}


def evaluate(energy, beta, distribution):
    probability, log_probability, residual = distribution
    target_probability, log_target, log_partition = target(energy, beta)
    dimensionless = beta * energy
    reward = dimensionless + log_probability
    mean_reward = float(probability @ reward)
    centered = reward - mean_reward
    gradient = np.tril((residual * (probability * centered)[:, None]).T @ ORDERED, -1)
    metrics = {"entropy": float(-probability @ log_probability),
               "reverse_kl": float(probability @ (log_probability - log_target)),
               "reward_variance": float(probability @ centered ** 2),
               "gradient_infinity": float(np.abs(gradient).max()),
               "energy_error_per_spin": abs(float((probability - target_probability) @ dimensionless)) / 16,
               "target_sector_mass": float(target_probability[SECTOR].sum()),
               "proposal_sector_mass": float(probability[SECTOR].sum()),
               "target_entropy": float(-target_probability @ log_target),
               "log_partition": log_partition,
               "proposal_normalization_error": abs(float(probability.sum()) - 1),
               "target_normalization_error": abs(float(target_probability.sum()) - 1)}
    failures = []
    scores = []
    for name, (direction, threshold) in GATES.items():
        measured = metrics[name]
        if direction == "min":
            scores.append(max(0.0, min(1.0, measured / threshold)))
            if measured < threshold - 1e-10:
                failures.append(name)
        else:
            scores.append(1.0 if measured <= 0 else min(1.0, threshold / measured))
            if measured > threshold + 1e-10:
                failures.append(name)
    return {"metrics": metrics, "original_metric_gates_pass": not failures,
            "failed_metric_gates": failures, "minimum_gate_ratio": min(scores)}


def transform(values):
    result = np.array(values, dtype=float, copy=True)
    stride = 1
    while stride < len(result):
        blocks = result.reshape(-1, 2, stride)
        first = blocks[:, 0, :].copy()
        second = blocks[:, 1, :].copy()
        blocks[:, 0, :] = first + second
        blocks[:, 1, :] = first - second
        stride *= 2
    return result


def frustrated(bonds):
    total = 0
    for site in range(16):
        row, column = divmod(site, 4)
        right = 4 * row + (column + 1) % 4
        down = 4 * ((row + 1) % 4) + column
        total += bonds[2 * site] * bonds[2 * right + 1] * bonds[2 * down] * bonds[2 * site + 1] < 0
    return int(total)


def independent_sizes():
    neighbors = [0] * 16
    for first, second in EDGES:
        neighbors[first] |= 1 << second
        neighbors[second] |= 1 << first
    sizes = np.zeros(65536, dtype=np.int8)
    for mask in range(1, 65536):
        lowest = mask & -mask
        site = lowest.bit_length() - 1
        remainder = mask ^ lowest
        sizes[mask] = max(sizes[remainder], 1 + sizes[remainder & ~neighbors[site]])
    return sizes


def timeout_handler(signum, frame):
    raise TimeoutError("private audit exceeded its eight-minute computation cap")


def main():
    started = time.monotonic()
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(480)
    if hasattr(os, "sched_getaffinity"):
        os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    frozen_manifest = json.loads((ROOT / "adversary/release_manifest.json").read_text())
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in frozen_manifest["sha256"]}
    bonds = np.asarray(WITNESS["bonds"], dtype=float)
    weights = np.asarray(WITNESS["weights"], dtype=float)
    original = proposal(weights)
    energy = -(FEATURES @ bonds)
    original_report = evaluate(energy, WITNESS["beta"], original)
    official = json.loads((ROOT / "adversary/search_run/official_report.json").read_text())
    agreement = {name: abs(original_report["metrics"][name] - official["metrics"][name]) for name in GATES}
    assert max(agreement.values()) < 1e-10
    original_report["standalone_absolute_differences_from_official"] = agreement
    original_report.update(root_residual_correlation(original[0], original_report["metrics"]["entropy"]))
    save("original_crosscheck.json", original_report)
    floor_rows = []
    beta_rows = []
    for floor in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2):
        scaled = weights * (math.log((1 - floor) / floor) / np.abs(weights).sum(axis=1).max())
        distribution = proposal(scaled)
        report = evaluate(energy, 2.0, distribution)
        report.update(floor=floor, beta=2.0, weight_scale=float(np.max(np.abs(scaled)) / np.max(np.abs(weights))))
        floor_rows.append(report)
        for beta in np.linspace(1, 3, 41):
            report = evaluate(energy, float(beta), distribution)
            report.update(floor=floor, beta=float(beta))
            beta_rows.append(report)
    save("floor_sweep.json", floor_rows)
    save("beta_profiles.json", beta_rows)
    core = original[1] >= original[1].max() - 1e-10
    root = WITNESS["order"][0]
    free = [WITNESS["order"][position] for position in range(1, 16) if not np.any(weights[position])]
    fixed = [site for site in range(16) if site not in free]
    relative = np.zeros(16)
    relative[root] = 1
    for position, site in enumerate(WITNESS["order"]):
        if position > 0 and site in fixed:
            relative[site] = np.sign(weights[position, 0])
    perturbations = []
    for amplitude in (0.001, 0.003, 0.01, 0.03, 0.1):
        for repetition in range(32):
            noise = GENERATOR.uniform(-1, 1, size=32)
            noise -= noise.mean()
            noise /= np.max(np.abs(noise))
            perturbed = bonds * (1 + amplitude * noise)
            perturbed_energy = -(FEATURES @ perturbed)
            coupling_matrix = np.zeros((16, 16))
            for coupling, (first, second) in zip(perturbed, EDGES):
                coupling_matrix[first, second] = coupling
                coupling_matrix[second, first] = coupling
            adjusted = weights.copy()
            for position, site in enumerate(WITNESS["order"]):
                if site in free:
                    adjusted[position, 0] = 4 * float(coupling_matrix[site] @ relative)
            fixed_report = evaluate(perturbed_energy, 2.0, original)
            adjusted_report = evaluate(perturbed_energy, 2.0, proposal(adjusted))
            perturbations.append({"amplitude": amplitude, "repetition": repetition,
                                  "bond_magnitudes": np.abs(perturbed).tolist(),
                                  "old_core_energy_range": float(np.ptp(perturbed_energy[core])),
                                  "ground_degeneracy_tolerance_1e_9": int(np.count_nonzero(np.abs(perturbed_energy - perturbed_energy.min()) < 1e-9)),
                                  "fixed_weights": fixed_report, "analytic_floppy_field_adjustment": adjusted_report,
                                  "adjusted_weights": adjusted.tolist()})
    save("bond_perturbations.json", perturbations)
    print("Floor, beta and generic-perturbation sweeps complete", flush=True)
    sizes = independent_sizes()
    populations = ((SPINS + 1) / 2).sum(axis=1)
    ball_transform = transform((populations <= 4).astype(float))
    survey = []
    draws = 0
    while len(survey) < 512:
        draws += 1
        sampled = GENERATOR.choice([-1, 1], size=32)
        count = frustrated(sampled)
        if not 4 <= count <= 12:
            continue
        sampled_energy = -(FEATURES @ sampled)
        probability, log_probability, log_partition = target(sampled_energy, 1.0)
        entropy = float(-probability @ log_probability)
        ground = SPINS[sampled_energy == sampled_energy.min()]
        coupling_matrix = np.zeros((16, 16))
        for coupling, (first, second) in zip(sampled, EDGES):
            coupling_matrix[first, second] = coupling
            coupling_matrix[second, first] = coupling
        zero_fields = (ground @ coupling_matrix) == 0
        free_masks = (zero_fields.astype(np.uint32) * np.left_shift(np.uint32(1), BITS)).sum(axis=1).astype(np.uint32)
        maximum_free = int(sizes[free_masks].max())
        ball_mass = transform(transform(probability) * ball_transform) / 65536
        ball_log_moment = transform(transform(probability * log_probability) * ball_transform) / 65536
        eligible = ball_mass >= 0.175 - 1e-12
        row = {"bonds": sampled.tolist(), "frustrated_plaquettes": count, "entropy_beta1": entropy,
               "ground_energy": float(sampled_energy.min()), "ground_degeneracy": len(ground),
               "maximum_ground_coordinate_cube_free_spins": maximum_free,
               "maximum_antipodal_ground_cube_states": 2 ** (maximum_free + 1),
               "maximum_cube_star_entropy_floor_1e_4": float((maximum_free + 1) * math.log(2) + (15 - maximum_free) * binary_entropy(np.asarray(1e-4))),
               "necessary_q_entropy_upper_bound_original_energy_and_KL": entropy - 0.08,
               "maximum_radius4_antipodal_mass": float(2 * ball_mass.max())}
        row.update(root_residual_correlation(probability, entropy))
        if np.any(eligible):
            conditional = -ball_log_moment[eligible] / ball_mass[eligible] + np.log(ball_mass[eligible])
            sector_identifier = int(np.flatnonzero(eligible)[np.argmax(conditional)])
            selected = np.count_nonzero(SPINS != SPINS[sector_identifier], axis=1) <= 4
            restricted = probability[selected] / probability[selected].sum()
            restricted_entropy = float(-restricted @ np.log(restricted))
            marginals = ((SPINS[selected] + 1) / 2).T @ restricted
            row.update(maximum_entropy_mass_qualified_antipodal_sector=restricted_entropy + math.log(2),
                       oriented_sector_entropy=restricted_entropy,
                       oriented_sector_total_correlation=float(binary_entropy(marginals).sum() - restricted_entropy),
                       selected_sector_mass=float(2 * probability[selected].sum()),
                       selected_pattern=SPINS[sector_identifier].astype(int).tolist())
        survey.append(row)
    save("binary_instance_survey.json", {"admissible_models": len(survey), "random_draws": draws,
                                         "beta": 1.0, "rows": survey})
    after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in before}
    summary = {"completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "elapsed_seconds": time.monotonic() - started, "seed": 202608281806,
               "numpy_version": np.__version__, "standalone_no_evaluator_import": True,
               "original_contract_still_passes": original_report["original_metric_gates_pass"],
               "frozen_files_changed_during_audit": [name for name in before if before[name] != after[name]],
               "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "observed_maximum_entropy_beta1": max(row["entropy_beta1"] for row in survey),
               "maximum_ground_cube_free_spins_observed": max(row["maximum_ground_coordinate_cube_free_spins"] for row in survey),
               "mass_qualified_sector_models": sum("maximum_entropy_mass_qualified_antipodal_sector" in row for row in survey),
               "survey_is_not_global_exhaustion": True}
    summary["floor_profiles"] = []
    for floor in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2):
        selected_rows = [row for row in beta_rows if row["floor"] == floor]
        passing = [row["beta"] for row in selected_rows if row["original_metric_gates_pass"]]
        best = max(selected_rows, key=lambda row: row["minimum_gate_ratio"])
        summary["floor_profiles"].append({"floor": floor, "passing_beta_grid": passing,
                                           "best_beta": best["beta"], "best_gate_ratio": best["minimum_gate_ratio"],
                                           "minimum_variance_on_beta_grid": min(row["metrics"]["reward_variance"] for row in selected_rows),
                                           "minimum_gradient_on_beta_grid": min(row["metrics"]["gradient_infinity"] for row in selected_rows)})
    summary["perturbation_profiles"] = []
    for amplitude in (0.001, 0.003, 0.01, 0.03, 0.1):
        rows = [row for row in perturbations if row["amplitude"] == amplitude]
        record = {"amplitude": amplitude, "trials": len(rows)}
        for mode in ("fixed_weights", "analytic_floppy_field_adjustment"):
            failures = {}
            for row in rows:
                for name in row[mode]["failed_metric_gates"]:
                    failures[name] = failures.get(name, 0) + 1
            record[mode] = {"all_metric_gates_pass": sum(row[mode]["original_metric_gates_pass"] for row in rows),
                            "failure_counts": failures,
                            "median_variance": float(np.median([row[mode]["metrics"]["reward_variance"] for row in rows])),
                            "median_gradient": float(np.median([row[mode]["metrics"]["gradient_infinity"] for row in rows]))}
        summary["perturbation_profiles"].append(record)
    summary["survey_entropy_quantiles"] = np.quantile([row["entropy_beta1"] for row in survey], [0, .25, .5, .75, .9, .99, 1]).tolist()
    summary["ground_cube_free_spin_histogram"] = {str(size): sum(row["maximum_ground_coordinate_cube_free_spins"] == size for row in survey) for size in range(9)}
    eligible_rows = [row for row in survey if "maximum_entropy_mass_qualified_antipodal_sector" in row]
    if eligible_rows:
        champion = max(eligible_rows, key=lambda row: row["maximum_entropy_mass_qualified_antipodal_sector"])
        summary["highest_entropy_mass_qualified_sector"] = champion
    save("summary.json", summary)
    signal.alarm(0)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
