"""Private binary-HS witness search using the exploration helper's convention.

The spin-channel interaction is ALF 2.0, arXiv:2012.11914v2, Section 8.3.2.
The exact two-state HS identity is arXiv:2108.00553, Section II, Equation (4);
it is not the ALF paper's generic four-state HS approximation.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm

from explore import hopping


class SignObjective:
    def __init__(self, beta, interaction, chemical, slices, radius=0.05):
        self.beta = beta
        self.interaction = interaction
        self.chemical = chemical
        self.slices = slices
        self.chemicals = chemical + np.array([-radius, 0.0, radius])
        self.kinetic = expm(-beta / slices * hopping())
        self.coupling = np.arccosh(np.exp(beta * interaction / (2 * slices)))

    def products(self, fields):
        fields = np.asarray(fields)
        if fields.ndim == 2:
            fields = fields[None]
        products = np.broadcast_to(np.eye(16), (len(fields), 2, 16, 16)).copy()
        for time_index in range(self.slices):
            diagonal = np.exp(self.coupling * fields[:, time_index, None, :] * np.array([1, -1])[None, :, None])
            products = self.kinetic @ (diagonal[..., :, None] * products)
        return products

    def evaluate(self, fields, details=False):
        products = self.products(fields)
        singular_values = np.linalg.svd(products, compute_uv=False)
        scores = []
        signs_by_chemical = []
        logs_by_chemical = []
        for chemical in self.chemicals:
            fugacity = np.exp(self.beta * chemical)
            signs, logarithms = np.linalg.slogdet(np.eye(16) + fugacity * products)
            normalization = np.log1p(fugacity * singular_values).sum(axis=-1)
            total_sign = signs.prod(axis=1)
            normalized_logs = (logarithms - normalization).sum(axis=1)
            scores.append(total_sign * np.exp(normalized_logs))
            signs_by_chemical.append(signs)
            logs_by_chemical.append(logarithms)
        objective = np.max(scores, axis=0)
        if details:
            return objective, np.array(signs_by_chemical), np.array(logs_by_chemical), products
        return objective


def proposals(fields, random, extra=96):
    flat_fields = fields.reshape(-1)
    count = len(flat_fields)
    candidates = np.repeat(flat_fields[None], count + extra, axis=0)
    indices = np.arange(count)
    candidates[indices, indices] *= -1
    for candidate in candidates[count:]:
        changed = random.choice(count, size=int(random.integers(2, 9)), replace=False)
        candidate[changed] *= -1
    return candidates.reshape(-1, *fields.shape)


def witness_record(fields, objective, elapsed, iterations):
    score, signs, logarithms, products = objective.evaluate(fields, details=True)
    half_signs, half_logs = np.linalg.slogdet(np.eye(16) + products)
    chemical_grid = np.linspace(objective.chemicals[0], objective.chemicals[-1], 21)
    grid_signs = []
    for chemical in chemical_grid:
        spin_signs = np.linalg.slogdet(np.eye(16) + np.exp(objective.beta * chemical) * products)[0]
        grid_signs.append(float(spin_signs.prod()))
    if not np.all(signs.prod(axis=2) < 0) or half_signs.prod() <= 0 or min(grid_signs) != -1.0 or max(grid_signs) != -1.0:
        raise ValueError("Witness failed sign or half-filling controls")
    return {
        "beta": objective.beta,
        "interaction": objective.interaction,
        "chemical": objective.chemical,
        "slices": objective.slices,
        "fields": fields.tolist(),
        "objective": float(score[0]),
        "objective_definition": "max_mu product_sigma det(I+exp(beta*mu)*P_sigma)/product_j(1+exp(beta*mu)*sv_j(P_sigma))",
        "chemical_checks": objective.chemicals.tolist(),
        "spin_signs": signs[:, 0].tolist(),
        "spin_logabsdet": logarithms[:, 0].tolist(),
        "half_filling_spin_signs": half_signs[0].tolist(),
        "half_filling_spin_logabsdet": half_logs[0].tolist(),
        "dense_chemical_grid": chemical_grid.tolist(),
        "dense_chemical_total_signs": grid_signs,
        "seconds": elapsed,
        "iterations": iterations,
        "high_precision_verified": False,
        "continuous_interval_certified": False,
    }


def search(arguments):
    seed = json.loads(arguments.start.read_text())
    fields = np.asarray(seed["fields"], dtype=np.int8)
    if fields.shape != (seed["slices"], 16) or not np.isin(fields, [-1, 1]).all():
        raise ValueError("Expected binary fields on the periodic 4x4 square lattice")
    random = np.random.default_rng(arguments.seed)
    start = time.monotonic()
    current_beta = float(seed["beta"])
    best_witness = None
    total_iterations = 0
    history = []
    while time.monotonic() - start < arguments.seconds:
        objective = SignObjective(current_beta, seed["interaction"], seed["chemical"], seed["slices"], arguments.mu_radius)
        score = float(objective.evaluate(fields)[0])
        best_fields = fields.copy()
        best_score = score
        stale = 0
        negative_steps = 0
        print(json.dumps({"stage_beta": current_beta, "initial_objective": score, "seconds": time.monotonic() - start}), flush=True)
        while time.monotonic() - start < arguments.seconds:
            total_iterations += 1
            candidates = proposals(fields, random)
            values = objective.evaluate(candidates)
            selected = int(np.argmin(values))
            candidate_score = float(values[selected])
            if candidate_score < score:
                fields = candidates[selected].copy()
                score = candidate_score
            else:
                stale += 1
                fields = best_fields.copy()
                changed = random.choice(fields.size, size=int(random.integers(2, 7)), replace=False)
                fields.reshape(-1)[changed] *= -1
                score = float(objective.evaluate(fields)[0])
            if score < best_score:
                best_score = score
                best_fields = fields.copy()
                stale = 0
            if best_score < -arguments.margin:
                negative_steps += 1
                if negative_steps >= arguments.polish:
                    best_witness = witness_record(best_fields, objective, time.monotonic() - start, total_iterations)
                    history.append({"beta": current_beta, "objective": best_score, "seconds": time.monotonic() - start})
                    best_witness["continuation_history"] = history
                    arguments.output.write_text(json.dumps(best_witness, indent=2) + "\n")
                    print(json.dumps({"saved": str(arguments.output), "beta": current_beta, "objective": best_score, "seconds": time.monotonic() - start}), flush=True)
                    fields = best_fields.copy()
                    break
            if total_iterations % 20 == 0:
                print(json.dumps({"beta": current_beta, "best_objective": best_score, "iterations": total_iterations, "stale": stale, "seconds": time.monotonic() - start}), flush=True)
        if best_score >= -arguments.margin:
            break
        if current_beta <= arguments.target_beta + 1e-10:
            break
        current_beta = max(arguments.target_beta, round(current_beta - arguments.step, 8))
    print(json.dumps({"finished": True, "best_beta": None if best_witness is None else best_witness["beta"], "iterations": total_iterations, "seconds": time.monotonic() - start}), flush=True)


def verify_witness(path, digits):
    import mpmath as multiprecision

    record = json.loads(path.read_text())
    fields = np.asarray(record["fields"], dtype=np.int8)
    start = time.monotonic()
    with multiprecision.workdps(digits):
        beta = multiprecision.mpf(str(record["beta"]))
        interaction = multiprecision.mpf(str(record["interaction"]))
        slices = record["slices"]
        kinetic = multiprecision.expm(-beta / slices * multiprecision.matrix(hopping().tolist()))
        coupling = multiprecision.acosh(multiprecision.exp(beta * interaction / (2 * slices)))
        products = [multiprecision.eye(16), multiprecision.eye(16)]
        for time_fields in fields:
            for spin_index, spin in enumerate([1, -1]):
                diagonal = [multiprecision.exp(spin * coupling * int(field)) for field in time_fields]
                scaled = multiprecision.matrix([[diagonal[row] * products[spin_index][row, column] for column in range(16)] for row in range(16)])
                products[spin_index] = kinetic * scaled
        checks = []
        for chemical in [0.0, *record["chemical_checks"]]:
            fugacity = multiprecision.exp(beta * multiprecision.mpf(str(chemical)))
            determinants = [multiprecision.det(multiprecision.eye(16) + fugacity * product) for product in products]
            signs = [int(multiprecision.sign(determinant)) for determinant in determinants]
            expected = 1 if chemical == 0 else -1
            if signs[0] * signs[1] != expected:
                raise ValueError(f"High-precision sign control failed at chemical={chemical}")
            checks.append({
                "chemical": chemical,
                "spin_signs": signs,
                "spin_logabsdet": [multiprecision.nstr(multiprecision.log(abs(determinant)), 40) for determinant in determinants],
            })
        sublattice = multiprecision.diag([(-1) ** (site // 4 + site % 4) for site in range(16)])
        expected_down = sublattice * (products[0].T ** -1) * sublattice
        residual = multiprecision.norm(products[1] - expected_down) / multiprecision.norm(products[1])
        if residual > multiprecision.mpf(10) ** (-digits // 2):
            raise ValueError("Particle-hole identity failed")
        record["high_precision_verification"] = {
            "decimal_digits": digits,
            "independent_kinetic_exponential": True,
            "checks": checks,
            "particle_hole_relative_residual": multiprecision.nstr(residual, 12),
            "seconds": time.monotonic() - start,
        }
    objective = SignObjective(record["beta"], record["interaction"], record["chemical"], record["slices"], 0.0)
    shifted = np.array([np.roll(fields, offset, axis=0) for offset in range(len(fields))])
    shifted_scores = objective.evaluate(shifted)
    flipped_score = float(objective.evaluate(-fields)[0])
    if not np.all(shifted_scores < 0) or flipped_score >= 0:
        raise ValueError("Time-translation or spin-inversion control failed")
    record["symmetry_controls"] = {"negative_cyclic_time_shifts": len(shifted), "global_spin_inversion_negative": True}
    record["high_precision_verified"] = True
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"verified": str(path), "beta": record["beta"], **record["high_precision_verification"], "symmetry_controls": record["symmetry_controls"]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=Path, default=Path(__file__).with_name("negative_2.0_4.0_1.0_16.json"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("negative_continuation.json"))
    parser.add_argument("--seconds", type=float, default=480)
    parser.add_argument("--target-beta", type=float, default=1.6)
    parser.add_argument("--step", type=float, default=0.05)
    parser.add_argument("--mu-radius", type=float, default=0.05)
    parser.add_argument("--margin", type=float, default=1e-10)
    parser.add_argument("--polish", type=int, default=8)
    parser.add_argument("--seed", type=int, default=41027)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--digits", type=int, default=80)
    arguments = parser.parse_args()
    if arguments.verify is not None:
        verify_witness(arguments.verify, arguments.digits)
    else:
        search(arguments)


if __name__ == "__main__":
    main()
