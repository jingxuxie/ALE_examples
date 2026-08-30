import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
from scipy.special import expit

from exact import STATES, LIMIT, evaluate, frustration


KEYS = {'schema_version', 'bonds', 'beta', 'order', 'weights', 'pattern', 'radius'}
GATES = {
    'entropy': (3.0, True),
    'reverse_kl': (.4, True),
    'reward_variance': (.05, False),
    'gradient_infinity': (.003, False),
    'energy_error_per_spin': (.02, False),
    'target_sector_mass': (.35, True),
    'proposal_sector_mass': (.001, False),
}


def structural(witness):
    assert isinstance(witness, dict) and set(witness) == KEYS
    assert type(witness['schema_version']) is int and witness['schema_version'] == 1
    assert type(witness['radius']) is int and witness['radius'] in [2, 3, 4]
    assert len(witness['bonds']) == 32 and all(type(value) is int and value in [-1, 1] for value in witness['bonds'])
    assert len(witness['pattern']) == 16 and all(type(value) is int and value in [-1, 1] for value in witness['pattern'])
    assert len(witness['order']) == 16 and all(type(value) is int for value in witness['order'])
    assert sorted(witness['order']) == list(range(16))
    assert type(witness['beta']) in [int, float] and math.isfinite(witness['beta']) and 1 <= witness['beta'] <= 3
    assert len(witness['weights']) == 16 and all(len(row) == 16 for row in witness['weights'])
    assert all(type(value) in [int, float] and math.isfinite(value) for row in witness['weights'] for value in row)
    weights = np.asarray(witness['weights'], dtype=np.float64)
    assert np.all(weights[np.triu_indices(16)] == 0)
    assert np.all(np.abs(weights).sum(axis=1) <= LIMIT)
    assert 4 <= frustration(witness['bonds']) <= 12


def finalize(source=None):
    files = [Path(source)] if source else list(Path('.').glob('*_best.json')) + list(Path('.').glob('*minimax.json')) + [Path('witness.json')]
    best = None
    best_source = None
    best_score = -1
    for path in files:
        try:
            witness = json.loads(path.read_text())
            structural(witness)
            report = evaluate(witness)
        except (OSError, ValueError, AssertionError, KeyError, TypeError):
            continue
        print(path.name, report['core_score'], flush=True)
        if report['core_score'] > best_score:
            best, best_score, best_source = witness, report['core_score'], path.name
    assert best is not None
    weights = np.array(best['weights'])
    lengths = np.abs(weights).sum(axis=1)
    weights *= np.minimum(1, (LIMIT - 1e-10) / np.maximum(lengths, 1e-100))[:, None]
    best['weights'] = weights.tolist()
    structural(best)
    destination = Path('witness.json')
    destination.write_text(json.dumps(best, indent=2, allow_nan=False) + '\n')
    assert destination.is_file() and not destination.is_symlink() and destination.stat().st_size <= 131072
    start = time.perf_counter()
    report, data = evaluate(json.loads(destination.read_text()), True)
    logits = STATES[:, best['order']] @ weights.T
    report['minimum_conditional_outcome_probability'] = float(expit(-np.abs(logits)).min())
    report['minimum_configuration_probability'] = float(data[1].min())
    report['full_enumeration_configurations'] = 65536
    report['structurally_valid'] = True
    report['failing_gates'] = [key for key, (threshold, lower) in GATES.items()
                               if (report[key] < threshold - 1e-10 if lower else report[key] > threshold + 1e-10)]
    report['passed'] = not report['failing_gates']
    assert abs(report['normalization'] - 1) <= 1e-10
    assert report['symmetry_error'] <= 1e-12
    assert report['minimum_configuration_probability'] > 0
    report['source_candidate'] = best_source
    report['verification_wall_seconds'] = time.perf_counter() - start
    report['witness_sha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
    Path('verification.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    status = 'All seven metric gates pass.' if report['passed'] else 'This is a tested partial construction, not a passing counterexample.'
    lines = ['# Submission', '', status, '',
             '`witness.json` is the evaluator input. `verification.json` contains exhaustive float64 measurements.', '',
             '| Metric | Measured | Requirement |', '|---|---:|---:|']
    for key, (threshold, lower) in GATES.items():
        lines.append(f'| {key} | {report[key]:.12g} | {">=" if lower else "<="} {threshold:g} |')
    lines += ['', f'Core score: {report["core_score"]:.12g}.', '',
              'Verification enumerates all 65,536 configurations without probability truncation or renormalization.',
              'The proposal has no biases, is globally spin-flip symmetric, and satisfies every row L1 bound.', '',
              'Recheck with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B exact.py witness.json`.', '',
              'Search scripts and logs document the numerical construction. No external sources or delegated agents were used.']
    Path('README.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source')
    arguments = parser.parse_args()
    finalize(arguments.source)
