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
    parser.add_argument('--seed', type=int, default=50)
    parser.add_argument('--trials', type=int, default=25)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input, 'aligned')
    desired = compiler.targets.copy()
    generator = np.random.default_rng(arguments.seed)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    start = time.monotonic()
    best = np.inf
    best_amplitudes = np.zeros((24, 3))

    for trial in range(arguments.trials):
        if trial == 0:
            amplitudes = np.zeros((24, 3))
        else:
            coarse = generator.normal(size=(8, 3))
            amplitudes = .4 * np.column_stack([np.interp(np.linspace(0, 7, 24), np.arange(8), coarse[:, channel]) for channel in range(3)])
            if trial % 3 == 2:
                amplitudes = best_amplitudes + amplitudes * .5
        reference = np.array([compiler.forward((amplitudes, member))[0] for member in range(4)])
        destination = desired.copy()
        for member in range(4):
            phase = -np.angle(np.vdot(reference[member], destination[member]))
            if trial % 3 == 1:
                phase = generator.uniform(-np.pi, np.pi)
            destination[member] *= np.exp(1j * phase)
        for fraction in [.1, .2, .35, .5, .65, .8, 1.]:
            for member in range(4):
                blend = (1 - fraction) * reference[member] + fraction * destination[member]
                left, singular, right = np.linalg.svd(blend, full_matrices=False)
                compiler.targets[member] = left @ right
            fast = Native(compiler)
            def objective(flattened):
                amplitudes = flattened.reshape(24, 3)
                loss, gradient = fast.objective(amplitudes, [0, 1, 2, 3], 'aligned')
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
                return loss, gradient.ravel()
            result = minimize(objective, amplitudes.ravel(), jac=True, method='L-BFGS-B', options={'maxiter': 150, 'ftol': 1e-11, 'gtol': 1e-7, 'maxcor': 25})
            amplitudes = result.x.reshape(24, 3)
            print('trial', trial, 'fraction', fraction, 'loss', result.fun, 'calls', result.nfev, 'seconds', time.monotonic() - start, flush=True)
        if result.fun < best:
            best = result.fun
            best_amplitudes = amplitudes.copy()
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        if best < 1e-9:
            print('SOLVED', flush=True)
            break


if __name__ == '__main__':
    main()
