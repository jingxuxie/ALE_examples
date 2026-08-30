import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
for variable, suffix in (("TMPDIR", "tmp"), ("XDG_CACHE_HOME", "cache"), ("TORCH_HOME", "cache/torch")):
    destination = ROOT / suffix
    destination.mkdir(parents=True, exist_ok=True)
    os.environ[variable] = str(destination)

import argparse
import json
import time

import numpy as np
import scipy.linalg as sla
import torch

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch.set_default_dtype(torch.float64)
sys.path.insert(0, str(ROOT.parents[1] / "evaluator" / "hidden"))
import trusted_physics


def exact_targets():
    orders = np.asarray([trusted_physics.exact_order(distance) for distance in range(1, 129)])
    densities = np.asarray([trusted_physics.exact_density(distance) for distance in range(1, 33)])
    return torch.from_numpy(orders), torch.from_numpy(densities)


ORDER_TARGET, DENSITY_TARGET = exact_targets()


def unpack(raw):
    orthogonal, triangular = torch.linalg.qr(raw, mode="reduced")
    signs = torch.sign(torch.diagonal(triangular, dim1=-2, dim2=-1))
    rows = (orthogonal * signs[:, None, :]).transpose(1, 2)
    half = rows.shape[1]
    return rows[0, :, :half], rows[0, :, half:], rows[1, :, :half], rows[1, :, half:]


def assemble(blocks):
    even, upper, odd, lower = blocks
    zero = torch.zeros_like(even)
    return torch.stack((torch.cat((torch.cat((even, zero), 1), torch.cat((zero, odd), 1)), 0),
                        torch.cat((torch.cat((zero, upper), 1), torch.cat((lower, zero), 1)), 0)))


def raw_from_tensor(tensor):
    half = tensor.shape[1] // 2
    rows = np.stack((np.concatenate((tensor[0, :half, :half], tensor[1, :half, half:]), axis=1),
                     np.concatenate((tensor[0, half:, half:], tensor[1, half:, :half]), axis=1)))
    return torch.tensor(rows.transpose(0, 2, 1).copy(), requires_grad=True)


def stationary(blocks):
    even, upper, odd, lower = blocks
    half = even.shape[0]
    def product(matrix):
        transposed = matrix.T.contiguous()
        return torch.kron(transposed, transposed)
    transfer = torch.cat((torch.cat((product(even), product(lower)), 1),
                          torch.cat((product(upper), product(odd)), 1)), 0)
    identity = torch.eye(half)
    trace = torch.cat((identity.reshape(-1), identity.reshape(-1)))
    source = trace / (2 * half)
    system = torch.eye(2 * half**2) - transfer + source[:, None] * trace[None, :]
    vector = torch.linalg.solve(system, source)
    density_even = vector[:half**2].reshape(half, half)
    density_odd = vector[half**2:].reshape(half, half)
    return (density_even + density_even.T) / 2, (density_odd + density_odd.T) / 2


def observables(raw, full=True):
    blocks = unpack(raw)
    even, upper, odd, lower = blocks
    density_even, density_odd = stationary(blocks)
    initial_z_even = even @ even.T - upper @ upper.T
    initial_z_odd = odd @ odd.T - lower @ lower.T
    magnetization = torch.sum(density_even * initial_z_even) + torch.sum(density_odd * initial_z_odd)
    order_left = even.T @ density_even @ upper + lower.T @ density_odd @ odd
    order_environment = even @ lower.T + upper @ odd.T
    nearest_order = 2 * torch.sum(order_left * order_environment)
    energy_excess = -nearest_order - magnetization + 4 / np.pi
    if not full:
        return energy_excess, None, None
    density_left_even = even.T @ density_even @ even - lower.T @ density_odd @ lower
    density_left_odd = odd.T @ density_odd @ odd - upper.T @ density_even @ upper
    identity = torch.eye(even.shape[0])
    density_environment_even = initial_z_even - magnetization * identity
    density_environment_odd = initial_z_odd - magnetization * identity
    orders = []
    densities = []
    for distance in range(128):
        orders.append(2 * torch.sum(order_left * order_environment))
        if distance < 32:
            densities.append(torch.sum(density_left_even * density_environment_even)
                             + torch.sum(density_left_odd * density_environment_odd))
            next_even = even @ density_environment_even @ even.T + upper @ density_environment_odd @ upper.T
            next_odd = lower @ density_environment_even @ lower.T + odd @ density_environment_odd @ odd.T
            density_environment_even, density_environment_odd = next_even, next_odd
        order_environment = even @ order_environment @ odd.T + upper @ order_environment.T @ lower.T
    return energy_excess, torch.stack(orders), torch.stack(densities)


def grow(tensor, new_dimension, seed, noise=1e-3):
    rng = np.random.default_rng(seed)
    previous_half = tensor.shape[1] // 2
    new_half = new_dimension // 2
    if new_half > 2 * previous_half:
        raise ValueError("Grow by at most a factor of two")
    expanded = np.zeros((2, new_dimension, new_dimension))
    previous_rows = raw_from_tensor(tensor).detach().numpy().transpose(0, 2, 1)
    for sector in range(2):
        complement = sla.null_space(previous_rows[sector])
        rows = np.concatenate((previous_rows[sector], complement[:, :new_half-previous_half].T), axis=0)
        sector_rows = np.zeros((new_half, 2 * new_half))
        sector_rows[:, :previous_half] = rows[:, :previous_half]
        sector_rows[:, new_half:new_half+previous_half] = rows[:, previous_half:]
        sector_rows += noise * rng.normal(size=sector_rows.shape)
        orthogonal, triangular = np.linalg.qr(sector_rows.T)
        sector_rows = (orthogonal * np.sign(np.diag(triangular))).T
        if sector == 0:
            expanded[0, :new_half, :new_half] = sector_rows[:, :new_half]
            expanded[1, :new_half, new_half:] = sector_rows[:, new_half:]
        else:
            expanded[0, new_half:, new_half:] = sector_rows[:, :new_half]
            expanded[1, new_half:, :new_half] = sector_rows[:, new_half:]
    return expanded


def short_score(result):
    values = result.get("metrics", {})
    return {key: result.get(key) for key in ("passed", "valid", "core_score", "worst_family_score")} | {
        key: values.get(key) for key in ("dimension", "energy_excess", "order_max_relative_error",
                                        "density_max_relative_error", "minimum_density_eigenvalue",
                                        "second_transfer_modulus")}


class Run:
    def __init__(self, name, seed, seconds):
        self.directory = ROOT / name
        self.directory.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.evaluations = 0
        self.best_quality = -1.0
        self.best_core = -1.0
        self.log = (self.directory / "progress.jsonl").open("a", buffering=1)

    def record(self, value):
        value["elapsed"] = time.monotonic() - self.started
        self.log.write(json.dumps(value, allow_nan=False) + "\n")
        print(json.dumps(value, allow_nan=False), flush=True)

    def save(self, raw, label):
        with torch.no_grad():
            tensor = assemble(unpack(raw)).numpy().copy()
        path = self.directory / (label + ".npz")
        np.savez(path, A=tensor)
        result = trusted_physics.check(path)
        (self.directory / (label + ".score.json")).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        self.record({"event": "checkpoint", "label": label, "evaluations": self.evaluations, **short_score(result)})
        quality = result.get("worst_family_score", 0.0)
        core = result.get("core_score", 0.0)
        if quality > self.best_quality or (quality == self.best_quality and core > self.best_core):
            self.best_quality, self.best_core = quality, core
            np.savez(self.directory / "state.npz", A=tensor)
            (self.directory / "score.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        return result

    def optimize(self, raw, mode, iterations, label, energy_weight=1.0):
        optimizer = torch.optim.LBFGS([raw], lr=1.0, max_iter=20, max_eval=30, history_size=100,
                                      tolerance_grad=1e-12, tolerance_change=1e-15, line_search_fn="strong_wolfe")
        def closure():
            optimizer.zero_grad()
            excess, orders, densities = observables(raw, full=mode != "energy")
            if mode == "energy":
                loss = excess * 1000
            else:
                normalized_energy = excess / 5e-5
                normalized_order = (orders / ORDER_TARGET - 1) / 0.025
                normalized_density = (densities / DENSITY_TARGET - 1) / 0.1
                if mode == "fit":
                    loss = energy_weight * normalized_energy.square() + normalized_order.square().mean() + normalized_density.square().mean()
                elif mode == "hinge":
                    loss = energy_weight * torch.relu(normalized_energy - 0.75).square()
                    loss = loss + torch.relu(normalized_order.abs() - 0.75).square().mean()
                    loss = loss + torch.relu(normalized_density.abs() - 0.75).square().mean()
                    loss = loss + 1e-4 * (normalized_order.square().mean() + normalized_density.square().mean())
                else:
                    loss = energy_weight * normalized_energy.square() + normalized_order.pow(4).mean() + normalized_density.pow(4).mean()
            if not torch.isfinite(loss):
                raise FloatingPointError("Nonfinite objective")
            loss.backward()
            self.evaluations += 1
            if self.evaluations % 100 == 0:
                self.record({"event": "objective", "mode": mode, "evaluations": self.evaluations,
                             "loss": float(loss.detach()), "energy_excess": float(excess.detach())})
            return loss
        for block in range((iterations + 19) // 20):
            if time.monotonic() >= self.deadline:
                break
            optimizer.step(closure)
            if block % 10 == 9:
                result = self.save(raw, f"{label}_{block+1:03d}")
                if result.get("passed"):
                    return True
        return self.save(raw, label).get("passed", False)


def validate_derivatives():
    torch.manual_seed(441)
    raw = torch.randn(2, 4, 2, requires_grad=True)
    excess, orders, densities = observables(raw)
    tensor = assemble(unpack(raw)).detach().numpy()
    independent = trusted_physics.metrics(tensor)
    errors = {"energy": abs(float(excess.detach()) - independent["energy_excess"]),
              "order": float(np.max(np.abs(orders.detach().numpy() - independent["order_correlations"]))),
              "density": float(np.max(np.abs(densities.detach().numpy() - independent["density_connected_correlations"])))}
    objective = excess + orders.sum() + densities.sum()
    objective.backward()
    analytic = raw.grad[0, 1, 1].item()
    displaced = raw.detach().clone()
    step = 1e-5
    def scalar(value):
        energy, order, density = observables(value)
        return float(energy + order.sum() + density.sum())
    displaced[0, 1, 1] += step
    positive = scalar(displaced)
    displaced[0, 1, 1] -= 2 * step
    negative = scalar(displaced)
    finite_difference = (positive-negative)/(2*step)
    errors["gradient_absolute"] = abs(analytic-finite_difference)
    print(json.dumps(errors), flush=True)
    (ROOT / "derivative_validation.json").write_text(json.dumps(errors, indent=2) + "\n")
    assert max(errors.values()) < 1e-6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="direct_seed_1")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--seconds", type=int, default=1400)
    parser.add_argument("--energy-iterations", type=int, default=500)
    parser.add_argument("--fit-iterations", type=int, default=1500)
    parser.add_argument("--resume")
    parser.add_argument("--dimension", type=int, default=24)
    parser.add_argument("--validate", action="store_true")
    arguments = parser.parse_args()
    if arguments.validate:
        validate_derivatives()
        return
    run = Run(arguments.name, arguments.seed, arguments.seconds)
    torch.manual_seed(arguments.seed)
    if arguments.resume:
        tensor = np.load(arguments.resume, allow_pickle=False)["A"].real
        if tensor.shape[1] < arguments.dimension:
            tensor = grow(tensor, arguments.dimension, arguments.seed)
        raw = raw_from_tensor(tensor)
    else:
        raw = torch.randn(2, 4, 2, requires_grad=True)
        dimensions = [dimension for dimension in (4, 8, 16, 24) if dimension <= arguments.dimension]
        for dimension in dimensions:
            if raw.shape[-1] * 2 != dimension:
                tensor = assemble(unpack(raw)).detach().numpy()
                raw = raw_from_tensor(grow(tensor, dimension, arguments.seed + dimension))
            run.optimize(raw, "energy", arguments.energy_iterations, f"energy_D{dimension}")
    for round_index, mode in enumerate(("fit", "hinge", "fourth", "hinge")):
        if time.monotonic() >= run.deadline:
            break
        if run.optimize(raw, mode, arguments.fit_iterations, f"{mode}_{round_index}"):
            break
    run.record({"event": "finished", "best_quality": run.best_quality, "best_core": run.best_core})


if __name__ == "__main__":
    main()
