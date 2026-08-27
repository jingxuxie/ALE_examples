import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np

from .physics import load_case, observables
from .predictor import predict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case')
    parser.add_argument('destination')
    parser.add_argument('--mode', default='selected',
                        choices=['selected', 'baseline', 'no_memory', 'refined'])
    arguments = parser.parse_args()
    case, arrays = load_case(arguments.case)
    started = time.perf_counter()
    channel, generator, diagnostics = predict(case, arrays, arguments.mode)
    elapsed = time.perf_counter() - started
    destination = Path(arguments.destination)
    destination.mkdir(parents=True, exist_ok=True)
    np.savez(destination / 'process.npz', channel=channel, k2=generator)
    metrics = observables(channel, arrays)
    metrics.update(case_id=case['case_id'], mode=arguments.mode, seconds=elapsed,
                   peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                   k2_norm=float(np.linalg.norm(generator)), diagnostics=diagnostics)
    (destination / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(json.dumps(metrics))


if __name__ == '__main__':
    main()
