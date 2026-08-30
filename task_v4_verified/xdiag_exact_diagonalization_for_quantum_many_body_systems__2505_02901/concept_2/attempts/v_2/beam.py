import argparse
import itertools
import json
import time
from pathlib import Path
from solve import Compiler, np, minimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=10)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input)
    generator = np.random.default_rng(arguments.seed)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    members = [0, 2]
    start = time.monotonic()
    beam = []
    for slices, width in [(1, 24), (2, 20), (4, 16), (6, 12), (12, 8), (24, 6)]:
        compiler.duration = .85 * 24 / slices
        if slices >= 12:
            members = [0, 1, 2, 3]
        def objective(flattened):
            amplitudes = flattened.reshape(slices, 3)
            results = [compiler.member((amplitudes, member)) for member in members]
            loss = np.mean([result[0] for result in results])
            gradient = np.mean([result[1] for result in results], axis=0)
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

        if slices == 1:
            seeds = [np.array(values)[None, :] * limits * .65 for values in itertools.product(np.linspace(-1, 1, 5), repeat=3)]
        else:
            seeds = []
            for loss, previous in beam:
                interpolated = np.column_stack([np.interp((np.arange(slices) + .5) / slices, (np.arange(len(previous)) + .5) / len(previous), previous[:, channel]) for channel in range(3)])
                seeds.append(interpolated)
                seeds.append(interpolated + generator.normal(size=interpolated.shape) * .18)
        candidates = []
        for index, seed in enumerate(seeds):
            result = minimize(objective, seed.ravel(), jac=True, method='L-BFGS-B', options={'maxiter': 100 if slices < 6 else 250, 'ftol': 1e-10, 'gtol': 1e-7, 'maxcor': 20})
            amplitudes = result.x.reshape(slices, 3)
            candidates.append((result.fun, amplitudes))
            candidates.sort(key=lambda item: item[0])
            best = candidates[0]
            payload = {'schema_version': 1, 'amplitudes': np.repeat(best[1], 24 // slices, axis=0).tolist()}
            arguments.output.write_text(json.dumps(payload) + '\n')
            if index % 5 == 0 or result.fun < .2:
                print('slices', slices, 'index', index, 'loss', result.fun, 'best', best[0], 'seconds', time.monotonic() - start, flush=True)
            if result.fun < 1e-9:
                print('SOLVED', flush=True)
                return
        beam = []
        for candidate in candidates:
            if all(np.sqrt(np.mean((candidate[1] - previous[1]) ** 2)) > .08 for previous in beam):
                beam.append(candidate)
            if len(beam) >= width:
                break
        print('LEVEL', slices, 'best', beam[0][0], 'size', len(beam), 'seconds', time.monotonic() - start, flush=True)
        np.savez(arguments.output.with_name(arguments.output.stem + '_level' + str(slices) + '.npz'), amplitudes=np.array([entry[1] for entry in beam]), losses=np.array([entry[0] for entry in beam]))


if __name__ == '__main__':
    main()
