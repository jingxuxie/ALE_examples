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
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--weight', type=float, default=0.)
    parser.add_argument('--iterations', type=int, default=1000)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input)
    targets = np.concatenate(compiler.targets, axis=1)
    gram_target = targets.conj().T @ targets
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    amplitudes = np.zeros((24, 3))
    if arguments.initial:
        amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
    elif arguments.seed:
        generator = np.random.default_rng(arguments.seed)
        coarse = generator.normal(size=(6, 3))
        amplitudes = .35 * np.column_stack([np.interp(np.linspace(0, 5, 24), np.arange(6), coarse[:, channel]) for channel in range(3)])
    calls = 0
    best = np.inf
    start = time.monotonic()

    def objective(flattened):
        nonlocal calls, best
        amplitudes = flattened.reshape(24, 3)
        forwards = [compiler.forward((amplitudes, member)) for member in range(4)]
        states = np.concatenate([forward[0] for forward in forwards], axis=1)
        delta = states.conj().T @ states - gram_target
        gram_loss = np.sum(abs(delta) ** 2) / 24
        linear_loss = 1 - np.vdot(targets, states).real / 24
        loss = gram_loss + arguments.weight * linear_loss
        adjoints = states @ delta / 6 - arguments.weight * targets / 24
        gradient = sum(compiler.backward(forwards[member][1], adjoints[:, 6 * member:6 * (member + 1)]) for member in range(4))
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
        if loss < best:
            best = loss
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        if calls % 20 == 0:
            print('eval', calls, 'loss', loss, 'gram', gram_loss, 'linear', linear_loss, 'seconds', time.monotonic() - start, flush=True)
        return loss, gradient.ravel()

    result = minimize(objective, amplitudes.ravel(), jac=True, method='L-BFGS-B', options={'maxiter': arguments.iterations, 'ftol': 1e-13, 'gtol': 1e-8, 'maxcor': 30})
    print(result.message, result.fun, flush=True)


if __name__ == '__main__':
    main()
