import argparse
import json
from pathlib import Path

import numpy as np

from physics import check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidates', nargs='+')
    arguments = parser.parse_args()
    families = ['energy_excess', 'order_max_relative_error', 'density_max_relative_error', 'y_max_relative_error', 'composite_order_max_relative_error']
    limits = np.array([5e-5, 0.025, 0.1, 0.1, 0.01])
    best = None
    for candidate in arguments.candidates:
        if not Path(candidate).is_file():
            continue
        result = check(candidate)
        if not result['valid']:
            print(candidate, result['reason'], flush=True)
            continue
        ratios = np.array([result['metrics'][family] for family in families]) / limits
        print(candidate, result['passed'], ratios.tolist(), flush=True)
        if best is None or max(ratios) < best[0]:
            best = (max(ratios), candidate)
    if best is None:
        raise RuntimeError('No admissible candidate')
    with np.load(best[1], allow_pickle=False) as archive:
        tensor = archive['A'].copy()
    np.savez('state.npz', A=tensor)
    result = check('state.npz')
    Path('validation.json').write_text(json.dumps(result, indent=2) + '\n')
    summary = {key: value for key, value in result.items() if key != 'metrics'}
    summary['source_candidate'] = best[1]
    summary['metrics'] = {key: value for key, value in result['metrics'].items() if not isinstance(value, list)}
    Path('summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)
    if not result['passed']:
        raise RuntimeError('Final candidate fails a witness condition')


if __name__ == '__main__':
    main()
