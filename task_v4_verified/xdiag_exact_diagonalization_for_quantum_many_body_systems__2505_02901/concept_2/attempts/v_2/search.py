import argparse
import json
import time
from pathlib import Path
from solve import Compiler, np, minimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--trials', type=int, default=30)
    parser.add_argument('--modes', type=int, default=6)
    parser.add_argument('--objective', default='linear')
    parser.add_argument('--initial', type=Path)
    parser.add_argument('--refine', type=float, default=.3)
    parser.add_argument('--smooth', type=float, default=0.)
    parser.add_argument('--members', default='1')
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--basis', default='dct')
    parser.add_argument('--penalty', type=float, default=1.)
    parser.add_argument('--dc', type=float, default=0.)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input, arguments.objective, [1])
    members = [int(member) for member in arguments.members.split(',')]
    fast = None
    if arguments.native:
        from native import Native
        fast = Native(compiler)
    generator = np.random.default_rng(arguments.seed)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    basis = np.cos(np.pi * (np.arange(24)[:, None] + .5) * np.arange(24)[None, :] / 24)
    basis[:, 0] /= np.sqrt(2)
    basis *= np.sqrt(2 / 24)
    if arguments.basis == 'fourier':
        times = np.arange(24) / 24
        vectors = [np.ones(24) / np.sqrt(24)]
        for frequency in range(1, 12):
            vectors.extend([np.cos(2 * np.pi * frequency * times) * np.sqrt(2 / 24), np.sin(2 * np.pi * frequency * times) * np.sqrt(2 / 24)])
        vectors.append(np.cos(24 * np.pi * times) / np.sqrt(24))
        basis = np.column_stack(vectors)
    best = np.inf
    start = time.monotonic()
    best_amplitudes = np.zeros((24, 3))

    def optimize(amplitudes, modes, iterations, smooth=0.):
        selected = basis[:, :modes]
        if modes == 24 and arguments.penalty == 0:
            selected = np.eye(24)
        def objective(parameters):
            amplitudes = selected @ parameters.reshape(modes, 3)
            if fast is not None:
                loss, gradient = fast.objective(amplitudes, members, arguments.objective)
            else:
                results = [compiler.member((amplitudes, member)) for member in members]
                loss = np.mean([result[0] for result in results])
                gradient = np.mean([result[1] for result in results], axis=0)
            base_loss, base_gradient = loss, gradient.copy()
            excessive = np.maximum(abs(amplitudes) - limits, 0)
            loss += .3 * np.sum(excessive ** 2)
            gradient += .6 * excessive * np.sign(amplitudes)
            differences = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
            excessive_jump = np.maximum(abs(differences) - jump_limits, 0)
            loss += .3 * np.sum(excessive_jump ** 2)
            jump_gradient = .6 * excessive_jump * np.sign(differences)
            gradient += jump_gradient[:-1] - jump_gradient[1:]
            loss += smooth * np.sum(differences ** 2)
            gradient += 2 * smooth * (differences[:-1] - differences[1:])
            exposure = compiler.duration * np.sum((amplitudes / limits) ** 2)
            excess = max(exposure - 13.5, 0)
            loss += .01 * excess ** 2
            gradient += .04 * compiler.duration * excess * amplitudes / limits ** 2
            loss = base_loss + arguments.penalty * (loss - base_loss)
            gradient = base_gradient + arguments.penalty * (gradient - base_gradient)
            return loss, (selected.T @ gradient).ravel()
        bounds = [(-limit, limit) for step in range(24) for limit in limits] if modes == 24 and arguments.penalty == 0 else None
        result = minimize(objective, (selected.T @ amplitudes).ravel(), jac=True, method='L-BFGS-B', bounds=bounds, options={'maxiter': iterations, 'ftol': 1e-11, 'gtol': 1e-7, 'maxcor': 20})
        return selected @ result.x.reshape(modes, 3), result.fun, result.nfev

    for trial in range(arguments.trials):
        modes = arguments.modes
        if trial == 0 and arguments.initial:
            amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
        elif trial == 0 and arguments.seed == 0:
            amplitudes = np.zeros((24, 3))
        else:
            coefficients = generator.normal(size=(modes, 3)) / (1 + np.arange(modes)[:, None] * .25)
            amplitudes = basis[:, :modes] @ coefficients
            amplitudes *= generator.uniform(.3, .65) / np.sqrt(np.mean(amplitudes ** 2))
            if trial % 3 == 2:
                amplitudes = best_amplitudes + amplitudes * .45
        if arguments.dc and trial % 3 != 2 and not (trial == 0 and arguments.initial):
            amplitudes = amplitudes * .5 + generator.uniform(-arguments.dc, arguments.dc, size=(1, 3))
        if arguments.smooth:
            for smooth in [arguments.smooth, arguments.smooth / 5, arguments.smooth / 25]:
                amplitudes, loss, calls = optimize(amplitudes, modes, 150, smooth)
                print('smooth', smooth, 'loss', loss, flush=True)
        amplitudes, loss, calls = optimize(amplitudes, modes, 220)
        print('trial', trial, 'modes', modes, 'loss', loss, 'calls', calls, 'seconds', time.monotonic() - start, flush=True)
        if loss < best:
            best = loss
            best_amplitudes = amplitudes.copy()
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
        if loss < arguments.refine:
            amplitudes, refined, calls = optimize(amplitudes, 24, 400)
            print('REFINED', trial, refined, 'calls', calls, 'seconds', time.monotonic() - start, flush=True)
            if refined < best:
                best = refined
                best_amplitudes = amplitudes.copy()
                arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}) + '\n')
            if refined < 1e-9:
                print('SOLVED', json.dumps(compiler.report(amplitudes)), flush=True)
                break


if __name__ == '__main__':
    main()
