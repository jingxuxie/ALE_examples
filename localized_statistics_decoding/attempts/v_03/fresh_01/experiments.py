import argparse
import json
import os
from pathlib import Path
import time

import numpy as np

from solve import solve
from validate import compare


def run(inputs, settings, output_path):
    results = []
    for name, parameters in settings:
        for key in list(os.environ):
            if key.startswith('DECODER_'):
                del os.environ[key]
        os.environ.update({key: str(value) for key, value in parameters.items()})
        for size in ('small', 'large'):
            with np.load(inputs / ('validation_' + size + '.npz'), allow_pickle=False) as data:
                with np.load(inputs / ('validation_' + size + '_labels.npz'), allow_pickle=False) as labels:
                    started = time.perf_counter()
                    predictions = solve(data)
                    elapsed = time.perf_counter() - started
                    metrics = compare(data, labels, predictions)
                    correction = predictions['correction']
                    recovered = ((correction @ data['L'].T) % 2 == labels['logical_target']).all(axis=1)
                    result = dict(name=name, network=size, parameters=parameters, elapsed=elapsed,
                                  failed_frames=np.flatnonzero(~recovered).tolist(), **metrics)
                    result['diagnostics'] = predictions['diagnostics'].tolist()
                    results.append(result)
                    print(json.dumps({key: value for key, value in result.items() if key != 'diagnostics'}), flush=True)
                    np.savez_compressed(output_path.parent / (name + '_' + size + '_predictions.npz'), **predictions)
                    output_path.write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    settings = [
        ('prior_osd0', {'DECODER_GROUPED': 0, 'DECODER_ATTEMPTS': 0, 'DECODER_DEPTH': 0}),
        ('prior_osd2', {'DECODER_GROUPED': 1, 'DECODER_ATTEMPTS': 0, 'DECODER_DEPTH': 40}),
        ('binary_single', {'DECODER_GROUPED': 0, 'DECODER_ATTEMPTS': 1, 'DECODER_DEPTH': 40}),
        ('grouped_single', {'DECODER_GROUPED': 1, 'DECODER_ATTEMPTS': 1, 'DECODER_DEPTH': 40}),
        ('grouped_osd0', {'DECODER_GROUPED': 1, 'DECODER_ATTEMPTS': 40, 'DECODER_DEPTH': 0}),
        ('grouped_ensemble', {'DECODER_GROUPED': 1, 'DECODER_ATTEMPTS': 256, 'DECODER_ITERATIONS': 80, 'DECODER_DEPTH': 60}),
    ]
    run(arguments.inputs, settings, arguments.output)
