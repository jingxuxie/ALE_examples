import argparse
import json
import time
from pathlib import Path
from solve import Compiler, np, minimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--initial', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=110)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input)
    targets = np.concatenate(compiler.targets, axis=1)
    eigenvalues, vectors = np.linalg.eigh(targets.conj().T @ targets)
    print('Gram eigenvalues', eigenvalues, flush=True)
    generator = np.random.default_rng(arguments.seed)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    best_amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
    best = np.inf
    start = time.monotonic()
    for trial in range(10):
        amplitudes = best_amplitudes.copy()
        if trial:
            amplitudes += generator.normal(size=(24, 3)) * .2
        values = np.r_[amplitudes.ravel(), np.zeros(4)]
        for regularizer in [.03, .1, 1., 1e6]:
            weighting = (vectors * ((1 + regularizer) / (eigenvalues + regularizer))[None, :]) @ vectors.conj().T / 24
            def objective(parameters):
                amplitudes = parameters[:72].reshape(24, 3)
                phases = np.exp(-1j * parameters[72:])
                forwards = [compiler.forward((amplitudes, member)) for member in range(4)]
                states = np.concatenate([phases[member] * forwards[member][0] for member in range(4)], axis=1)
                residual = states - targets
                adjoint = residual @ weighting
                loss = .5 * np.vdot(residual, adjoint).real
                gradient = np.zeros(76)
                for member in range(4):
                    aligned = adjoint[:, 6 * member:6 * (member + 1)]
                    gradient[:72] += compiler.backward(forwards[member][1], phases[member].conjugate() * aligned).ravel()
                    gradient[72 + member] = np.vdot(aligned, -1j * phases[member] * forwards[member][0]).real
                differences = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
                excessive_jump = np.maximum(abs(differences) - jump_limits, 0)
                loss += .3 * np.sum(excessive_jump ** 2)
                jump_gradient = .6 * excessive_jump * np.sign(differences)
                gradient[:72] += (jump_gradient[:-1] - jump_gradient[1:]).ravel()
                exposure = compiler.duration * np.sum((amplitudes / limits) ** 2)
                excess = max(exposure - 13.5, 0)
                loss += .01 * excess ** 2
                gradient[:72] += (.04 * compiler.duration * excess * amplitudes / limits ** 2).ravel()
                return loss, gradient
            bounds = [(-limit, limit) for step in range(24) for limit in limits] + [(None, None)] * 4
            result = minimize(objective, values, jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': 250, 'ftol': 1e-11, 'gtol': 1e-7, 'maxcor': 30})
            values = result.x
            print('trial', trial, 'regularizer', regularizer, 'loss', result.fun, 'calls', result.nfev, 'seconds', time.monotonic() - start, flush=True)
        if result.fun < best:
            best = result.fun
            best_amplitudes = values[:72].reshape(24, 3)
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': best_amplitudes.tolist()}) + '\n')
        if best < 1e-9:
            print('SOLVED', flush=True)
            break


if __name__ == '__main__':
    main()
