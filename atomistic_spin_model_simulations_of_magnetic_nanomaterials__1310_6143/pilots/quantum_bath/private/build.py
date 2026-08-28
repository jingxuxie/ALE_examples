import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'private' / 'reference'))
import solve as reference
from common import initialize, classical_integrate


def make_case(family, seed, large=False):
    case = dict(shape=[12, 12, 12], initial_seed=seed, noise_seed=seed + 10000, disorder=0.18,
        twist=0.5, dt=0.002, steps=768, decimation=8, nfft=256,
        sample_steps=list(range(0, 769, 96)), field=[0.25, -0.15, 1.0],
        initial_memory='equilibrated', lags=[0, 1, 2, 4, 8, 16, 32],
        materials=[dict(mu=1.0, K=0.06, A=7.0, omega0=5.0, Gamma=1.5, T=0.3,
                        initial_direction=[1.0, 0.2, 0.1])], exchange=[[0.6]], thermostat='nozero')
    if family == 'resonant_quantum':
        case['thermostat'] = 'quantum'
        case['initial_memory'] = 'empty'
        case['materials'][0].update(omega0=3.4 + (seed % 7) * 0.11, A=14.0, Gamma=0.7, T=0.05)
    elif family == 'stiff_classical':
        case['thermostat'] = 'classical'
        case['materials'][0].update(omega0=24.0, A=800.0, Gamma=7.0, T=2.0)
        case['exchange'] = [[1.7]]
        case['disorder'] = 0.38
    elif family == 'compensated_nozero':
        case['materials'].append(dict(mu=2.7, K=-0.035, A=45.0, omega0=8.0, Gamma=2.7, T=1.2,
                                     initial_direction=[-1.0, -0.1, 0.15]))
        case['exchange'] = [[0.4, -1.3], [-1.3, 0.7]]
        case['twist'] = 2.4
    if large:
        case['shape'] = [36, 36, 36]
        case['steps'] = 1536
        case['sample_steps'] = list(range(0, 1537, 192))
        case['nfft'] = 512
    return case


def weak(case):
    spins, material, neighbors, parameters = initialize(case)
    spins, trace = classical_integrate(spins, material, neighbors, parameters,
        np.asarray(case['exchange']), np.asarray(case['field']), case['dt'], case['steps'],
        np.asarray(case['sample_steps']))
    return dict(spins=spins, trace=trace, memory=np.zeros((len(spins), 6)),
        covariance=np.zeros((len(parameters), len(case['lags']))))


def validate():
    case = make_case('resonant_quantum', 921)
    case.update(shape=[2, 2, 2], steps=48, sample_steps=[0, 24, 48], dt=0.001)
    full = reference.solve(case)
    refined = reference.solve(case, substeps=4)
    spins, material, neighbors, parameters = initialize(case)
    noise, covariance = reference.forcing(case, material)
    initial = np.zeros((len(spins), 9))
    initial[:, :3] = spins

    def right_hand_side(time, flat):
        state = flat.reshape((-1, 9))
        field = np.broadcast_to(case['field'], (len(spins), 3)).copy()
        for atom in range(len(spins)):
            species = material[atom]
            for neighbor in neighbors[atom]:
                field[atom] += case['exchange'][species][material[neighbor]] * state[neighbor, :3] / parameters[species, 0]
            field[atom, 2] += 2 * parameters[species, 1] * state[atom, 2] / parameters[species, 0]
            position = time / (case['dt'] * case['decimation'])
            left = min(int(position), noise.shape[2] - 2)
            fraction = position - left
            field[atom] += ((1 - fraction) * noise[atom, :, left] + fraction * noise[atom, :, left + 1]) / np.sqrt(parameters[species, 0])
        derivative = np.zeros_like(state)
        derivative[:, :3] = np.cross(state[:, :3], field + state[:, 3:6])
        derivative[:, 3:6] = state[:, 6:]
        derivative[:, 6:] = (parameters[material, 2, None] * state[:, :3]
            - parameters[material, 3, None] ** 2 * state[:, 3:6] - parameters[material, 4, None] * state[:, 6:])
        return derivative.ravel()

    independent = solve_ivp(right_hand_side, [0, case['steps'] * case['dt']], initial.ravel(),
        method='DOP853', rtol=1e-10, atol=1e-11, max_step=case['dt'] / 4).y[:, -1].reshape((-1, 9))
    comparison = dict(independent_spin_max=float(np.max(np.abs(full['spins'] - independent[:, :3]))),
        independent_memory_max=float(np.max(np.abs(full['memory'] - independent[:, 3:]))),
        step_refinement_max=float(np.max(np.abs(full['spins'] - refined['spins']))),
        zero_temperature_nozero_max=float(np.max(reference.spectrum(np.linspace(0, 40, 301),
            dict(case['materials'][0], T=0.0), 'nozero'))))
    assert comparison['independent_spin_max'] < 2e-7
    assert comparison['independent_memory_max'] < 2e-7
    assert comparison['zero_temperature_nozero_max'] == 0
    (ROOT / 'private' / 'reference' / 'independent_validation.json').write_text(json.dumps(comparison, indent=2))
    return comparison


def main():
    validate()
    manifest = []
    families = ['resonant_quantum', 'stiff_classical', 'compensated_nozero']
    public = make_case('stiff_classical', 19)
    public.update(shape=[8, 8, 8], steps=96, sample_steps=[0, 48, 96])
    (ROOT / 'participant' / 'input' / 'example.json').write_text(json.dumps(public, indent=2))
    for split, seeds in [('initial', [1123, 2317]), ('challenge', [4103, 5521, 6719])]:
        for family_index, family in enumerate(families):
            for seed_index, seed in enumerate(seeds):
                identity = f'{split}_{family}_{seed}'
                large = seed_index == 1 and (family_index == 0 or split == 'challenge')
                case = make_case(family, seed, large)
                destination = ROOT / 'private' / 'challenge_pool' / (identity + '.json')
                destination.write_text(json.dumps(case, indent=2))
                started = time.monotonic()
                answer = reference.solve(case)
                baseline = weak(case)
                elapsed = time.monotonic() - started
                weak_errors = {key: float(np.sqrt(np.mean((baseline[key] - answer[key]) ** 2))) for key in answer}
                np.savez_compressed(ROOT / 'private' / 'reference' / (identity + '.npz'), **answer)
                manifest.append(dict(id=identity, family=family, split=split, weak_errors=weak_errors,
                    atoms=int(np.prod(case['shape'])), reference_and_baseline_seconds=elapsed,
                    case_sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
                (ROOT / 'private' / 'manifest.json').write_text(json.dumps(manifest, indent=2))
                print(identity, elapsed, weak_errors, flush=True)


if __name__ == '__main__':
    main()
