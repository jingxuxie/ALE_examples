import argparse
import json
import time
from pathlib import Path
from solve import Compiler, np, minimize
from native import Native


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--initial', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=80)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input, 'aligned')
    full = Native(compiler)
    generator = np.random.default_rng(arguments.seed)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    initial, targets = compiler.initial.copy(), compiler.targets.copy()
    models = []
    for column in range(6):
        compiler.initial = initial[:, column:column + 1].copy()
        compiler.targets = targets[:, :, column:column + 1].copy()
        models.append(Native(compiler, library_name='propagate_one.so'))
    compiler.initial, compiler.targets = initial, targets
    best_amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
    best = np.inf
    start = time.monotonic()
    for trial in range(10):
        amplitudes = np.tile(best_amplitudes[None, :, :], (24, 1, 1))
        if trial:
            amplitudes += generator.normal(size=(1, 24, 3)) * generator.uniform(.1, .4)
        for coupling in [.0003, .001, .003, .01, .03, .1, .3, 1., 3.]:
            def objective(flattened):
                amplitudes = flattened.reshape(24, 24, 3)
                loss = 0.
                gradient = np.empty_like(amplitudes)
                for member in range(4):
                    for column in range(6):
                        index = 6 * member + column
                        local_loss, gradient[index] = models[column].objective(amplitudes[index], [member], 'aligned')
                        loss += local_loss
                differences = amplitudes - np.mean(amplitudes, axis=0)[None, :, :]
                loss += coupling * np.sum(differences ** 2)
                gradient += 2 * coupling * differences
                excessive = np.maximum(abs(amplitudes) - limits, 0)
                loss += .3 * np.sum(excessive ** 2)
                gradient += .6 * excessive * np.sign(amplitudes)
                jumps = np.diff(np.concatenate((np.zeros((24, 1, 3)), amplitudes, np.zeros((24, 1, 3))), axis=1), axis=1)
                excessive_jump = np.maximum(abs(jumps) - jump_limits, 0)
                loss += .3 * np.sum(excessive_jump ** 2)
                jump_gradient = .6 * excessive_jump * np.sign(jumps)
                gradient += jump_gradient[:, :-1] - jump_gradient[:, 1:]
                exposure = compiler.duration * np.sum((amplitudes / limits) ** 2, axis=(1, 2))
                excess = np.maximum(exposure - 13.5, 0)
                loss += .01 * np.sum(excess ** 2)
                gradient += .04 * compiler.duration * excess[:, None, None] * amplitudes / limits ** 2
                return loss / 24, gradient.ravel() / 24
            bounds = [(-limit, limit) for member in range(24) for step in range(24) for limit in limits]
            result = minimize(objective, amplitudes.ravel(), jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': 170, 'ftol': 1e-10, 'gtol': 1e-7, 'maxcor': 30})
            amplitudes = result.x.reshape(24, 24, 3)
            common = np.mean(amplitudes, axis=0)
            common_loss = full.objective(common, [0, 1, 2, 3], 'fidelity')[0]
            print('trial', trial, 'coupling', coupling, 'loss', result.fun, 'common loss', common_loss, 'spread', np.sqrt(np.mean((amplitudes - common) ** 2)), 'seconds', time.monotonic() - start, flush=True)
            if common_loss < best:
                best = common_loss
                best_amplitudes = common.copy()
                arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': common.tolist()}) + '\n')
        if best < 1e-9:
            print('SOLVED', flush=True)
            break


if __name__ == '__main__':
    main()
