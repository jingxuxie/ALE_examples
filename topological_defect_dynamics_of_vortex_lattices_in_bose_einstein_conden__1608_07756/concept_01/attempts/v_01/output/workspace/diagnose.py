import json
import sys
from pathlib import Path

import numpy as np


def diagnose(manifest_path, output_path):
    manifest_path = Path(manifest_path)
    for case in json.loads(manifest_path.read_text())['cases']:
        with np.load(manifest_path.parent / case['asset']) as asset:
            area = (asset['x'][1] - asset['x'][0]) * (asset['y'][1] - asset['y'][0])
            initial_density = np.abs(asset['psi']) ** 2
        with np.load(Path(output_path) / (case['id'] + '.npz')) as saved:
            density = np.abs(saved['psi']) ** 2
        norms = density.sum(axis=(1, 2)) * area
        first_change = np.linalg.norm(density[0] - initial_density) / np.linalg.norm(initial_density)
        print(json.dumps({'case': case['id'], 'max_norm_drift': float(np.max(np.abs(norms - norms[0]))), 'imprint_density_change': float(first_change), 'final_density_change': float(np.linalg.norm(density[-1] - density[0]) / np.linalg.norm(density[0]))}))


if __name__ == '__main__':
    diagnose(sys.argv[1], sys.argv[2])
