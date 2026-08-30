import argparse
import json
import time
from pathlib import Path
from solve import Compiler, np, minimize
from native import Native
from scipy.ndimage import gaussian_filter1d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--column', type=int, default=2)
    parser.add_argument('--member', type=int, default=1)
    parser.add_argument('--seed', type=int, default=90)
    parser.add_argument('--penalty', type=float, default=1.)
    parser.add_argument('--members')
    parser.add_argument('--dc', type=float, default=0.)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input)
    full = Native(compiler)
    compiler.initial = compiler.initial[:, arguments.column:arguments.column + 1].copy()
    compiler.targets = compiler.targets[:, :, arguments.column:arguments.column + 1].copy()
    native = Native(compiler, library_name='propagate_one.so')
    generator = np.random.default_rng(arguments.seed)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    best_state = np.inf
    best_full = np.inf
    best_amplitudes = np.zeros((24, 3))
    start = time.monotonic()
    bounds = [(-limit, limit) for step in range(24) for limit in limits]
    members = [arguments.member] if arguments.members is None else [int(member) for member in arguments.members.split(',')]

    def objective(flattened):
        amplitudes = flattened.reshape(24, 3)
        loss, gradient = native.objective(amplitudes, members, 'fidelity')
        differences = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
        excessive_jump = np.maximum(abs(differences) - jump_limits, 0)
        loss += arguments.penalty * .3 * np.sum(excessive_jump ** 2)
        jump_gradient = arguments.penalty * .6 * excessive_jump * np.sign(differences)
        gradient += jump_gradient[:-1] - jump_gradient[1:]
        exposure = compiler.duration * np.sum((amplitudes / limits) ** 2)
        excess = max(exposure - 13.5, 0)
        loss += arguments.penalty * .01 * excess ** 2
        gradient += arguments.penalty * .04 * compiler.duration * excess * amplitudes / limits ** 2
        return loss, gradient.ravel()

    for trial in range(2000):
        if trial == 0:
            amplitudes = np.zeros((24, 3))
        else:
            amplitudes = gaussian_filter1d(generator.normal(size=(24, 3)), generator.uniform(.3, 2.5), axis=0)
            amplitudes *= generator.uniform(.3, .65) / np.sqrt(np.mean(amplitudes ** 2))
            if trial % 3 == 2:
                amplitudes = best_amplitudes + amplitudes * generator.uniform(.3, .8)
            elif arguments.dc:
                amplitudes = amplitudes * .5 + generator.uniform(-arguments.dc, arguments.dc, size=(1, 3))
        result = minimize(objective, amplitudes.ravel(), jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': 160, 'ftol': 1e-10, 'gtol': 1e-7, 'maxcor': 25})
        if result.fun < best_state or result.fun < .05:
            result = minimize(objective, result.x, jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': 400, 'ftol': 1e-13, 'gtol': 1e-8, 'maxcor': 30})
        amplitudes = result.x.reshape(24, 3)
        if result.fun < best_state:
            best_state = result.fun
            best_amplitudes = amplitudes.copy()
            arguments.output.with_name(arguments.output.stem + '_state.json').write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        full_loss = full.objective(amplitudes, [0, 1, 2, 3], 'fidelity')[0]
        if full_loss < .65:
            def full_objective(values):
                loss, gradient = full.objective(values.reshape(24, 3), [0, 1, 2, 3], 'fidelity')
                return loss, gradient.ravel()
            refined = minimize(full_objective, amplitudes.ravel(), jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': 500, 'ftol': 1e-13, 'gtol': 1e-8, 'maxcor': 30})
            full_loss = refined.fun
            amplitudes = refined.x.reshape(24, 3)
        if full_loss < best_full:
            best_full = full_loss
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        print('trial', trial, 'state loss', result.fun, 'best state', best_state, 'full loss', full_loss, 'best full', best_full, 'seconds', time.monotonic() - start, flush=True)
        if best_full < 1e-10:
            print('SOLVED', flush=True)
            break


if __name__ == '__main__':
    main()
