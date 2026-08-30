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
import hashlib
import json
import math
import shutil
import time

import numpy as np
import torch

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch.set_default_dtype(torch.float64)
sys.path.insert(0, str(ROOT.parents[1] / "evaluator" / "hidden"))
import trusted_physics


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


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
    if np.max(np.abs(np.imag(tensor))) > 1e-12:
        raise ValueError("This optimizer uses real parity-block tensors")
    tensor = np.real(tensor)
    half = tensor.shape[1] // 2
    rows = np.stack((np.concatenate((tensor[0, :half, :half], tensor[1, :half, half:]), axis=1),
                     np.concatenate((tensor[0, half:, half:], tensor[1, half:, :half]), axis=1)))
    return torch.tensor(rows.transpose(0, 2, 1).copy(), requires_grad=True)


def symmetric_basis(half):
    basis = []
    for row in range(half):
        for column in range(row + 1):
            matrix = torch.zeros((half, half))
            if row == column:
                matrix[row, column] = 1.0
            else:
                matrix[row, column] = 1.0 / math.sqrt(2.0)
                matrix[column, row] = 1.0 / math.sqrt(2.0)
            basis.append(matrix.reshape(-1))
    return torch.stack(basis)


def correlation_sequence(transfer, initial, final, count):
    vectors = initial[:, None]
    power = transfer
    while vectors.shape[1] < count:
        remaining = min(vectors.shape[1], count - vectors.shape[1])
        vectors = torch.cat((vectors, power @ vectors[:, :remaining]), dim=1)
        if vectors.shape[1] < count:
            power = power @ power
    return final @ vectors


class Physics:
    def __init__(self, half):
        self.half = half
        self.basis = symmetric_basis(half)
        self.sector_size = self.basis.shape[0]
        self.identity = torch.eye(2 * self.sector_size)
        self.trace = torch.cat((self.basis @ torch.eye(half).reshape(-1),) * 2)
        self.source = self.trace / (2 * half)
        self.transpose = torch.arange(half * half).reshape(half, half).T.reshape(-1)
        self.targets_x = torch.tensor([trusted_physics.exact_order(distance) for distance in range(1, 1025)])
        self.targets_z = torch.tensor([trusted_physics.exact_density(distance) for distance in range(1, 257)])
        self.targets_y = -self.targets_x[:128] / (4 * torch.arange(1, 129).square() - 1)

    def observables(self, raw, counts=(1024, 256, 128)):
        even, upper, odd, lower = unpack(raw)
        matrices = torch.stack((even, upper, lower, odd))
        products = torch.einsum("bij,bkl->bikjl", matrices, matrices).reshape(4, self.half**2, self.half**2)
        projected = self.basis @ products @ self.basis.T
        transfer_even = torch.cat((torch.cat((projected[0], projected[1]), 1),
                                   torch.cat((projected[2], projected[3]), 1)), 0)
        system = self.identity - transfer_even.T + self.source[:, None] * self.trace[None, :]
        density_vector = torch.linalg.solve(system, self.source)
        density_even = (self.basis.T @ density_vector[:self.sector_size]).reshape(self.half, self.half)
        density_odd = (self.basis.T @ density_vector[self.sector_size:]).reshape(self.half, self.half)
        right_z_even = even @ even.T - upper @ upper.T
        right_z_odd = odd @ odd.T - lower @ lower.T
        right_z = torch.cat((self.basis @ right_z_even.reshape(-1), self.basis @ right_z_odd.reshape(-1)))
        magnetization = density_vector @ right_z
        left_z_even = even.T @ density_even @ even - lower.T @ density_odd @ lower
        left_z_odd = odd.T @ density_odd @ odd - upper.T @ density_even @ upper
        left_z = torch.cat((self.basis @ left_z_even.reshape(-1), self.basis @ left_z_odd.reshape(-1)))
        right_x = (even @ lower.T + upper @ odd.T).reshape(-1)
        left_x = 2 * (even.T @ density_even @ upper + lower.T @ density_odd @ odd).reshape(-1)
        right_y = (even @ lower.T - upper @ odd.T).reshape(-1)
        left_y = -2 * (even.T @ density_even @ upper - lower.T @ density_odd @ odd).reshape(-1)
        same = torch.kron(even.contiguous(), odd.contiguous())
        crossed = torch.kron(upper.contiguous(), lower.contiguous())[:, self.transpose]
        orders = correlation_sequence(same + crossed, right_x, left_x, counts[0])
        densities = correlation_sequence(transfer_even, right_z - magnetization * self.trace, left_z, counts[1])
        y_values = correlation_sequence(same - crossed, right_y, left_y, counts[2])
        energy_excess = -orders[0] - magnetization + 4.0 / math.pi
        return energy_excess, orders, densities, y_values, (density_even, density_odd)

    def errors(self, observables):
        energy, orders, densities, y_values, unused_density = observables
        return (energy / 5e-5, (orders / self.targets_x[:len(orders)] - 1) / 0.025,
                (densities / self.targets_z[:len(densities)] - 1) / 0.1,
                (y_values / self.targets_y[:len(y_values)] - 1) / 0.1)


def concise(report):
    result = {key: report.get(key) for key in ("valid", "passed", "core_score", "worst_family_score", "reason")}
    if "metrics" in report:
        for key, value in report["metrics"].items():
            if not isinstance(value, list):
                result[key] = value
    return result


def validate():
    generator = np.random.default_rng(17)
    tensor = np.load(ROOT.parent / "portfolio" / "state.npz")["A"]
    raw = raw_from_tensor(tensor)
    physics = Physics(raw.shape[-1])
    started = time.monotonic()
    output = physics.observables(raw)
    loss = sum(error.square().mean() for error in physics.errors(output))
    loss.backward()
    elapsed = time.monotonic() - started
    rebuilt = assemble(unpack(raw)).detach().numpy()
    reference = trusted_physics.metrics(rebuilt)
    comparisons = {
        "energy_absolute_difference": abs(output[0].item() - reference["energy_excess"]),
        "order_max_absolute_difference": float(np.max(np.abs(output[1].detach().numpy() - reference["order_correlations"]))),
        "density_max_absolute_difference": float(np.max(np.abs(output[2].detach().numpy() - reference["density_connected_correlations"]))),
        "y_max_absolute_difference": float(np.max(np.abs(output[3].detach().numpy() - reference["y_correlations"]))),
        "forward_backward_seconds": elapsed,
        "initial_v2_score": concise(trusted_physics.score_metrics(reference)),
    }
    direction = torch.tensor(generator.normal(size=raw.shape))
    direction /= torch.linalg.vector_norm(direction)
    analytic = torch.sum(raw.grad * direction).item()
    finite_differences = []
    with torch.no_grad():
        for epsilon in (1e-5, 1e-6, 1e-7):
            plus = sum(error.square().mean() for error in physics.errors(physics.observables(raw + epsilon * direction))).item()
            minus = sum(error.square().mean() for error in physics.errors(physics.observables(raw - epsilon * direction))).item()
            numerical = (plus - minus) / (2 * epsilon)
            finite_differences.append({"epsilon": epsilon, "analytic": analytic, "finite_difference": numerical,
                                       "relative_difference": abs(analytic - numerical) / max(1, abs(analytic))})
    comparisons["gradient_validation"] = finite_differences
    write_json(ROOT / "derivative_validation.json", comparisons)
    print(json.dumps(comparisons, indent=2), flush=True)
    if max(comparisons[key] for key in ("energy_absolute_difference", "order_max_absolute_difference", "density_max_absolute_difference", "y_max_absolute_difference")) > 1e-9:
        raise RuntimeError("Fast contractions disagree with independent checker")


class Runner:
    def __init__(self, args):
        self.args = args
        self.folder = ROOT / args.name
        self.folder.mkdir(parents=True, exist_ok=True)
        self.start = time.monotonic()
        self.deadline = self.start + args.seconds
        tensor = np.load(Path(args.start).resolve())["A"]
        self.raw = raw_from_tensor(tensor)
        if args.noise:
            generator = torch.Generator().manual_seed(args.seed)
            with torch.no_grad():
                self.raw.add_(args.noise * torch.randn(self.raw.shape, generator=generator))
        self.physics = Physics(self.raw.shape[-1])
        self.evaluations = 0
        self.iterations = 0
        self.best_rank = (-1.0, -1.0)
        self.best_report = None
        self.last_loss = None
        self.last_errors = None
        self.checkpoint_index = 0
        write_json(self.folder / "configuration.json", vars(args))

    def checkpoint(self, tag):
        tensor = assemble(unpack(self.raw)).detach().numpy()
        path = self.folder / f"{self.checkpoint_index:04d}_{tag}.npz"
        self.checkpoint_index += 1
        np.savez(path, A=tensor)
        report = trusted_physics.check(path)
        report.update({"elapsed_seconds": time.monotonic() - self.start, "evaluations": self.evaluations,
                       "requested_iterations": self.iterations, "loss": self.last_loss,
                       "normalized_max_errors": self.last_errors, "artifact": str(path.relative_to(ROOT))})
        write_json(path.with_suffix(".score.json"), report)
        summary = concise(report)
        summary.update({key: report[key] for key in ("elapsed_seconds", "evaluations", "requested_iterations", "loss", "normalized_max_errors", "artifact")})
        with (self.folder / "progress.jsonl").open("a") as stream:
            stream.write(json.dumps(summary) + "\n")
        print(json.dumps(summary), flush=True)
        rank = (report.get("worst_family_score", 0), report.get("core_score", 0))
        if rank > self.best_rank:
            self.best_rank = rank
            self.best_report = report
            shutil.copyfile(path, self.folder / "state.npz")
            write_json(self.folder / "score.json", report)
        return report

    def phase(self, counts, iterations, mode, learning_rate=1.0):
        optimizer = torch.optim.LBFGS([self.raw], lr=learning_rate, max_iter=25, max_eval=40,
                                     tolerance_grad=1e-10, tolerance_change=1e-14,
                                     history_size=100, line_search_fn="strong_wolfe")

        def closure():
            if time.monotonic() >= self.deadline:
                raise TimeoutError("portfolio worker budget reached")
            optimizer.zero_grad(set_to_none=True)
            observables = self.physics.observables(self.raw, counts)
            errors = self.physics.errors(observables)
            if mode == "square":
                loss = sum(error.square().mean() for error in errors)
            elif mode == "fourth":
                loss = sum((error.square().mean() + 0.1 * error.pow(4).mean()) for error in errors)
            elif mode == "hinge":
                loss = sum(torch.relu(error.abs() - 0.6).square().mean() + 0.01 * error.square().mean() for error in errors)
            else:
                raise ValueError(mode)
            if self.args.floor_weight:
                eigenvalues = torch.cat([torch.linalg.eigvalsh(density) for density in observables[4]])
                barrier = torch.relu(torch.log(torch.tensor(3e-12)) - torch.log(eigenvalues.clamp_min(1e-17)))
                loss = loss + self.args.floor_weight * barrier.square().mean()
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite optimization loss")
            loss.backward()
            self.evaluations += 1
            self.last_loss = loss.item()
            self.last_errors = [torch.max(torch.abs(error)).item() for error in errors]
            return loss

        for iteration in range(0, iterations, 25):
            optimizer.step(closure)
            self.iterations += 25
            if (iteration + 25) % self.args.check_every == 0 or iteration + 25 >= iterations:
                report = self.checkpoint(f"{counts[0]}_{mode}_{self.iterations:05d}")
                if report.get("passed"):
                    return True
        return False

    def run(self):
        self.checkpoint("initial")
        if self.args.strategy == "curriculum":
            schedule = [((256, 64, 32), 300, "square"), ((512, 128, 64), 500, "square")]
        else:
            schedule = []
        schedule += [((1024, 256, 128), self.args.iterations, "square"),
                     ((1024, 256, 128), self.args.iterations, "fourth"),
                     ((1024, 256, 128), self.args.iterations, "hinge")]
        try:
            for counts, iterations, mode in schedule:
                if self.phase(counts, iterations, mode):
                    break
        except (TimeoutError, FloatingPointError, RuntimeError) as error:
            write_json(self.folder / "termination.json", {"reason": str(error), "elapsed_seconds": time.monotonic() - self.start})
            print(str(error), flush=True)
        finally:
            self.checkpoint("final")
            if self.best_report is not None:
                write_json(self.folder / "summary.json", {"best": concise(self.best_report),
                           "elapsed_seconds": time.monotonic() - self.start, "evaluations": self.evaluations,
                           "sha256": hashlib.sha256((self.folder / "state.npz").read_bytes()).hexdigest()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--name", default="direct17")
    parser.add_argument("--start", default=str(ROOT.parent / "portfolio" / "state.npz"))
    parser.add_argument("--strategy", choices=("direct", "curriculum"), default="direct")
    parser.add_argument("--seconds", type=float, default=1800)
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--check-every", type=int, default=100)
    parser.add_argument("--floor-weight", type=float, default=0.0)
    parser.add_argument("--noise", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    if args.validate:
        validate()
    else:
        Runner(args).run()


if __name__ == "__main__":
    main()
