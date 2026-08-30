import argparse
import json
import time
from pathlib import Path
from solve import Compiler, np
from scipy.optimize import least_squares


def state_jacobian(compiler, records):
    dimension = compiler.initial.shape[0]
    post = np.eye(dimension, dtype=complex)
    jacobian = np.empty((dimension, 6, 72), dtype=complex)
    for step in range(23, -1, -1):
        energies, vectors, phases, before = records[step]
        differences = energies[:, None] - energies[None, :]
        divided = (-1j * compiler.duration) * np.exp(-0.5j * compiler.duration * (energies[:, None] + energies[None, :]))
        divided *= np.sinc(compiler.duration * differences / (2 * np.pi))
        rotated = vectors.conj().T @ (compiler.controls @ vectors)
        local = (rotated * divided[None, :, :]) @ before
        after = post @ vectors
        derivatives = after @ local
        jacobian[:, :, 3 * step:3 * step + 3] = derivatives.transpose(1, 2, 0)
        post = (after * phases[None, :]) @ vectors.conj().T
    return jacobian


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--initial', type=Path)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--trials', type=int, default=20)
    parser.add_argument('--gram', action='store_true')
    parser.add_argument('--all', action='store_true')
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input)
    generator = np.random.default_rng(arguments.seed)
    limits = np.tile(compiler.spec['amplitude_limits'], 24)
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    difference_matrix = np.diff(np.vstack((np.zeros((1, 24)), np.eye(24), np.zeros((1, 24)))), axis=0)
    jump_matrix = np.kron(difference_matrix, np.eye(3))
    target_gram = np.concatenate(compiler.targets, axis=1)
    target_gram = target_gram.conj().T @ target_gram
    members = list(range(4)) if arguments.gram or arguments.all else [1]
    cached = None
    forwards = None
    calls = 0
    best = np.inf
    best_amplitudes = np.zeros((24, 3))
    start = time.monotonic()

    def residual(parameters):
        nonlocal cached, forwards, calls, best, best_amplitudes
        cached = parameters.copy()
        amplitudes = parameters.reshape(24, 3)
        forwards = [compiler.forward((amplitudes, member)) for member in members]
        if arguments.gram:
            states = np.concatenate([forward[0] for forward in forwards], axis=1)
            error = (states.conj().T @ states - target_gram).ravel() / np.sqrt(12)
        else:
            error = np.concatenate([(forward[0] - compiler.targets[member]).ravel() for member, forward in zip(members, forwards)]) / np.sqrt(6 * len(members))
        differences = jump_matrix @ parameters
        jumps = np.maximum(abs(differences.reshape(25, 3)) - jump_limits, 0).ravel()
        exposure = compiler.duration * np.sum((parameters / limits) ** 2)
        excessive = np.maximum(abs(parameters) - limits, 0)
        result = np.concatenate((error.real, error.imag, np.sqrt(.6) * excessive, np.sqrt(.6) * jumps, [np.sqrt(.02) * max(exposure - 13.5, 0)]))
        loss = np.dot(result, result) / 2
        calls += 1
        if loss < best:
            best = loss
            best_amplitudes = amplitudes.copy()
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        if calls % 20 == 0:
            print('eval', calls, 'loss', loss, 'best', best, 'seconds', time.monotonic() - start, flush=True)
        return result

    def jacobian(parameters):
        if cached is None or not np.array_equal(cached, parameters):
            residual(parameters)
        derivatives = [state_jacobian(compiler, forward[1]) for forward in forwards]
        if arguments.gram:
            states = np.concatenate([forward[0] for forward in forwards], axis=1)
            derivatives = np.concatenate(derivatives, axis=1)
            delta = np.einsum('ai,ajp->ijp', states.conj(), derivatives)
            derivative = (delta + delta.conj().transpose(1, 0, 2)).reshape(-1, 72) / np.sqrt(12)
        else:
            derivative = np.concatenate([value.reshape(-1, 72) for value in derivatives], axis=0) / np.sqrt(6 * len(members))
        differences = jump_matrix @ parameters
        active_jumps = (abs(differences) > np.tile(jump_limits, 25)) * np.sign(differences)
        amplitude_jacobian = np.diag((abs(parameters) > limits) * np.sign(parameters))
        jump_jacobian = active_jumps[:, None] * jump_matrix
        exposure = compiler.duration * np.sum((parameters / limits) ** 2)
        exposure_jacobian = 2 * compiler.duration * parameters[None, :] / limits ** 2 * (exposure > 13.5)
        return np.vstack((derivative.real, derivative.imag, np.sqrt(.6) * amplitude_jacobian, np.sqrt(.6) * jump_jacobian, np.sqrt(.02) * exposure_jacobian))

    for trial in range(arguments.trials):
        if trial == 0 and arguments.initial:
            amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
        elif trial == 0:
            amplitudes = np.zeros((24, 3))
        else:
            coarse = generator.normal(size=(8, 3))
            amplitudes = .4 * np.column_stack([np.interp(np.linspace(0, 7, 24), np.arange(8), coarse[:, channel]) for channel in range(3)])
            if trial % 2:
                amplitudes = best_amplitudes + amplitudes * .5
        result = least_squares(residual, amplitudes.ravel(), jac=jacobian, max_nfev=240, ftol=1e-11, xtol=1e-10, gtol=1e-8)
        print('trial', trial, 'loss', result.cost, 'message', result.message, 'seconds', time.monotonic() - start, flush=True)
        if result.cost < 1e-10:
            break


if __name__ == '__main__':
    main()
