import argparse
import copy
import hashlib
import json
from pathlib import Path
import time

import numpy as np

import dense_oracle
import evaluator
import numerics


ROOT = Path(__file__).resolve().parents[1]


def numerical_audit():
    random = np.random.default_rng(890671)
    records = []
    for count in [2, 3, 7, 12, 19]:
        for shifted in [False, True]:
            tensors = random.normal(size=(count, 3, 3))
            tensors = 0.15 * (tensors + tensors.transpose(0, 2, 1))
            spins = random.normal(size=(count, 3))
            spins /= np.linalg.norm(spins, axis=1)[:, None]
            case = dict(n_spins=count, exchange_meV=random.uniform(0.2, 2, count - 1).tolist(),
                        anisotropy_meV=tensors.tolist(), field_meV=random.normal(size=3).tolist())
            if shifted:
                rotation, _ = np.linalg.qr(random.normal(size=(3, 3)))
                spins = spins @ rotation.T
                case['anisotropy_meV'] = np.einsum('ac,ncd,bd->nab', rotation, tensors, rotation).tolist()
                case['field_meV'] = (rotation @ np.asarray(case['field_meV'])).tolist()
            dense = dense_oracle.diagnostics(case, spins)
            banded = numerics.diagnostics(case, spins)
            dense_matrix = dense_oracle.tangent_hessian(case, spins)
            differences = dense_oracle.finite_difference_hessian(case, spins)
            bands = numerics.tangent_bands(case, spins)
            rebuilt = np.zeros_like(dense_matrix)
            for offset in range(4):
                columns = np.arange(2 * count - offset)
                rebuilt[columns + offset, columns] = bands[offset, columns]
                rebuilt[columns, columns + offset] = bands[offset, columns]
            record = dict(count=count, rotated=shifted,
                          energy_error=abs(dense['energy_meV'] - banded['energy_meV']),
                          gradient_error=float(np.max(np.abs(dense_oracle.energy_gradient(case, spins)[1] - numerics.energy_gradient(case, spins)[1]))),
                          matrix_error=float(np.max(np.abs(dense_matrix - rebuilt))),
                          spectrum_error=float(np.max(np.abs(dense['eigenvalues'] - banded['eigenvalues']))),
                          finite_difference_error=float(np.max(np.abs(differences - rebuilt))))
            assert max(record[name] for name in ['energy_error', 'gradient_error', 'matrix_error', 'spectrum_error']) < 1e-10, record
            assert record['finite_difference_error'] < 1e-7, record
            records.append(record)
    case = json.loads((ROOT / 'participant/input/long_chain_example.json').read_text())
    started = time.monotonic()
    large = numerics.diagnostics(case, np.asarray(case['minimum_a']))
    return dict(random_cases=records, large_case_spins=case['n_spins'],
                large_spectrum_seconds=time.monotonic() - started,
                large_eigenvalue_count=len(large['eigenvalues']))


def reference_audit():
    answers = {}
    records = []
    for split, directory in [('initial', ROOT / 'private/reference/initial'),
                             ('challenge', ROOT / 'private/challenge_pool/challenge')]:
        manifest = json.loads((directory / 'manifest.json').read_text())
        for relative, digest in manifest['sha256'].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
        case_paths = sorted(directory.glob('*/case.json'))
        assert len(case_paths) >= (6 if split == 'initial' else 3), (split, len(case_paths))
        families = {json.loads(case_path.read_text())['family'] for case_path in case_paths}
        assert len(families) >= 3, (split, families)
        for case_path in case_paths:
            case = json.loads(case_path.read_text())
            reference = json.loads(case_path.with_name('solution.json').read_text())
            weak = evaluator.weak_result(case)
            strong_loss, checks = evaluator.physical_loss(case, reference, reference)
            weak_loss, _ = evaluator.physical_loss(case, weak, reference)
            assert checks['residual_meV'] < 2e-6 and checks['negative_modes'] == 1 and checks['zero_modes'] == 0, checks
            assert strong_loss < weak_loss
            ablations = {}
            saddle_only = copy.deepcopy(reference)
            for name in ['eigenvalues_min_meV', 'eigenvalues_saddle_meV', 'log_omega0']:
                saddle_only[name] = weak[name]
            fluctuation_only = copy.deepcopy(weak)
            for name in ['eigenvalues_min_meV', 'eigenvalues_saddle_meV', 'log_omega0']:
                fluctuation_only[name] = reference[name]
            for name, prediction in [('weak', weak), ('saddle_only', saddle_only),
                                     ('fluctuation_only', fluctuation_only), ('strong', reference)]:
                loss, _ = evaluator.physical_loss(case, prediction, reference)
                ablations[name] = evaluator.calibrated_score(loss, weak_loss, strong_loss, 0, 1)[0]
            assert ablations['saddle_only'] < 0.70 and ablations['fluctuation_only'] < 0.70, ablations
            assert ablations['strong'] > 0.90
            answers[case['case_id']] = reference
            records.append(dict(case_id=case['case_id'], split=split, family=case['family'],
                                checks=checks, ablations=ablations))
    (ROOT / 'private/strong_submission/answers.json').write_text(json.dumps(answers, allow_nan=False))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--numerics-only', action='store_true')
    arguments = parser.parse_args()
    result = dict(numerics=numerical_audit())
    if not arguments.numerics_only:
        result['references'] = reference_audit()
    result['source_sha256'] = {name: hashlib.sha256((ROOT / 'private' / name).read_bytes()).hexdigest()
                               for name in ['numerics.py', 'dense_oracle.py', 'evaluator.py', 'isolated.py']}
    destination = ROOT / 'private' / ('numerics_audit.json' if arguments.numerics_only else 'audit.json')
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(status='PASS', numerical_cases=len(result['numerics']['random_cases']),
                         large_spectrum_seconds=result['numerics']['large_spectrum_seconds'],
                         references=len(result.get('references', []))), indent=2))


if __name__ == '__main__':
    main()
