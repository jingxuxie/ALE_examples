import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import json
from pathlib import Path
import numpy as np
import torch
from optimize import from_raw, to_raw, stationary_blocks, observables
from physics import check


def main():
    candidates = []
    for name in ('energy24.npz', 'fit24_checkpoint.npz', 'fit24.npz'):
        result = check(name)
        if not result.get('passed'):
            continue
        values = result['metrics']
        worst_ratio = max(values['energy_excess'] / 5e-5,
                          values['order_max_relative_error'] / 0.025,
                          values['density_max_relative_error'] / 0.1)
        candidates.append((worst_ratio, name, result))
    if not candidates:
        raise RuntimeError('No passing candidate was found')
    worst_ratio, name, result = min(candidates, key=lambda item: item[0])
    tensor = np.load(name)['A']
    np.savez('state.npz', A=tensor)
    result = check('state.npz')
    assert result['valid'] and result['passed']
    canonical_tensor, blocks = from_raw(torch.tensor(to_raw(tensor)))
    density = stationary_blocks(blocks)
    energy, orders, densities = observables(canonical_tensor, density)
    public = result['metrics']
    crosscheck = {
        'tensor_reconstruction_max_error': float(np.max(np.abs(canonical_tensor.numpy() - tensor))),
        'energy_contraction_difference': abs(float(energy) - public['energy_density']),
        'order_contraction_max_difference': float(np.max(np.abs(orders.numpy() - public['order_correlations']))),
        'density_contraction_max_difference': float(np.max(np.abs(densities.numpy() - public['density_connected_correlations']))),
    }
    assert max(crosscheck.values()) < 1e-10
    Path('validation.json').write_text(json.dumps(result, indent=2) + '\n')
    Path('crosscheck.json').write_text(json.dumps(crosscheck, indent=2) + '\n')
    print('Selected', name, 'worst tolerance fraction', worst_ratio)
    print(json.dumps(crosscheck, indent=2))
    print(json.dumps({key: value for key, value in public.items() if 'correlations' not in key}, indent=2))


if __name__ == '__main__':
    main()
