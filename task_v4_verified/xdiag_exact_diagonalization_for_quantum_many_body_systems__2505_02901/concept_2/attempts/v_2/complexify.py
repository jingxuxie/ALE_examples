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
    parser.add_argument('--seed', type=int, default=60)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input)
    native = Native(compiler)
    generator = np.random.default_rng(arguments.seed)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    best_amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
    best = np.inf
    start = time.monotonic()
    for trial in range(20):
        amplitudes = best_amplitudes.copy()
        if trial:
            amplitudes += generator.normal(size=(24, 3)) * generator.uniform(.1, .4)
        parameters = np.r_[amplitudes.ravel(), np.zeros(72)]
        for penalty in [.03, .1, .3, 1., 3., 10., 30., 100.]:
            def objective(values):
                loss, gradient = native.complex_objective(values, [0, 1, 2, 3])
                amplitudes = values[:72].reshape(24, 3)
                excessive = np.maximum(abs(amplitudes) - limits, 0)
                loss += .3 * np.sum(excessive ** 2)
                gradient[:72] += (.6 * excessive * np.sign(amplitudes)).ravel()
                differences = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
                excessive_jump = np.maximum(abs(differences) - jump_limits, 0)
                loss += .3 * np.sum(excessive_jump ** 2)
                jump_gradient = .6 * excessive_jump * np.sign(differences)
                gradient[:72] += (jump_gradient[:-1] - jump_gradient[1:]).ravel()
                exposure = compiler.duration * np.sum((amplitudes / limits) ** 2)
                excess = max(exposure - 13.5, 0)
                loss += .01 * excess ** 2
                gradient[:72] += (.04 * compiler.duration * excess * amplitudes / limits ** 2).ravel()
                loss += penalty * np.sum(values[72:] ** 2)
                gradient[72:] += 2 * penalty * values[72:]
                return loss, gradient
            bounds = [(-limit, limit) for step in range(24) for limit in limits] + [(-.3, .3)] * 72
            result = minimize(objective, parameters, jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': 160, 'ftol': 1e-10, 'gtol': 1e-7, 'maxcor': 30})
            parameters = result.x
            print('trial', trial, 'penalty', penalty, 'loss', result.fun, 'imaginary', np.linalg.norm(parameters[72:]), 'calls', result.nfev, 'seconds', time.monotonic() - start, flush=True)
        amplitudes = parameters[:72].reshape(24, 3)
        loss = native.objective(amplitudes, [0, 1, 2, 3], 'aligned')[0]
        if loss < best:
            best = loss
            best_amplitudes = amplitudes.copy()
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        if best < 1e-9:
            print('SOLVED', flush=True)
            break


if __name__ == '__main__':
    main()
