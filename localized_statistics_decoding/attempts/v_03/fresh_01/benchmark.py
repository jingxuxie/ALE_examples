import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'

import numpy as np

from validate import compare


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
    available = os.sched_getaffinity(0)
    os.sched_setaffinity(0, {min(available)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parent
    for key in list(os.environ):
        if key.startswith('DECODER_'):
            del os.environ[key]
    library = root / 'decoder.so'
    if library.exists():
        library.unlink()
    results = []
    log = []
    cases = [('validation_small', arguments.inputs / 'validation_small.npz',
              arguments.inputs / 'validation_small_labels.npz'),
             ('validation_large', arguments.inputs / 'validation_large.npz',
              arguments.inputs / 'validation_large_labels.npz'),
             ('bounded_synthetic', root / 'synthetic_1_6.npz', root / 'synthetic_1_6_labels.npz')]
    for name, input_path, label_path in cases:
        output_path = root / (name + '_predictions.npz')
        runtime_path = root / (name + '_runtime.json')
        command = ['/usr/bin/time', '-f', '{"wall_seconds":%e,"user_seconds":%U,"system_seconds":%S,"peak_rss_kib":%M}',
                   '-o', str(runtime_path), sys.executable, str(root / 'solve.py'),
                   '--input', str(input_path), '--output', str(output_path)]
        started = time.perf_counter()
        process = subprocess.run(command, capture_output=True, text=True, timeout=60,
                                 preexec_fn=limits, cwd=str(root))
        elapsed = time.perf_counter() - started
        log.append('COMMAND: ' + ' '.join(command) + '\n' + process.stdout + process.stderr)
        process.check_returncode()
        validate_command = [sys.executable, str(root / 'validate.py'), '--input', str(input_path),
                            '--labels', str(label_path), '--actual', str(output_path)]
        validation = subprocess.run(validate_command, capture_output=True, text=True, check=True)
        log.append('VALIDATE: ' + ' '.join(validate_command) + '\n' + validation.stdout + validation.stderr)
        result = dict(name=name, elapsed=elapsed, cold_compile=name == 'validation_small',
                      memory_limit_mib=1536, cpu_threads=1, **json.loads(runtime_path.read_text()),
                      **json.loads(validation.stdout))
        results.append(result)
        print(json.dumps(result), flush=True)
        (root / 'validation_metrics.json').write_text(json.dumps(results, indent=2) + '\n')
        (root / 'validation_cli.log').write_text('\n'.join(log))
    baselines = []
    for size in ('small', 'large'):
        data = np.load(arguments.inputs / ('validation_' + size + '.npz'), allow_pickle=False)
        labels = np.load(arguments.inputs / ('validation_' + size + '_labels.npz'), allow_pickle=False)
        prediction = np.load(root / ('baseline_' + size + '_predictions.npz'), allow_pickle=False)
        baselines.append(dict(network=size, **compare(data, labels, prediction)))
    (root / 'baseline_metrics.json').write_text(json.dumps(baselines, indent=2) + '\n')
