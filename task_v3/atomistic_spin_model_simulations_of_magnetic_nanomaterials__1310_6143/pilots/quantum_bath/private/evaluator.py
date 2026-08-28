import argparse
import json
import math
from pathlib import Path
import sys
import tempfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'authoring'))
from isolated import run_submission


def errors(output, reference):
    return {key: float(np.sqrt(np.mean((output[key] - reference[key]) ** 2)))
            for key in ('spins', 'trace', 'memory', 'covariance')}


def evaluate(submission, split):
    entries = json.load(open(ROOT / 'private' / 'manifest.json'))
    rows = []
    for entry in entries:
        if entry['split'] != split:
            continue
        case_path = ROOT / 'private' / 'challenge_pool' / (entry['id'] + '.json')
        reference = np.load(ROOT / 'private' / 'reference' / (entry['id'] + '.npz'))
        with tempfile.TemporaryDirectory(prefix='spin-quantum-eval-') as directory:
            output = Path(directory) / 'answer.npz'
            execution = run_submission(submission, case_path, output, ROOT / 'participant')
            row = dict(id=entry['id'], family=entry['family'], execution=execution, core_score=0.0)
            if execution['returncode'] == 0 and output.exists():
                try:
                    predicted = np.load(output, allow_pickle=False)
                    for key in reference.files:
                        if predicted[key].shape != reference[key].shape or not np.isfinite(predicted[key]).all():
                            raise ValueError('invalid array ' + key)
                    rms = errors(predicted, reference)
                    components = {key: math.exp(-math.log(2) * value / max(entry['weak_errors'][key], 1e-7))
                                  for key, value in rms.items()}
                    dynamic = (components['spins'] * components['trace']) ** 0.5
                    row.update(errors=rms, components=components,
                        core_score=(dynamic * components['memory'] * components['covariance']) ** (1 / 3))
                    row['unit_spin_max_error'] = float(np.max(np.abs(np.linalg.norm(predicted['spins'], axis=1) - 1)))
                    if row['unit_spin_max_error'] > 0.01:
                        row['core_score'] *= math.exp(-row['unit_spin_max_error'])
                except (ValueError, OSError, KeyError) as error:
                    row['error'] = str(error)
            rows.append(row)
    families = {family: float(np.mean([row['core_score'] for row in rows if row['family'] == family]))
                for family in sorted({row['family'] for row in rows})}
    return dict(submission=str(Path(submission).resolve()), split=split, cases=rows,
        mean_core=float(np.mean([row['core_score'] for row in rows])) if rows else 0,
        worst_family=min(families.values()) if families else 0, families=families,
        scoring='geometric mean of baseline-relative exponential physical component scores')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--split', default='initial', choices=['initial', 'challenge', 'confirmation'])
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.split)
    Path(arguments.output).write_text(json.dumps(report, indent=2))
    print(json.dumps({key: report[key] for key in ('mean_core', 'worst_family', 'families')}, indent=2))
