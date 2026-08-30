import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import least_squares


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from model import LOWER, UPPER, diagnose


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=900)
    parser.add_argument('--start', required=True)
    parser.add_argument('--refine', action='store_true')
    options = parser.parse_args()
    started = time.monotonic()
    candidate = np.array(json.loads(Path(options.start).read_text())['parameters'])
    probes = np.load(ROOT / 'evaluator' / 'hidden' / 'correlated_displacements.npy')
    report_name = 'generation2_private_evaluation.json' if options.refine else 'generation_2_previous_champion.json'
    report = json.loads((ROOT / 'adversary' / report_name).read_text())
    rows = sorted(report['correlated_perturbations'], key=lambda row: row['metrics']['plateau_spread'], reverse=True)
    indices = [row['probe'] for row in rows[:12]]
    indices += [int(value) for value in np.linspace(0, len(probes) - 1, 8)]
    if options.refine:
        indices += [row['probe'] for row in report['correlated_perturbations'] if not all(row['checks'].values())]
        indices = sorted(set(indices))
    axes = np.zeros((42, 25))
    for coordinate in range(21):
        axes[2 * coordinate, coordinate] = .02
        axes[2 * coordinate + 1, coordinate] = -.02
    directions = np.concatenate((np.zeros((1, 25)), axes, probes[indices]), axis=0)
    state = {'evaluations': 0, 'best_loss': float('inf'), 'parameters': candidate.tolist()}
    def residual(parameters):
        if time.monotonic() - started > options.seconds:
            raise TimeoutError
        output = []
        for position, displacement in enumerate(directions):
            metrics = diagnose(parameters + displacement, 25 if options.refine else 17)
            chern = round(metrics['chern'])
            contributions = np.array(metrics['contributions'])[2:4]
            if options.refine:
                threshold = .0035 if position == 0 else .0077
                differences = np.array([contributions[0], contributions[1], contributions.sum()])
                output.extend((20 * np.maximum(np.abs(differences) - threshold, 0)).tolist())
                output.extend((30 * np.maximum(.0151 - np.array(metrics['optical'][:4]), 0)).tolist())
            else:
                output.extend((20 * np.maximum(np.abs(contributions) - .0020, 0)).tolist())
                output.append(10 * max(.017 - metrics['retained_optical_min'], 0))
            minimum_gap = .67 if options.refine else .77
            output.append(2 * max(minimum_gap - metrics['sampled_gap'], 0))
            output.append(max(.21 - metrics['plateau_mean'], metrics['plateau_mean'] - .38, 0))
            output.append(4. * (chern != 1))
            output.append(max(abs(metrics['full'] - chern) - .03, 0))
        output = np.array(output)
        value = float(output @ output)
        state['evaluations'] += 1
        if value < state['best_loss']:
            state.update(best_loss=value, parameters=parameters.tolist(), elapsed_seconds=time.monotonic() - started)
            (ROOT / 'adversary' / 'generation2_search_checkpoint.json').write_text(json.dumps(state, indent=2))
        return output
    try:
        least_squares(residual, candidate, bounds=(LOWER, UPPER), max_nfev=250,
                      ftol=1e-10, xtol=1e-10, gtol=1e-8, diff_step=1e-4)
    except TimeoutError:
        pass
    state['fine_nominal'] = diagnose(state['parameters'], 97)
    (ROOT / 'adversary' / 'generation2_search_result.json').write_text(json.dumps(state, indent=2))
    (ROOT / 'adversary' / 'generation2_private_witness.json').write_text(json.dumps({'parameters': state['parameters']}, indent=2))
    print(json.dumps(state, indent=2))


if __name__ == '__main__':
    main()
