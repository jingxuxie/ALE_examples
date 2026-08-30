import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
sys.dont_write_bytecode = True
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
sys.path.insert(0, str(CONCEPT / 'adversary' / 'fourpoint_search'))

import hashlib
import importlib.util
import json
import subprocess
import time

from fourpoint import write_json


def main():
    started = time.monotonic()
    comparisons = {}
    for version in ('v_6', 'v_5'):
        destination = ROOT / f'{version}_four'
        destination.mkdir(parents=True, exist_ok=True)
        tensor = CONCEPT / 'attempts' / version / 'state.npz'
        for name in ('evaluation.json', 'audit.json'):
            source = CONCEPT / 'attempts' / f'{version}_audit' / name
            write_json(destination / f'archived_{name}', json.loads(source.read_text()))
        command = [sys.executable, str(CONCEPT / 'evaluator' / 'evaluate.py'), '--submission', str(tensor.parent), '--output', str(destination / 'independent_v3_score.json')]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        (destination / 'evaluator_stdout.json').write_text(completed.stdout)
        (destination / 'evaluator_stderr.log').write_text(completed.stderr)
        if completed.returncode:
            raise RuntimeError(f'{version} evaluator returned {completed.returncode}')
        score = json.loads((destination / 'independent_v3_score.json').read_text())
        metrics = score['metrics']
        comparisons[version] = {'tensor_sha256': hashlib.sha256(tensor.read_bytes()).hexdigest(),
                               'passed': score['passed'], 'core_score': score['core_score'],
                               'metrics': {key: metrics.get(key) for key in ('energy_excess', 'order_max_relative_error', 'density_max_relative_error', 'y_max_relative_error', 'composite_order_max_relative_error', 'minimum_density_eigenvalue', 'correlation_length')}}
        write_json(ROOT / 'champion_comparison.json', {'selected': 'v_6', 'reason': 'Main selects v6: better energy and all two-point families, with comparable passing composite covariance.', 'witnesses': comparisons})
        print(json.dumps({'event': 'independent_v3_recheck', 'version': version, **comparisons[version]}), flush=True)
        source = CONCEPT / 'adversary' / 'fourpoint_search' / 'search.py'
        specification = importlib.util.spec_from_file_location(f'legacy_four_{version}', source)
        legacy = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(legacy)
        legacy.ROOT = destination
        legacy.AUTHORIZED_TENSOR = tensor
        legacy.scan()
    write_json(ROOT / 'four_scan_complete.json', {'elapsed_seconds': time.monotonic() - started, 'selected': 'v_6', 'versions': list(comparisons), 'scope': str(ROOT)})


if __name__ == '__main__':
    main()
