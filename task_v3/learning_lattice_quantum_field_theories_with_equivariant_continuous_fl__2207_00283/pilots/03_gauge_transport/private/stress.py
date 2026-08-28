import sys
import json
import time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import case, weak
from reference.solver import solve, vector_divergence, jnp


def gauge_links(links, matrices):
    result = np.empty_like(links)
    for direction in range(2):
        shifted = np.roll(matrices, -1, axis=direction)
        result[:, :, direction] = matrices @ links[:, :, direction] @ shifted.conj().swapaxes(-1, -2)
    return result


def gauge_algebra(algebra, matrices):
    return matrices[:, :, None] @ algebra @ matrices.conj().swapaxes(-1, -2)[:, :, None]


def main():
    folder = HERE / 'reference/stress'
    folder.mkdir(exist_ok=True)
    records = []
    source = json.loads((HERE / 'challenge_pool/manifest.json').read_text())
    for group, index in ((1, 1), (3, 0)):
        name = f'gauge_conjugated_g{group}'
        original = next(record for record in source if record['id'] == f'challenge_g{group}_{index}')
        with np.load(HERE / 'challenge_pool' / original['input']) as archive:
            data = dict(archive)
        with np.load(HERE / 'challenge_pool' / original['reference']) as archive:
            target = dict(archive)
        matrices = case(49031 + group, data['links'].shape[:2], group, 0.0, 0.1)['links'][:, :, 0]
        data['links'] = gauge_links(data['links'], matrices)
        data['probe'] = gauge_links(data['probe'], matrices)
        target['state'] = gauge_links(target['state'], matrices)
        target['vector'] = gauge_algebra(target['vector'], matrices)
        target['initial_gradient'] = gauge_algebra(target['initial_gradient'], matrices)
        record = dict(original, id=name, family=f'g{group}_gauge_covariance', input=name + '.npz', reference=name + '.reference.npz', seed=49031 + group)
        np.savez(folder / record['input'], **data)
        np.savez(folder / record['reference'], **target)
        records.append(record)
    data = case(77181, (16, 16), 3, 0.21, 0.24)
    data['links'] = np.broadcast_to(np.eye(3, dtype=complex), data['links'].shape).copy()
    began = time.monotonic()
    target = solve(data)
    elapsed = time.monotonic() - began
    baseline = weak(data)
    errors = {name: max(float(np.sqrt(np.mean(np.abs(value - baseline[name])**2))), 1e-8) for name, value in target.items()}
    record = {'id': 'su3_stationary_density', 'family': 'g3_zero_drift_nonzero_density', 'input': 'stationary.npz',
              'reference': 'stationary.reference.npz', 'regime': 'exact_identity', 'seed': 77181,
              'size': [16, 16], 'weak_error': errors, 'reference_seconds': elapsed}
    np.savez(folder / record['input'], **data)
    np.savez(folder / record['reference'], **target)
    records.append(record)
    (folder / 'manifest.json').write_text(json.dumps(records, indent=2))
    fine = solve(data, steps=512)
    validation = {name: float(np.sqrt(np.mean(np.abs(value - fine[name])**2))) / errors[name] for name, value in target.items()}
    validation['stationary_drift'] = float(np.max(np.abs(target['state'] - data['links'])))
    validation['initial_divergence'] = float(target['divergence'])
    validation['terminal_log_density'] = float(target['log_density'])
    start, stop = float(data['t0']), float(data['t1'])
    time_integrals = np.array((stop - start,
                              (np.cos(2 * np.pi * start) - np.cos(2 * np.pi * stop)) / (2 * np.pi),
                              (np.sin(2 * np.pi * stop) - np.sin(2 * np.pi * start)) / (2 * np.pi)))
    integrated_weights = np.zeros_like(data['weights'])
    integrated_weights[:, 0, :] = np.einsum('t,ktf->kf', time_integrals, data['weights'])
    exact_log_density = -float(vector_divergence(0., jnp.asarray(data['links']), jnp.asarray(integrated_weights), jnp.asarray(data['generators']))[1])
    validation['analytic_density_relative_error'] = abs(float(target['log_density']) - exact_log_density) / errors['log_density']
    validation['minimum_component_score'] = min(1 / (1 + 9 * np.sqrt(validation[name])) for name in target)
    (folder / 'validation.json').write_text(json.dumps(validation, indent=2))
    print(json.dumps(validation, indent=2), flush=True)
    if validation['minimum_component_score'] <= 0.9:
        raise RuntimeError('Stationary reference needs refinement')


if __name__ == '__main__':
    main()
