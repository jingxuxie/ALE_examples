import importlib.util
import json
from pathlib import Path
import shutil
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main():
    spec = importlib.util.spec_from_file_location('private_catalogues', ROOT / 'evaluator/make_data.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    hidden = ROOT / 'evaluator/hidden/generation_2'
    hidden.mkdir(parents=True, exist_ok=True)
    public = ROOT / 'participant/input'
    manifest = []
    development = json.loads((public / 'manifest.json').read_text())
    for family_index, family in enumerate(['forward', 'valleys', 'hot_regions', 'mixed_scales']):
        for replicate in range(4):
            is_public = replicate == 3
            state_count = [384, 416, 448, 384][replicate]
            branch_count = [6, 7, 8, 8][replicate]
            name = f'generation_2_{family}_{replicate}'
            seed = 9811472 + 403 * family_index + 67 * replicate
            data = generator.make_case(seed, family, state_count, branch_count)
            temperatures = np.geomspace(18, 350, 10)
            energies = np.geomspace(2.5, 85, branch_count)
            thermal = energies[None, :] / (0.08617333262145 * temperatures[:, None])
            mixing = thermal / np.sinh(thermal / 2) ** 2
            mixing /= mixing.sum(axis=1)[:, None]
            data.update(temperatures=temperatures, mixing=mixing)
            destination = public if is_public else hidden
            np.savez_compressed(destination / f'{name}.npz', **data)
            row = {'name': name, 'family': family, 'path': f'{name}.npz' if is_public else f'generation_2/{name}.npz'}
            (development if is_public else manifest).append(row)
    (ROOT / 'evaluator/hidden/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (public / 'manifest.json').write_text(json.dumps(development, indent=2) + '\n')
    baseline = ROOT / 'participant/baseline'
    shutil.copy2(ROOT / 'champions/generation_1/participant/baseline/solve.py', baseline / 'solve.py')
    print(json.dumps({'hidden_cases': len(manifest), 'large_public_cases': 4, 'baseline': 'unchanged public weak baseline; champion remains private'}))


if __name__ == '__main__':
    main()
