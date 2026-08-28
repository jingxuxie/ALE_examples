import json
import sys
import argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'reference'))
from solver import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pool', default='initial')
    options = parser.parse_args()
    folder = HERE / ('challenge_pool' if options.pool == 'challenge' else f'reference/{options.pool}')
    manifest = json.loads((folder / 'manifest.json').read_text())
    records = []
    for item in manifest:
        with np.load(folder / item['input']) as archive:
            data = dict(archive)
        with np.load(folder / item['reference']) as archive:
            reference = dict(archive)
        fine = solve(data, steps=512)
        errors = {name: float(np.sqrt(np.mean(np.abs(fine[name] - value)**2))) / item['weak_error'][name]
                  for name, value in reference.items()}
        scores = {name: 1 / (1 + 9 * np.sqrt(error)) for name, error in errors.items()}
        state = reference['state']
        unitary = float(np.max(np.abs(state @ state.conj().swapaxes(-1, -2) - np.eye(state.shape[-1]))))
        determinant = float(np.max(np.abs(np.linalg.det(state) - 1))) if state.shape[-1] > 1 else None
        record = {'id': item['id'], 'normalized_errors': errors, 'scores': scores,
                  'mean_core': float(np.mean(list(scores.values()))),
                  'unitarity_error': unitary, 'determinant_error': determinant}
        records.append(record)
        report = {'mean_core': float(np.mean([record['mean_core'] for record in records])),
                  'worst_case': min(record['mean_core'] for record in records),
                  'minimum_component_score': min(min(record['scores'].values()) for record in records),
                  'method': 'independent step refinement, 256 versus 512 upstream CG3 stages',
                  'cases': records}
        (HERE / f'reference/validation_{options.pool}.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(record), flush=True)
    if report['minimum_component_score'] <= 0.9:
        raise RuntimeError('Reference needs additional convergence refinement')


if __name__ == '__main__':
    main()
