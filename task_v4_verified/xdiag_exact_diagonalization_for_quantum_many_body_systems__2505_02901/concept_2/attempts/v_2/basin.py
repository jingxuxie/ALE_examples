import argparse
import json
import time
from pathlib import Path
from solve import Compiler, np, minimize
from scipy.ndimage import gaussian_filter1d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--initial', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=10)
    parser.add_argument('--trials', type=int, default=400)
    parser.add_argument('--temperature', type=float, default=.03)
    parser.add_argument('--members', default='1')
    parser.add_argument('--objective', default='linear')
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--deflate', action='store_true')
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input, arguments.objective)
    members = [int(member) for member in arguments.members.split(',')]
    fast = None
    if arguments.native:
        from native import Native
        fast = Native(compiler)
    generator = np.random.default_rng(arguments.seed)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    amplitudes = np.array(json.loads(arguments.initial.read_text())['amplitudes'])
    best = np.inf
    current = np.inf
    best_amplitudes = amplitudes.copy()
    covariance = np.eye(72)
    calls = 0
    start = time.monotonic()
    centers = []

    def objective(parameters, repulsive=True):
        nonlocal calls
        amplitudes = parameters.reshape(24, 3)
        if fast is not None:
            loss, gradient = fast.objective(amplitudes, members, arguments.objective)
        else:
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
        calls += 1
        flattened_gradient = gradient.ravel()
        if arguments.deflate and repulsive and centers:
            differences = parameters[None, :] - np.array(centers)
            weights = np.exp(-np.sum(differences ** 2, axis=1) / 2.)
            multiplier = 1 + 2 * np.sum(weights)
            flattened_gradient = multiplier * flattened_gradient - 2 * loss * np.sum(weights[:, None] * differences, axis=0)
            loss *= multiplier
        return loss, flattened_gradient

    for trial in range(arguments.trials):
        if trial % 20 == 0 and trial:
            amplitudes = best_amplitudes.copy()
            current = best
            for candidate in arguments.output.parent.glob('basin*.json'):
                try:
                    other = np.array(json.loads(candidate.read_text())['amplitudes'])
                    value = objective(other.ravel())[0]
                    if value < current:
                        amplitudes = other
                        current = value
                except (ValueError, KeyError, json.JSONDecodeError):
                    pass
        candidate = amplitudes.copy()
        if trial:
            mutation = trial % 6
            scale = generator.uniform(.12, .6)
            if arguments.deflate:
                scale *= .2
            noise = generator.normal(size=(24, 3))
            if mutation == 0:
                noise = gaussian_filter1d(noise, generator.uniform(1, 3), axis=0)
            elif mutation == 1:
                noise = (covariance @ noise.ravel()).reshape(24, 3)
            elif mutation == 2:
                center = generator.integers(24)
                width = generator.uniform(1, 4)
                noise *= np.exp(-.5 * ((np.arange(24) - center) / width) ** 2)[:, None]
            elif mutation == 3:
                noise[:, generator.choice(3, 2, replace=False)] = 0
                noise = gaussian_filter1d(noise, 1, axis=0)
            elif mutation == 4:
                left = generator.integers(20)
                right = min(left + generator.integers(2, 9), 24)
                candidate[left:right] = candidate[left:right][::-1]
                scale *= .25
            noise *= scale / max(np.sqrt(np.mean(noise ** 2)), 1e-20)
            candidate += noise
        bounds = [(-limit, limit) for step in range(24) for limit in limits] if arguments.deflate else None
        result = minimize(objective, candidate.ravel(), jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': 180, 'ftol': 2e-10, 'gtol': 1e-7, 'maxcor': 20})
        if arguments.deflate:
            result = minimize(lambda parameters: objective(parameters, False), result.x, jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': 200, 'ftol': 1e-12, 'gtol': 1e-8, 'maxcor': 25})
            centers.append(result.x.copy())
        if not arguments.deflate and (result.fun < best - 1e-7 or result.fun < .1):
            result = minimize(objective, result.x, jac=True, method='L-BFGS-B', options={'maxiter': 500, 'ftol': 1e-13, 'gtol': 1e-8, 'maxcor': 30})
        if result.fun < best:
            best = result.fun
            best_amplitudes = result.x.reshape(24, 3).copy()
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': best_amplitudes.tolist()}) + '\n')
        temperature = arguments.temperature * (.5 + .5 * (1 + np.cos(2 * np.pi * trial / 50)))
        accepted = result.fun < current or generator.random() < np.exp(min(0., (current - result.fun) / max(temperature, 1e-12)))
        if accepted:
            current = result.fun
            amplitudes = result.x.reshape(24, 3).copy()
            eigenvalues, vectors = np.linalg.eigh(result.hess_inv.todense())
            covariance = (vectors * np.sqrt(np.maximum(eigenvalues, .01))[None, :]) @ vectors.T
        print('trial', trial, 'loss', result.fun, 'current', current, 'best', best, 'accepted', accepted, 'calls', calls, 'seconds', time.monotonic() - start, flush=True)
        if best < 1e-10:
            print('SOLVED', flush=True)
            break


if __name__ == '__main__':
    main()
