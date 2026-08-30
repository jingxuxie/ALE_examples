import argparse
import json
import time
from pathlib import Path
from solve import Compiler, np, minimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--initial', type=Path)
    parser.add_argument('--seed', type=int, default=20)
    parser.add_argument('--trials', type=int, default=20)
    parser.add_argument('--members', default='0,2')
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input)
    generator = np.random.default_rng(arguments.seed)
    members = [int(member) for member in arguments.members.split(',')]
    with np.load(arguments.input / 'hamiltonians.npz') as archive:
        basis = archive['basis']
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    partitions = {}
    for count in [2, 3, 4, 6, 8]:
        specifications = []
        for start in ([0] if count == 8 else [0, 2, 4, 6]):
            selected = [(start + offset) % 8 for offset in range(count)]
            rest = [site for site in range(8) if site not in selected]
            row_bits = sum(((basis >> site) & 1) << offset for offset, site in enumerate(selected))
            column_bits = sum((((basis >> site) & 1) << offset for offset, site in enumerate(rest)), np.zeros_like(basis))
            rows = row_bits[:, None] * 6 + np.arange(6)[None, :]
            columns = np.broadcast_to(column_bits[:, None], (70, 6))
            target_matrices = []
            for target in compiler.targets:
                matrix = np.zeros((6 * 2 ** count, 2 ** (8 - count)), dtype=complex)
                matrix[rows, columns] = target
                target_matrices.append((matrix, np.sum(abs(matrix.conj().T @ matrix) ** 2)))
            specifications.append((rows, columns, target_matrices))
        partitions[count] = specifications
    best = np.inf
    best_amplitudes = np.zeros((24, 3))
    start_time = time.monotonic()

    for trial in range(arguments.trials):
        if trial == 0 and arguments.initial:
            amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
        elif trial == 0:
            amplitudes = np.zeros((24, 3))
        else:
            coarse = generator.normal(size=(6, 3))
            amplitudes = .4 * np.column_stack([np.interp(np.linspace(0, 5, 24), np.arange(6), coarse[:, channel]) for channel in range(3)])
            if trial % 2 == 0:
                amplitudes = best_amplitudes + amplitudes * .7
        for count in [2, 3, 4, 6, 8]:
            calls = 0
            factor = 1 + 2 ** (8 - count) / (6 * 2 ** count)
            def objective(flattened):
                nonlocal calls
                amplitudes = flattened.reshape(24, 3)
                loss = 0.
                gradient = np.zeros_like(amplitudes)
                for member in members:
                    states, records = compiler.forward((amplitudes, member))
                    adjoint = np.zeros_like(states)
                    for rows, columns, targets in partitions[count]:
                        target, norm = targets[member]
                        matrix = np.zeros_like(target)
                        matrix[rows, columns] = states
                        gram = matrix.conj().T @ matrix
                        cross = target.conj().T @ matrix
                        loss += factor * (np.sum(abs(gram) ** 2) + norm - 2 * np.sum(abs(cross) ** 2)) / (2 * norm * len(members) * len(partitions[count]))
                        derivative = 2 * factor * (matrix @ gram - target @ cross) / (norm * len(members) * len(partitions[count]))
                        adjoint += derivative[rows, columns]
                    gradient += compiler.backward(records, adjoint)
                excessive = np.maximum(abs(amplitudes) - limits, 0)
                loss += .3 * np.sum(excessive ** 2)
                gradient += .6 * excessive * np.sign(amplitudes)
                differences = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
                excessive_jump = np.maximum(abs(differences) - jump_limits, 0)
                loss += .3 * np.sum(excessive_jump ** 2)
                jump_gradient = .6 * excessive_jump * np.sign(differences)
                gradient += jump_gradient[:-1] - jump_gradient[1:]
                exposure = compiler.duration * np.sum((amplitudes / limits) ** 2)
                excess = max(exposure - 13.5, 0)
                loss += .01 * excess ** 2
                gradient += .04 * compiler.duration * excess * amplitudes / limits ** 2
                calls += 1
                return loss, gradient.ravel()
            if trial == 0 and count == 2:
                direction = generator.normal(size=72)
                direction /= np.linalg.norm(direction)
                value, derivative = objective(amplitudes.ravel())
                positive = objective(amplitudes.ravel() + 1e-5 * direction)[0]
                negative = objective(amplitudes.ravel() - 1e-5 * direction)[0]
                print('gradient', derivative @ direction, (positive - negative) / 2e-5, flush=True)
            result = minimize(objective, amplitudes.ravel(), jac=True, method='L-BFGS-B', options={'maxiter': 250, 'ftol': 1e-11, 'gtol': 1e-7, 'maxcor': 25})
            amplitudes = result.x.reshape(24, 3)
            print('trial', trial, 'sites', count, 'loss', result.fun, 'calls', calls, 'seconds', time.monotonic() - start_time, flush=True)
            if count == 8 and result.fun < best:
                best = result.fun
                best_amplitudes = amplitudes.copy()
                arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        if best < 1e-9:
            print('SOLVED', flush=True)
            break


if __name__ == '__main__':
    main()
