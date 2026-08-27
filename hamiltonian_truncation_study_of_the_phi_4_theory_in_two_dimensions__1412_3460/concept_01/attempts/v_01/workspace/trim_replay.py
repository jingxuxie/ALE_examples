import json
import sys
from pathlib import Path

import numpy as np
from scipy import sparse


def trim(request_path, destination, cutoff=12):
    request_path, destination = Path(request_path).resolve(), Path(destination).resolve()
    request = json.loads(request_path.read_text())
    original_root = Path(request['archive_root'])
    if not original_root.is_absolute():
        original_root = request_path.parent / original_root
    destination.mkdir(parents=True, exist_ok=True)
    request['archive_root'] = 'renamed_archives'
    for index, case in enumerate(request['cases']):
        original = original_root / case['archive']
        renamed = f'opaque_{index:02d}'
        target = destination / request['archive_root'] / renamed
        target.mkdir(parents=True, exist_ok=True)
        manifest = json.loads((original / 'manifest.json').read_text())
        manifest['cutoff'] = cutoff
        for sector in manifest['sectors']:
            with np.load(original / (sector['name'] + '_basis.npz')) as archive:
                keep = np.flatnonzero(archive['free_energy'] <= cutoff + 1e-9)
                np.savez(target / (sector['name'] + '_basis.npz'), modes=archive['modes'],
                         frequencies=archive['frequencies'], free_energy=archive['free_energy'][keep],
                         occupations=archive['occupations'][keep])
            sector['size'] = len(keep)
            for operator in manifest['operators']:
                if operator['sector'] == sector['name']:
                    matrix = sparse.load_npz(original / operator['file'])
                    sparse.save_npz(target / operator['file'], matrix[keep][:, keep])
        (target / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        case['archive'] = renamed
        case['cutoffs'] = [10, cutoff]
    (destination / 'request.json').write_text(json.dumps(request, indent=2))


if __name__ == '__main__':
    trim(sys.argv[1], sys.argv[2])
