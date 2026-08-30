import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import sys
import numpy as np
from search import ROOT, INPUT, NAMES, evaluate


def generate(count=60, seed=781293):
    rng = np.random.default_rng(seed)
    spec = json.loads((INPUT / 'spec.json').read_text())
    instances = []
    for family in spec['sampling']['families']:
        for instance_index in range(count):
            shape = spec['sampling']['lattice_shapes'][instance_index % 3]
            horizontal, vertical = shape
            size = horizontal * vertical
            matrices = np.zeros((5, size, size), dtype=complex)
            tx = rng.uniform(*family['tx'])
            if family.get('ty') == 'tx':
                ty = tx
            elif 'ty_ratio' in family:
                ty = tx * rng.uniform(*family['ty_ratio'])
                if rng.random() < family['swap_axes_probability']:
                    tx, ty = ty, tx
            else:
                ty = rng.uniform(*family['ty'])
            dx = rng.uniform(*family['dx'])
            dy = rng.uniform(*family['dy'])
            strength = rng.uniform(*family['field_strength'])
            stagger = rng.uniform(*family['stagger'])
            chemical = rng.uniform(*family['chemical_potential'])
            shared_sign = rng.choice([-1, 1])
            for ypos in range(vertical):
                for xpos in range(horizontal):
                    source = xpos + horizontal * ypos
                    for component, target, scale, dimer, coordinate in [(xpos % 2, (xpos + 1) % horizontal + horizontal * ypos, tx, dx, xpos), (2 + ypos % 2, xpos + horizontal * ((ypos + 1) % vertical), ty, dy, ypos)]:
                        amplitude = scale * (1 + dimer * (-1) ** coordinate) * rng.uniform(1 - family['disorder'], 1 + family['disorder'])
                        phase = rng.uniform(-family['phase_width'], family['phase_width'])
                        value = amplitude * np.exp(1j * phase)
                        matrices[component, source, target] = value
                        matrices[component, target, source] = value.conjugate()
                    if family['field'] == 'uniform_binary':
                        field = shared_sign
                    elif family['field'] == 'binary':
                        field = rng.choice([-1, 1])
                    else:
                        field = np.clip(rng.normal(), -2, 2)
                    potential = strength * field + stagger * (-1) ** (xpos + ypos) - chemical
                    matrices[4, source, source] = -potential
            instances.append((family['name'] + '_' + str(instance_index), family['name'], matrices))
    return instances


if __name__ == '__main__':
    artifact = json.loads((ROOT / sys.argv[1]).read_text())
    assert set(artifact) == {'schema_version', 'stages'}
    assert artifact['schema_version'] == 1
    stages = artifact['stages']
    assert len(stages) == 33
    assert all(set(stage) == {'component', 'coefficient'} for stage in stages)
    word = np.array([NAMES.index(stage['component']) for stage in stages])
    values = np.array([stage['coefficient'] for stage in stages])
    assert np.all(word[:-1] != word[1:])
    assert np.all(word == word[::-1])
    assert np.all(np.abs(values - values[::-1]) <= 1e-12)
    assert np.all(np.isfinite(values)) and values.min() >= 1e-5 and values.max() <= 1
    assert np.max(abs(np.bincount(word, weights=values, minlength=5) - 1)) <= 1e-10
    print('structurally valid', flush=True)
    instances = generate(int(sys.argv[2]) if len(sys.argv) > 2 else 60, int(sys.argv[3]) if len(sys.argv) > 3 else 781293)
    summary, ratios = evaluate(word, values, instances=instances, verbose=True)
    np.savez(ROOT / ('validation_' + sys.argv[1].replace('.json', '') + '.npz'), ratios=ratios)
