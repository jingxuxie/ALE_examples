import hashlib
import json
from pathlib import Path
import secrets
import numpy as np
from search_regimes import regime_split


ROOT = Path(__file__).resolve().parents[1]


def main():
    seeds = {name: secrets.randbits(96) for name in ['train', 'validation', 'test']}
    checksums = {}
    for name, per_family in [('train', 2048), ('validation', 128), ('test', 96)]:
        inputs, labels = regime_split(seeds[name], per_family, 'warm_noisy_weak')
        directory = ROOT / ('evaluator/hidden' if name == 'test' else 'participant/input')
        for suffix, arrays in [('input', inputs), ('labels', labels)]:
            path = directory / f'{name}_{suffix}.npz'
            np.savez_compressed(path, **arrays)
            checksums[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        print(name, len(labels['family']), flush=True)
    manifest = {'version': '2.0', 'regime': 'warm_noisy_weak', 'private_seeds': seeds, 'sha256': checksums,
                'temperature_range': [4.0, 6.0], 'coupling_range': [0.55, 1.1], 'noise_scale_range': [0.0012, 0.002],
                'population': 'Same four smooth spectral families. Training, validation, and test independently follow the same conditional operating regime.',
                'reproducer': 'adversary/search_regimes.py:regime_split with the saved seeds and warm_noisy_weak regime'}
    (ROOT / 'evaluator/hidden/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
