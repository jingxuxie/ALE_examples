import json
import os
from pathlib import Path
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

import numpy as np

from run_audit import AUDIT, CASES, protected_hashes, weak_solve


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def main():
    original_hashes = json.loads((AUDIT / 'preservation_before.json').read_text())
    if protected_hashes() != original_hashes:
        raise AssertionError('An active artifact or immutable solver changed')
    records = []
    for name, family, qubits, seed in CASES:
        directory = AUDIT / 'cases' / name
        result = json.loads((directory / 'result.json').read_text())
        data = arrays(directory / 'input.npz')
        oracle = arrays(directory / 'oracle.npz')
        reference = arrays(directory / 'reference_output.npz')
        frozen = arrays(directory / 'frozen_output.npz')
        weak = weak_solve(data)
        mask = oracle['calibration_identifiable'].astype(bool)
        raw_losses = {label: float(np.mean((output['query_log_estimate'][mask] - oracle['query_log'][mask]) ** 2))
                      for label, output in (('weak', weak), ('reference', reference), ('frozen', frozen))}
        raw_query_qualified = raw_losses['reference'] <= raw_losses['weak'] / 10
        result['raw_query_losses'] = raw_losses
        result['raw_query_improvement'] = raw_losses['weak'] / raw_losses['reference']
        result['normalized_query_improvement'] = result['baseline_losses']['invariant_estimation'] / result['reference_losses']['invariant_estimation']
        result['prediction_improvement'] = result['baseline_losses']['heldout_prediction'] / result['reference_losses']['heldout_prediction']
        result['qualification']['raw_query_improvement_at_least_10x'] = raw_query_qualified
        result['qualified'] = bool(result['qualified'] and raw_query_qualified)
        records.append(result)
    families = {}
    for family in sorted({record['family'] for record in records}):
        selected = [record for record in records if record['family'] == family]
        families[family] = {'count': len(selected),
                            'reference_mean': float(np.mean([record['reference_score'] for record in selected])),
                            'frozen_mean': float(np.mean([record['frozen_score'] for record in selected])),
                            'frozen_minimum': min(record['frozen_score'] for record in selected),
                            'identification_errors': sum(sum(record['identification_mismatches'].values()) for record in selected)}
    independent_log = (AUDIT / 'independent_source_tests.log').read_text()
    summary = {'domain': 'original_20_24', 'extended_scale_cases': 0, 'cases': records, 'families': families,
               'case_count': len(records), 'qualified_count': sum(record['qualified'] for record in records),
               'reference_mean': float(np.mean([record['reference_score'] for record in records])),
               'frozen_mean': float(np.mean([record['frozen_score'] for record in records])),
               'frozen_worst_family': min(family['frozen_mean'] for family in families.values()),
               'frozen_worst_case': min(record['frozen_score'] for record in records),
               'identification_errors': sum(sum(record['identification_mismatches'].values()) for record in records),
               'maximum_score_gap': max(abs(record['reference_score'] - record['frozen_score']) for record in records),
               'minimum_raw_query_improvement': min(record['raw_query_improvement'] for record in records),
               'minimum_normalized_query_improvement': min(record['normalized_query_improvement'] for record in records),
               'minimum_prediction_improvement': min(record['prediction_improvement'] for record in records),
               'minimum_informative_holdouts': min(record['consistency']['informative_holdouts'] for record in records),
               'maximum_prediction_fisher_std_p95': max(record['consistency']['prediction_std_p95'] for record in records),
               'maximum_query_fisher_std_p95': max(record['consistency']['normalized_query_std_p95'] for record in records),
               'independent_transfer_maximum_error': max(record['consistency']['maximum_row_error'] for record in records),
               'reference_runtime_max': max(record['reference_runtime'] for record in records),
               'frozen_runtime_max': max(record['frozen_runtime'] for record in records),
               'reference_memory_max_mib': max(record['reference_memory']['peak_memory_mib'] for record in records),
               'frozen_memory_max_mib': max(record['frozen_memory']['peak_memory_mib'] for record in records),
               'independent_source_tests_passed': 'Ran 14 tests' in independent_log and independent_log.rstrip().endswith('OK'),
               'protected_artifacts_unchanged': True,
               'grading': 'Unchanged imported metrics and identical per-case scales for both solvers'}
    (AUDIT / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    (AUDIT / 'preservation_after.json').write_text(json.dumps(protected_hashes(), indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
