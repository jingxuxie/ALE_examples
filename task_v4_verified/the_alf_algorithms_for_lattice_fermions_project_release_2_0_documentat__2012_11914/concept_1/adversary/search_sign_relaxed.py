import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from search_sign import SignObjective
from search_sign_deep import StencilObjective


class SearchFinished(Exception):
    pass


class EigenvalueControl:
    def __init__(self, beta, target, penalty, angular=False):
        physical = SignObjective(beta, 4.0, 1.0, 16, 0.0)
        self.kinetic = physical.kinetic
        self.coupling = physical.coupling
        self.target = target
        self.penalty = penalty
        self.angular = angular

    def evaluate(self, vector):
        fields = vector.reshape(16, 16)
        diagonal = np.exp(self.coupling * fields)
        slices = self.kinetic[None] * diagonal[:, None, :]
        prefixes = [np.eye(16)]
        for transfer in slices:
            prefixes.append(transfer @ prefixes[-1])
        eigenvalues, eigenvectors = np.linalg.eig(prefixes[-1])
        denominators = 1 + np.abs(eigenvalues)
        distances = np.abs(eigenvalues - self.target) ** 2 / denominators ** 2
        if self.angular:
            radii = np.maximum(np.abs(eigenvalues), 1e-14)
            distances = eigenvalues.real / radii + 0.05 * np.log(radii / abs(self.target)) ** 2
        selected = int(np.argmin(distances))
        eigenvalue = eigenvalues[selected]
        right_vector = eigenvectors[:, selected]
        left_vector = np.linalg.inv(eigenvectors)[selected]
        denominator = denominators[selected]
        numerator = abs(eigenvalue - self.target) ** 2
        coefficient = np.conj(eigenvalue - self.target) / denominator ** 2
        if abs(eigenvalue) > 1e-15:
            coefficient -= numerator * np.conj(eigenvalue) / (abs(eigenvalue) * denominator ** 3)
        if self.angular:
            radius = max(abs(eigenvalue), 1e-14)
            coefficient = 0.5 * (1 / radius - eigenvalue.real * np.conj(eigenvalue) / radius ** 3)
            coefficient += 0.05 * np.log(radius / abs(self.target)) * np.conj(eigenvalue) / radius ** 2
        gradient = np.empty_like(fields)
        suffix = np.eye(16)
        for time_index in range(15, -1, -1):
            suffix = suffix @ slices[time_index]
            projected_left = left_vector @ suffix
            projected_right = prefixes[time_index] @ right_vector
            derivative = self.coupling * projected_left * projected_right
            gradient[time_index] = 2 * np.real(coefficient * derivative)
        value = float(distances[selected]) + self.penalty * np.mean(1 - fields ** 2)
        gradient -= 2 * self.penalty * fields / fields.size
        return value, gradient.reshape(-1)


def run(arguments):
    random = np.random.default_rng(arguments.seed)
    seeds = [np.asarray(json.loads(path.read_text())["fields"], dtype=np.int8) for path in arguments.start]
    if any(fields.shape != (16, 16) or not np.isin(fields, [-1, 1]).all() for fields in seeds):
        raise ValueError("Expected binary seeds")
    stencil = StencilObjective(arguments.beta)
    start = time.monotonic()
    best_gap = float("inf")
    restart = 0
    visited = set()
    found = False
    while time.monotonic() - start < arguments.seconds:
        target = [-0.65, -0.85, -1.15, -1.55][restart % 4]
        penalty = [0.0, 0.01, 0.05, 0.15][(restart // 4) % 4]
        objective = EigenvalueControl(arguments.beta, target, penalty, angular=restart % 2 == 1)
        fields = seeds[restart % len(seeds)].copy()
        if restart >= len(seeds):
            fields.reshape(-1)[random.choice(256, size=int(random.integers(2, 25)), replace=False)] *= -1
        initial = np.clip(fields.astype(float) * 0.95 + random.normal(0, 0.03, fields.shape), -1, 1).reshape(-1)
        if restart % 3 == 1:
            initial = random.uniform(-1, 1, 256)
        elif restart % 3 == 2:
            fields = np.repeat(random.choice([-1, 1], size=(1, 16)), 16, axis=0)
            horizontal, vertical = divmod(int(random.integers(16)), 4)
            sites = [4 * ((horizontal + delta_horizontal) % 4) + (vertical + delta_vertical) % 4 for delta_horizontal, delta_vertical in [(0, 0), (0, 1), (1, 1), (1, 0)]]
            durations = random.multinomial(12, [0.25] * 4) + 1
            time_index = 0
            for duration, occupied in zip(durations, [(0, 2), (1, 2), (1, 3), (2, 3)]):
                fields[time_index:time_index + duration, sites] = -1
                fields[time_index:time_index + duration, np.asarray(sites)[list(occupied)]] = 1
                time_index += duration
            initial = fields.astype(float).reshape(-1) * 0.98

        def inspect(vector):
            nonlocal best_gap, found
            if time.monotonic() - start > arguments.seconds:
                raise SearchFinished()
            relaxed = vector.reshape(16, 16)
            candidates = np.array([
                np.where(relaxed >= 0, 1, -1),
                np.where(random.random(relaxed.shape) < (relaxed + 1) / 2, 1, -1),
            ], dtype=np.int8)
            scores = stencil.evaluate(candidates, "product")
            selected = int(np.argmin(scores))
            if scores[selected] < -1e-12:
                record = stencil.record(candidates[selected], "product", float(scores[selected]), time.monotonic() - start, restart, arguments.seed)
                record["search_method"] = "bounded continuous eigenvalue control followed by binary rounding"
                arguments.output.write_text(json.dumps(record, indent=2) + "\n")
                arguments.output.with_name(arguments.output.stem + "_fields.json").write_text(json.dumps({"fields": record["fields"]}) + "\n")
                print(json.dumps({"relaxed_search_saved": str(arguments.output), "beta": arguments.beta, "objective": float(scores[selected]), "restart": restart, "seconds": time.monotonic() - start}), flush=True)
                found = True
                raise SearchFinished()
            binary = candidates[0]
            signature = binary.tobytes()
            if signature not in visited:
                visited.add(signature)
                gap, _ = objective.evaluate(binary.astype(float).reshape(-1))
                if gap < best_gap:
                    best_gap = gap
                    seeds.append(binary.copy())
                    if len(seeds) > 32:
                        seeds.pop(3)
                    checkpoint = {"success": False, "not_a_witness": True, "beta": arguments.beta, "interaction": 4.0, "chemical": 1.0, "slices": 16, "fields": binary.tolist(), "target_eigenvalue": target, "gap_objective": gap, "seconds": time.monotonic() - start}
                    arguments.output.with_name(arguments.output.stem + "_checkpoint.json").write_text(json.dumps(checkpoint, indent=2) + "\n")

        def evaluate(vector):
            if time.monotonic() - start > arguments.seconds:
                raise SearchFinished()
            return objective.evaluate(vector)

        try:
            inspect(initial)
            result = minimize(evaluate, initial, method="L-BFGS-B", jac=True, bounds=[(-1.0, 1.0)] * 256, callback=inspect, options={"maxiter": 180, "maxls": 30, "ftol": 1e-12, "gtol": 1e-7})
            inspect(result.x)
        except SearchFinished:
            break
        if restart % 25 == 0:
            print(json.dumps({"relaxed_restart": restart, "beta": arguments.beta, "best_binary_gap": best_gap, "continuous_objective": float(result.fun), "seconds": time.monotonic() - start}), flush=True)
        restart += 1
    print(json.dumps({"relaxed_search_finished": True, "found": found, "restarts": restart, "best_binary_gap": best_gap, "seconds": time.monotonic() - start}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--beta", type=float, default=0.75)
    parser.add_argument("--seconds", type=float, default=360)
    parser.add_argument("--seed", type=int, default=770941)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
