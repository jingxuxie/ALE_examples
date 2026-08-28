import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main():
    specification = importlib.util.spec_from_file_location('diagnostic', ROOT / 'participant/v_03/software/validate.py')
    diagnostic = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(diagnostic)
    reports = []
    for name in ['validation_small', 'validation_large']:
        data_path = ROOT / f'participant/v_03/input/{name}.npz'
        labels_path = ROOT / f'participant/v_03/input/{name}_labels.npz'
        for label, directory, destination in [('baseline', ROOT / 'participant/v_03/software', ROOT / 'authoring'),
                                              ('reference', ROOT / 'solution/v_03', ROOT / 'solution/v_03')]:
            output = destination / (f'{name}_predictions.npz' if label == 'reference' else f'baseline_{name}_predictions.npz')
            started = time.monotonic()
            subprocess.run([sys.executable, str(directory / 'solve.py'), '--input', str(data_path), '--output', str(output)],
                           check=True, env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
            report = diagnostic.compare(np.load(data_path), np.load(labels_path), np.load(output))
            report.update(case=name, implementation=label, seconds=round(time.monotonic() - started, 3))
            reports.append(report)
    (ROOT / 'authoring/v03_validation_metrics.json').write_text(json.dumps(reports, indent=2) + '\n')
    print(json.dumps(reports))


if __name__ == '__main__':
    main()
