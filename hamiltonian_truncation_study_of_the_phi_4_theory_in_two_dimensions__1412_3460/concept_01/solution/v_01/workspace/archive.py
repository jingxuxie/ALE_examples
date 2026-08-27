import json
from pathlib import Path

import numpy as np
from scipy import sparse

def write_archive(path, case, cutoff):
    from basis import enumerate_basis
    from operators import operator_matrix

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    operators = sorted({(degree, transfer)
                        for degree in range(5)
                        for transfer in case.get('operator_transfers', [0])})
    manifest = {'length': case['length'], 'mass': case['mass'], 'boundary': case['boundary'],
                'cutoff': cutoff, 'operators': [], 'sectors': []}
    for sector in case['sectors']:
        modes, frequencies, states, energies = enumerate_basis(
            case['length'], case['mass'], cutoff, case['boundary'],
            sector['momentum'], sector['parity'])
        label = sector['name']
        np.savez_compressed(path / (label + '_basis.npz'), modes=modes, frequencies=frequencies,
                            occupations=states, free_energy=energies)
        sector_record = dict(sector, size=len(states))
        manifest['sectors'].append(sector_record)
        print(path.name, label, len(states), 'states', flush=True)
        for degree, transfer in operators:
            if sector['parity'] is not None and degree % 2:
                continue
            if sector['momentum'] is not None and transfer != 0:
                continue
            matrix = operator_matrix(modes, frequencies, states, case['length'], degree, transfer)
            name = f'{label}_v{degree}_q{transfer}.npz'
            sparse.save_npz(path / name, matrix)
            manifest['operators'].append({'sector': label, 'degree': degree, 'transfer': transfer, 'file': name})
    (path / 'manifest.json').write_text(json.dumps(manifest, indent=2))


def load_archive(path, cutoff):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text())
    sectors = {}
    for sector in manifest['sectors']:
        label = sector['name']
        basis = np.load(path / (label + '_basis.npz'))
        keep = np.flatnonzero(basis['free_energy'] <= cutoff + 1e-9)
        matrices = {}
        for operator in manifest['operators']:
            if operator['sector'] == label:
                matrix = sparse.load_npz(path / operator['file'])
                matrices[(operator['degree'], operator['transfer'])] = matrix[keep][:, keep]
        sectors[label] = {'energy': basis['free_energy'][keep], 'operators': matrices}
    return manifest, sectors
