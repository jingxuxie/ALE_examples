import json
from pathlib import Path

import numpy as np
from scipy import sparse


def load_archive(path, cutoff, labels=None):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text())
    if cutoff > manifest['cutoff'] + 1e-8:
        raise ValueError('Requested cutoff exceeds the supplied projection')
    sectors = {}
    for sector in manifest['sectors']:
        label = sector['name']
        if labels is not None and label not in labels:
            continue
        basis = np.load(path / (label + '_basis.npz'))
        keep = np.flatnonzero(basis['free_energy'] <= cutoff + 1e-9)
        matrices = {}
        for operator in manifest['operators']:
            if operator['sector'] == label:
                matrix = sparse.load_npz(path / operator['file'])
                matrices[(operator['degree'], operator['transfer'])] = matrix[keep][:, keep]
        sectors[label] = {'energy': basis['free_energy'][keep], 'operators': matrices,
                          'modes': basis['modes'], 'occupations': basis['occupations'][keep]}
    return manifest, sectors
