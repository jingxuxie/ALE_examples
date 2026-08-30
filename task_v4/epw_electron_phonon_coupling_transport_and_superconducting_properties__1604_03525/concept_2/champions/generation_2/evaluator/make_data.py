import json
from pathlib import Path
import numpy as np
from scipy.linalg import qr


def make_case(seed, family, state_count, branch_count=4):
    generator = np.random.default_rng(seed)
    positions = generator.normal(size=(state_count, 3))
    positions /= np.linalg.norm(positions, axis=1)[:, None]
    source, target = np.triu_indices(state_count, 1)
    distance = np.sum((positions[source] - positions[target]) ** 2, axis=1)
    valley_count = 3 + seed % 3
    labels = np.arange(state_count) % valley_count
    generator.shuffle(labels)
    same = labels[source] == labels[target]
    channels = []
    for branch in range(branch_count):
        axis = generator.normal(size=3)
        axis /= np.linalg.norm(axis)
        projection = positions @ axis
        texture = np.exp(generator.uniform(0.4, 1.4) * (projection[source] + projection[target]))
        if family == 'forward':
            width = generator.uniform(0.09, 0.6) * (1 + branch * 0.3)
            weights = np.exp(-distance / width) + generator.uniform(0.003, 0.025)
        elif family == 'valleys':
            intervalley = 10 ** generator.uniform(-3.2, -1.0) if branch < 2 else generator.uniform(0.1, 0.8)
            weights = np.where(same, 1.0, intervalley) * (0.08 + np.exp(-distance / 1.1))
        elif family == 'hot_regions':
            hot = np.exp(generator.uniform(1.4, 3.5) * projection)
            weights = (0.005 + np.sqrt(hot[source] * hot[target])) * (0.03 + np.exp(-distance / 0.35))
        elif family == 'mixed_scales':
            hotspots = np.sin((branch + 2) * projection * np.pi) ** 2 + 0.02
            weights = (0.003 + np.exp(-distance / generator.uniform(0.09, 1.2)))
            weights *= np.sqrt(hotspots[source] * hotspots[target])
            weights *= np.where(same, 1, 10 ** generator.uniform(-2, -0.3))
        else:
            raise ValueError(family)
        channels.append(weights * texture * generator.lognormal(0, 0.25, len(source)))
    channels = np.column_stack(channels)
    channels /= channels.mean(axis=0)
    phonon_mev = np.geomspace(generator.uniform(2, 5), generator.uniform(60, 95), branch_count)
    temperatures = np.array([18., 32., 60., 110., 200., 350.])
    thermal_ratio = phonon_mev[None, :] / (0.08617333262145 * temperatures[:, None])
    mixing = thermal_ratio / np.sinh(thermal_ratio / 2) ** 2
    mixing /= mixing.sum(axis=1)[:, None]
    velocity = positions + 0.15 * generator.normal(size=positions.shape)
    if family in ('valleys', 'mixed_scales'):
        velocity += generator.normal(size=(valley_count, 3))[labels]
    velocity -= velocity.mean(axis=0)
    velocity, _ = qr(velocity, mode='economic')
    probes = [velocity[:, index] for index in range(3)]
    for axis in range(3):
        for frequency in (1, 2, 3, 4):
            probes.append(np.sin(frequency * np.pi * positions[:, axis]))
    for label in range(valley_count):
        probes.append((labels == label).astype(float))
    probes = np.column_stack(probes)
    probes -= probes.mean(axis=0)
    probes /= np.linalg.norm(probes, axis=0)
    budget = state_count * 8
    return dict(source=source, target=target, channels=channels, mixing=mixing,
                velocities=velocity, probes=probes, positions=positions, budget=np.array(budget),
                temperatures=temperatures)


def main():
    root = Path(__file__).resolve().parents[1]
    hidden = root / 'evaluator' / 'hidden'
    public = root / 'participant' / 'input'
    hidden.mkdir(parents=True, exist_ok=True)
    families = ['forward', 'valleys', 'hot_regions', 'mixed_scales']
    manifest = []
    public_manifest = []
    for family_index, family in enumerate(families):
        for replicate in range(3):
            name = f'{family}_{replicate}'
            seed = 804729 + 73 * family_index + 19 * replicate
            case = make_case(seed, family, [96, 120, 144][replicate], 3 + replicate)
            np.savez_compressed(hidden / f'{name}.npz', **case)
            manifest.append(dict(name=name, family=family, path=f'{name}.npz'))
        for replicate in range(2):
            name = f'development_{family}_{replicate}'
            case = make_case(1300 + 57 * family_index + replicate, family, 80 + 16 * replicate, 4)
            np.savez_compressed(public / f'{name}.npz', **case)
            public_manifest.append(dict(name=name, family=family, path=f'{name}.npz'))
    (hidden / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (public / 'manifest.json').write_text(json.dumps(public_manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
