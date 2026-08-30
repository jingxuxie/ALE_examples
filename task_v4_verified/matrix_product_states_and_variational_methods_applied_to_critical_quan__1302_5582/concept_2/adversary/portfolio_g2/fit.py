import argparse
import hashlib
import json
import math
import shutil
import time

from optimize import ROOT, assemble, np, raw_from_tensor, symmetric_basis, torch, trusted_physics, unpack, write_json


def powers_of(transfer, count):
    powers = [transfer]
    for index in range(1, max(1, (count - 1).bit_length())):
        powers.append(powers[-1] @ powers[-1])
    return powers


def environments(powers, initial, count):
    vectors = initial[:, None]
    for power in powers:
        if vectors.shape[1] >= count:
            break
        remaining = min(vectors.shape[1], count - vectors.shape[1])
        vectors = torch.cat((vectors, power @ vectors[:, :remaining]), dim=1)
    return vectors


class CompositePhysics:
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
        self.targets_c = torch.tensor([trusted_physics.exact_composite_covariance(quartet) for quartet in trusted_physics.COMPOSITE_QUARTETS])
        self.lengths = torch.tensor([16, 32, 64, 96])
        self.left_masks = [(((self.lengths - 1) & (1 << bit)) != 0)[:, None] for bit in range(7)]
        lengths = [16, 32, 64, 96]
        gaps = [32, 64, 96, 128]
        self.quartet_indices = tuple(torch.tensor(indices) for indices in zip(*[(gaps.index(quartet[2] - quartet[1]), lengths.index(quartet[1]), lengths.index(quartet[3] - quartet[2])) for quartet in trusted_physics.COMPOSITE_QUARTETS]))

    def pack(self, first, second):
        return torch.cat((first.reshape(*first.shape[:-2], -1) @ self.basis.T,
                          second.reshape(*second.shape[:-2], -1) @ self.basis.T), dim=-1)

    def observables(self, raw):
        even, upper, odd, lower = unpack(raw)
        matrices = torch.stack((even, upper, lower, odd))
        products = torch.einsum('bij,bkl->bikjl', matrices, matrices).reshape(4, self.half**2, self.half**2)
        projected = self.basis @ products @ self.basis.T
        transfer_even = torch.cat((torch.cat((projected[0], projected[1]), 1), torch.cat((projected[2], projected[3]), 1)), 0)
        system = self.identity - transfer_even.T + self.source[:, None] * self.trace[None, :]
        density_vector = torch.linalg.solve(system, self.source)
        density_even = (self.basis.T @ density_vector[:self.sector_size]).reshape(self.half, self.half)
        density_odd = (self.basis.T @ density_vector[self.sector_size:]).reshape(self.half, self.half)
        right_z = self.pack(even @ even.T - upper @ upper.T, odd @ odd.T - lower @ lower.T)
        magnetization = density_vector @ right_z
        left_z = self.pack(even.T @ density_even @ even - lower.T @ density_odd @ lower,
                           odd.T @ density_odd @ odd - upper.T @ density_even @ upper)
        right_x = (even @ lower.T + upper @ odd.T).reshape(-1)
        right_y = (even @ lower.T - upper @ odd.T).reshape(-1)
        left_x = 2 * (even.T @ density_even @ upper + lower.T @ density_odd @ odd).reshape(-1)
        left_y = -2 * (even.T @ density_even @ upper - lower.T @ density_odd @ odd).reshape(-1)
        direct = torch.einsum('ij,kl->ikjl', even, odd).reshape(self.half**2, self.half**2)
        exchange = torch.einsum('ij,kl->ikjl', upper, lower).reshape(self.half**2, self.half**2)[:, self.transpose]
        powers_x = powers_of(direct + exchange, 1024)
        powers_y = powers_of(direct - exchange, 128)
        powers_z = powers_of(transfer_even, 256)
        vectors_x = environments(powers_x, right_x, 1024)
        orders = left_x @ vectors_x
        densities = left_z @ environments(powers_z, right_z - magnetization * self.trace, 256)
        y_correlations = left_y @ environments(powers_y, right_y, 128)
        right_odd = vectors_x[:, self.lengths - 1].T.reshape(4, self.half, self.half)
        right_even = self.pack(even @ right_odd @ upper.T + upper @ right_odd.transpose(-1, -2) @ even.T,
                               lower @ right_odd @ odd.T + odd @ right_odd.transpose(-1, -2) @ lower.T)
        right_centered = (right_even - orders[self.lengths - 1, None] * self.trace[None, :]).T
        left_odd = (left_x / 2)[None, :].expand(4, -1)
        for power, mask in zip(powers_x, self.left_masks):
            left_odd = torch.where(mask, left_odd @ power, left_odd)
        left_odd = left_odd.reshape(4, self.half, self.half)
        left_even = self.pack(even.T @ left_odd @ lower + lower.T @ left_odd.transpose(-1, -2) @ even,
                              upper.T @ left_odd @ odd + odd.T @ left_odd.transpose(-1, -2) @ upper)
        gap_32 = right_centered
        for power in powers_z[:5]:
            gap_32 = power @ gap_32
        gap_64 = powers_z[5] @ gap_32
        gap_96 = powers_z[6] @ gap_32
        gap_128 = powers_z[6] @ gap_64
        covariances = torch.stack([left_even @ environment for environment in (gap_32, gap_64, gap_96, gap_128)])[self.quartet_indices]
        energy = 4 / math.pi - orders[0] - magnetization
        return energy, orders, densities, y_correlations, covariances, (density_even, density_odd)

    def errors(self, output):
        return (output[0].reshape(1) / 5e-5, (output[1] / self.targets_x - 1) / .025,
                (output[2] / self.targets_z - 1) / .1, (output[3] / self.targets_y - 1) / .1,
                (output[4] / self.targets_c - 1) / .01)


def concise(report):
    result = {key: report.get(key) for key in ('valid', 'passed', 'core_score', 'worst_family_score', 'error')}
    metrics = report.get('metrics', {})
    result.update({key: metrics.get(key) for key in ('energy_excess', 'order_max_relative_error', 'density_max_relative_error', 'y_max_relative_error', 'composite_order_max_relative_error', 'composite_order_worst_quartet', 'correlation_length', 'stationary_min_eigenvalue')})
    return result


def validate(start):
    tensor = np.load(start, allow_pickle=False)['A']
    raw = raw_from_tensor(tensor)
    physics = CompositePhysics(raw.shape[-1])
    started = time.monotonic()
    output = physics.observables(raw)
    loss = sum(error.square().mean() for error in physics.errors(output))
    loss.backward()
    elapsed = time.monotonic() - started
    rebuilt = assemble(unpack(raw)).detach().numpy()
    reference = trusted_physics.metrics(rebuilt)
    differences = {'energy': abs(output[0].item() - reference['energy_excess'])}
    for index, key in enumerate(('order_correlations', 'density_connected_correlations', 'y_correlations', 'composite_order_covariances'), start=1):
        differences[key] = float(np.max(np.abs(output[index].detach().numpy() - reference[key])))
    generator = torch.Generator().manual_seed(983)
    direction = torch.randn(raw.shape, generator=generator)
    direction /= torch.linalg.vector_norm(direction)
    analytic = torch.sum(raw.grad * direction).item()
    checks = []
    with torch.no_grad():
        for epsilon in (1e-5, 1e-6, 1e-7):
            plus = sum(error.square().mean() for error in physics.errors(physics.observables(raw + epsilon * direction))).item()
            minus = sum(error.square().mean() for error in physics.errors(physics.observables(raw - epsilon * direction))).item()
            numerical = (plus - minus) / (2 * epsilon)
            checks.append({'epsilon': epsilon, 'analytic': analytic, 'numerical': numerical, 'relative_error': abs(analytic - numerical) / max(1, abs(analytic))})
    record = {'source': str(start), 'source_sha256': hashlib.sha256(start.read_bytes()).hexdigest(),
              'tensor_imaginary_max': float(np.max(np.abs(np.imag(tensor)))), 'absolute_differences': differences,
              'forward_backward_seconds': elapsed, 'gradient_checks': checks, 'initial_v3_score': concise(trusted_physics.score_metrics(reference))}
    write_json(ROOT / 'derivative_validation.json', record)
    print(json.dumps(record, indent=2), flush=True)
    if max(differences.values()) > 1e-9 or min(check['relative_error'] for check in checks) > 2e-4:
        raise RuntimeError('Independent contraction or gradient validation failed')


class PortfolioStop(Exception):
    pass


class Runner:
    def __init__(self, args):
        self.args = args
        self.folder = ROOT / args.name
        self.folder.mkdir(parents=True, exist_ok=True)
        self.started = time.monotonic()
        self.deadline = self.started + args.seconds
        self.base = raw_from_tensor(np.load(args.start, allow_pickle=False)['A']).detach()
        if args.noise:
            generator = torch.Generator().manual_seed(args.seed)
            self.base = self.base + args.noise * torch.randn(self.base.shape, generator=generator)
        self.physics = CompositePhysics(self.base.shape[-1])
        with torch.no_grad():
            densities = self.physics.observables(self.base)[5]
            scales = []
            for density in densities:
                eigenvalues, vectors = torch.linalg.eigh(density)
                scales.append((vectors * eigenvalues.clamp_min(1e-8).pow(-args.precondition / 2)) @ vectors.T)
            self.scales = torch.stack(scales)
        self.parameters = torch.zeros_like(self.base, requires_grad=True)
        self.evaluations = 0
        self.iterations = 0
        self.checkpoint_index = 0
        self.best_rank = (-1, -1.0, -1.0)
        self.best_report = None
        self.last_loss = None
        self.last_errors = None
        self.fast_best = float('inf')
        self.last_pass_check = -100
        write_json(self.folder / 'configuration.json', vars(args))

    def raw(self):
        return self.base + self.parameters @ self.scales

    def checkpoint(self, tag, tensor=None):
        if tensor is None:
            tensor = assemble(unpack(self.raw())).detach().numpy()
        path = self.folder / f'{self.checkpoint_index:04d}_{tag}.npz'
        self.checkpoint_index += 1
        np.savez(path, A=tensor)
        report = trusted_physics.check(path)
        report.update({'elapsed_seconds': time.monotonic() - self.started, 'evaluations': self.evaluations,
                       'requested_iterations': self.iterations, 'loss': self.last_loss,
                       'normalized_max_errors': self.last_errors, 'artifact': str(path.relative_to(ROOT))})
        write_json(path.with_suffix('.score.json'), report)
        summary = concise(report)
        summary.update({key: report[key] for key in ('elapsed_seconds', 'evaluations', 'requested_iterations', 'loss', 'normalized_max_errors', 'artifact')})
        with (self.folder / 'progress.jsonl').open('a') as stream:
            stream.write(json.dumps(summary) + '\n')
        print(json.dumps(summary), flush=True)
        rank = (int(report.get('passed', False)), report.get('worst_family_score', 0), report.get('core_score', 0))
        if rank > self.best_rank:
            self.best_rank = rank
            self.best_report = report
            shutil.copyfile(path, self.folder / 'state.npz')
            write_json(self.folder / 'score.json', report)
        if report.get('passed'):
            write_json(ROOT / 'PASS_FOUND.json', {'worker': self.args.name, 'artifact': str(path.relative_to(ROOT)), 'trusted_check_passed': True, 'full_evaluate_py_still_required': True})
        return report

    def phase(self, mode):
        optimizer = torch.optim.LBFGS([self.parameters], lr=1.0, max_iter=25, max_eval=40,
                                     tolerance_grad=1e-10, tolerance_change=1e-14, history_size=100, line_search_fn='strong_wolfe')

        def closure():
            if (ROOT / 'STOP').exists() or (ROOT / 'PASS_FOUND.json').exists():
                raise PortfolioStop('Private stop marker observed')
            if time.monotonic() >= self.deadline:
                raise PortfolioStop('Private worker time budget reached')
            optimizer.zero_grad(set_to_none=True)
            output = self.physics.observables(self.raw())
            errors = self.physics.errors(output)
            if mode == 'square':
                loss = sum(error.square().mean() for error in errors)
            elif mode == 'fourth':
                loss = sum(error.square().mean() + .1 * error.pow(4).mean() for error in errors)
            else:
                loss = sum(torch.relu(error.abs() - .6).square().mean() + .01 * error.square().mean() for error in errors)
            if self.args.floor_weight:
                eigenvalues = torch.cat([torch.linalg.eigvalsh(density) for density in output[5]])
                barrier = torch.relu(math.log(3e-12) - torch.log(eigenvalues.clamp_min(1e-17)))
                loss = loss + self.args.floor_weight * barrier.square().mean()
            if not torch.isfinite(loss):
                raise FloatingPointError('Nonfinite objective')
            loss.backward()
            self.evaluations += 1
            self.last_loss = loss.item()
            self.last_errors = [error.detach().abs().max().item() for error in errors]
            worst = max(self.last_errors)
            if worst < self.fast_best:
                self.fast_best = worst
                np.savez(self.folder / 'fast_best.npz', A=assemble(unpack(self.raw())).detach().numpy())
                write_json(self.folder / 'fast_best.json', {'normalized_max_errors': self.last_errors, 'evaluation': self.evaluations, 'loss': self.last_loss, 'elapsed_seconds': time.monotonic() - self.started})
            if worst < .98 and self.evaluations - self.last_pass_check >= 20:
                self.last_pass_check = self.evaluations
                if self.checkpoint('candidate').get('passed'):
                    raise PortfolioStop('Actual trusted v3 check passed')
            return loss

        for iteration in range(0, self.args.iterations, 25):
            optimizer.step(closure)
            self.iterations += 25
            if (iteration + 25) % self.args.check_every == 0 or iteration + 25 >= self.args.iterations:
                if self.checkpoint(f'{mode}_{self.iterations:05d}').get('passed'):
                    return True
        return False

    def run(self):
        self.checkpoint('initial')
        try:
            for mode in ('square', 'fourth', 'hinge'):
                if self.phase(mode):
                    break
        except (PortfolioStop, FloatingPointError, RuntimeError) as error:
            write_json(self.folder / 'termination.json', {'reason': str(error), 'elapsed_seconds': time.monotonic() - self.started})
            print(str(error), flush=True)
        finally:
            self.checkpoint('final')
            fast_path = self.folder / 'fast_best.npz'
            if fast_path.exists():
                self.checkpoint('fast_best', np.load(fast_path, allow_pickle=False)['A'])
            if self.best_report is not None:
                write_json(self.folder / 'summary.json', {'best': concise(self.best_report), 'elapsed_seconds': time.monotonic() - self.started,
                           'evaluations': self.evaluations, 'sha256': hashlib.sha256((self.folder / 'state.npz').read_bytes()).hexdigest()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--start', default=str(ROOT.parents[1] / 'champions' / 'generation_2' / 'state.npz'))
    parser.add_argument('--name', default='champion_plain')
    parser.add_argument('--seconds', type=float, default=1600)
    parser.add_argument('--iterations', type=int, default=1800)
    parser.add_argument('--check-every', type=int, default=100)
    parser.add_argument('--precondition', type=float, default=0)
    parser.add_argument('--floor-weight', type=float, default=.01)
    parser.add_argument('--noise', type=float, default=0)
    parser.add_argument('--seed', type=int, default=17)
    args = parser.parse_args()
    if args.validate:
        from pathlib import Path
        validate(Path(args.start))
    else:
        Runner(args).run()


if __name__ == '__main__':
    main()
