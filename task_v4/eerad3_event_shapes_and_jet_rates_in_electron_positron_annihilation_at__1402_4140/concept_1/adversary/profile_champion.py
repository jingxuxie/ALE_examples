import ctypes
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

CONCEPT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONCEPT.parent / 'research'))
from build_prediction import generate_events, native_values, FAMILIES


def main():
    library = ctypes.CDLL(str(CONCEPT / 'champions/generation_1/kernel.so'))
    pointer = ctypes.POINTER(ctypes.c_double)
    library.predict_kernel.argtypes = [pointer, pointer, pointer, ctypes.c_long]
    generator = np.random.default_rng(29103844)
    results = []
    for family in FAMILIES:
        invariants, momenta = generate_events(generator, 12000, family)
        keep = invariants.min(axis=1) > 1e-10
        invariants = np.ascontiguousarray(invariants[keep])
        momenta = np.ascontiguousarray(momenta[keep])
        output = np.empty(len(invariants))
        started = time.process_time()
        library.predict_kernel(momenta.ctypes.data_as(pointer), invariants.ctypes.data_as(pointer),
                               output.ctypes.data_as(pointer), len(output))
        champion_seconds = time.process_time() - started
        started = time.process_time()
        native = native_values(invariants, CONCEPT / 'adversary/native', 8)
        native_seconds = time.process_time() - started
        error = output - np.log(native)
        results.append({'family': family, 'count': len(output), 'champion_cpu_seconds': champion_seconds,
                        'native_double_cpu_seconds': native_seconds,
                        'champion_to_native_cost': champion_seconds / native_seconds,
                        'log_rmse': float(np.sqrt(np.mean(error ** 2))),
                        'maximum_absolute_log_error': float(np.max(np.abs(error)))})
        print(results[-1], flush=True)
    total_count = sum(result['count'] for result in results)
    champion_total = sum(result['champion_cpu_seconds'] for result in results)
    native_total = sum(result['native_double_cpu_seconds'] for result in results)
    report = {'cases': results, 'total_count': total_count,
              'champion_cpu_seconds_per_million': champion_total / total_count * 1e6,
              'native_cpu_seconds_per_million': native_total / total_count * 1e6,
              'root_cause': 'repeated helicity/current contractions versus direct native invariant evaluation',
              'accuracy_failure': any(result['maximum_absolute_log_error'] > 0.05 for result in results)}
    (CONCEPT / 'adversary/generation_1_profile.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
