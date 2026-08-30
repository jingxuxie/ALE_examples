import argparse
import json
from pathlib import Path
from solve import Compiler, np, minimize
from native import Native
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--multiple', type=int, default=1)
    arguments = parser.parse_args()
    compiler = Compiler(arguments.input, 'fidelity')
    compiler.executor.shutdown()
    from concurrent.futures import ThreadPoolExecutor
    compiler.executor = ThreadPoolExecutor(max_workers=1)
    native = Native(compiler)
    limits = np.array(compiler.spec['amplitude_limits'])
    jump_limits = np.array(compiler.spec['adjacent_jump_limits'])
    best = -np.inf
    best_amplitudes = np.zeros((24, 3))
    candidates = []
    for candidate in arguments.output.parent.glob('*.json'):
        try:
            amplitudes = np.array(json.loads(candidate.read_text())['amplitudes'])
            if amplitudes.shape != (24, 3):
                continue
            differences = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
            exposure = compiler.duration * np.sum((amplitudes / limits) ** 2)
            scale = max(1., np.max(abs(amplitudes) / limits), np.max(abs(differences) / jump_limits), np.sqrt(exposure / 13.5)) * (1 + 1e-12)
            amplitudes /= scale
            fidelity = 1 - native.objective(amplitudes, [0, 1, 2, 3], 'fidelity')[0]
            candidates.append((fidelity, amplitudes.copy(), candidate.name))
            if fidelity > best:
                best, best_amplitudes = fidelity, amplitudes.copy()
                print('candidate', candidate.name, 'score', fidelity, flush=True)
        except (ValueError, KeyError, json.JSONDecodeError):
            pass
    flat_limits = np.tile(limits, 24)
    differences = np.diff(np.vstack((np.zeros((1, 24)), np.eye(24), np.zeros((1, 24)))), axis=0)
    jump_matrix = np.kron(differences, np.eye(3))
    constraints = [LinearConstraint(jump_matrix, -np.tile(jump_limits, 25), np.tile(jump_limits, 25)), NonlinearConstraint(lambda values: compiler.duration * np.sum((values / flat_limits) ** 2), -np.inf, 13.5, jac=lambda values: 2 * compiler.duration * values / flat_limits ** 2)]
    def objective(values):
        loss, gradient = native.objective(values.reshape(24, 3), [0, 1, 2, 3], 'fidelity')
        return loss, gradient.ravel()
    candidates.sort(key=lambda entry: -entry[0])
    selected = []
    for candidate in candidates:
        if all(np.sqrt(np.mean((candidate[1] - previous[1]) ** 2)) > .03 for previous in selected):
            selected.append(candidate)
        if len(selected) >= arguments.multiple:
            break
    best = -np.inf
    for score, initial, name in selected:
        result = minimize(objective, initial.ravel(), jac=True, method='SLSQP', bounds=Bounds(-flat_limits, flat_limits), constraints=constraints, options={'maxiter': 400, 'ftol': 1e-13})
        amplitudes = result.x.reshape(24, 3)
        report = compiler.report(amplitudes)
        print(name, json.dumps(report), flush=True)
        if not report['physical_valid']:
            amplitudes *= 1 - 1e-9
            report = compiler.report(amplitudes)
        if report['physical_valid'] and report['core_score'] > best:
            best = report['core_score']
            arguments.output.write_text(json.dumps({'schema_version': 1, 'amplitudes': amplitudes.tolist()}, indent=2) + '\n')
            arguments.output.with_suffix('.report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
