import os
os.environ.setdefault('JAX_ENABLE_X64', 'true')
os.environ.setdefault('JAX_PLATFORMS', 'cpu')
import sys
import json
import time
import argparse
from pathlib import Path
import numpy as np
from scipy.linalg import expm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'reference'))
from solver import solve, vector_divergence, potential, lie, jax, jnp


def case(seed, size, group, start, duration, regime='haar'):
    rng = np.random.default_rng(seed)
    generators = np.asarray({1: lie.U1_GEN, 2: lie.SU2_GEN, 3: lie.SU3_GEN}[group])
    if group == 1:
        links = np.exp(1j * rng.uniform(-np.pi, np.pi, size + (2, 1, 1)))
    else:
        random = rng.normal(size=size + (2, group, group)) + 1j * rng.normal(size=size + (2, group, group))
        links, triangular = np.linalg.qr(random)
        diagonal = np.diagonal(triangular, axis1=-2, axis2=-1)
        links = links * (diagonal / np.abs(diagonal)).conj()[..., None, :]
        links[..., :, 0] /= np.linalg.det(links)[..., None]
    if regime == 'near_center':
        components = rng.normal(size=size + (2, len(generators))) * 0.055
        algebra = np.einsum('...a,aij->...ij', components, generators)
        links = np.stack([expm(matrix) for matrix in algebra.reshape(-1, group, group)]).reshape(algebra.shape)
        if group > 1:
            links = links * np.exp(2j * np.pi * rng.integers(group, size=size + (2, 1, 1)) / group)
    weights = rng.normal(size=(3, 3, 4)) * (0.075 if regime == 'haar' else 0.11)
    weights[0, 0, 0] += 0.3
    probe = (rng.normal(size=links.shape) + 1j * rng.normal(size=links.shape)) / np.sqrt(links.size)
    return {'links': links, 'weights': weights, 'generators': generators,
            't0': np.array(start), 't1': np.array(start + duration),
            'probe': probe, 'density_weight': np.array(0.04 / np.sqrt(np.prod(size)))}


def weak(data):
    return {'vector': np.zeros_like(data['links']), 'divergence': np.array(0.),
            'state': data['links'], 'log_density': np.array(0.),
            'weight_gradient': np.zeros_like(data['weights']),
            'initial_gradient': np.zeros_like(data['links'])}


def verify_local():
    data = case(2190, (3, 3), 2, 0.23, 0.05)
    links, weights, generators = [jnp.asarray(data[name]) for name in ('links', 'weights', 'generators')]
    field, divergence = vector_divergence(data['t0'], links, weights, generators)
    flat_links = links.reshape(-1, 2, 2)
    scalar = lambda value: potential(value.reshape(links.shape), weights, data['t0'])
    exact = 0.0
    for link_index in range(flat_links.shape[0]):
        for generator in generators:
            def directional(value):
                tangent = jnp.zeros_like(value).at[link_index].set(generator @ value[link_index])
                return jax.jvp(scalar, (value,), (tangent,))[1]
            tangent = jnp.zeros_like(flat_links).at[link_index].set(generator @ flat_links[link_index])
            exact += float(jax.jvp(directional, (flat_links,), (tangent,))[1])
    relative = abs(exact - float(divergence)) / max(1.0, abs(exact))
    return {'explicit_link_trace': exact, 'local_reference_trace': float(divergence),
            'relative_error': relative, 'pass': relative < 2e-10}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--validate-local', action='store_true')
    parser.add_argument('--pool', default='initial', choices=('initial', 'challenge', 'ratchet1', 'heldout1'))
    args = parser.parse_args()
    if args.validate_local:
        result = verify_local()
        (HERE / 'reference/local_validation.json').write_text(json.dumps(result, indent=2))
        print(result, flush=True)
        if not result['pass']:
            raise RuntimeError('Independent trace validation failed')
        return
    cases = []
    if args.quick:
        design = [('su2_smoke', 3021, (4, 4), 2, 0.12, 0.11, 'haar')]
    elif args.pool == 'initial':
        design = [('u1_forward', 3091, (16, 16), 1, 0.07, 0.19, 'haar'),
                  ('su2_forward', 4017, (16, 16), 2, 0.19, 0.22, 'haar'),
                  ('su3_forward', 5907, (16, 16), 3, 0.32, 0.18, 'haar'),
                  ('u1_reverse', 5109, (8, 12), 1, 0.73, -0.27, 'haar'),
                  ('su2_reverse', 6147, (12, 8), 2, 0.81, -0.21, 'haar'),
                  ('su3_reverse', 7113, (8, 12), 3, 0.94, -0.26, 'haar')]
    else:
        base = {'challenge': 8123, 'ratchet1': 10217, 'heldout1': 15971}[args.pool]
        design = [(f'{args.pool}_g{group}_{mode}', base + group * 79 + mode * 23,
                   (16, 16) if mode == 0 else (12, 16), group,
                   0.21 if mode == 0 else 1.17,
                   0.41 if mode == 0 else -0.39, 'near_center')
                  for group in (1, 2, 3) for mode in (0, 1)]
    output = HERE / ('reference/smoke' if args.quick else 'challenge_pool' if args.pool == 'challenge' else f'reference/{args.pool}')
    output.mkdir(parents=True, exist_ok=True)
    for name, seed, size, group, start, duration, regime in design:
        data = case(seed, size, group, start, duration, regime)
        input_path = output / f'{name}.npz'
        reference_path = output / f'{name}.reference.npz'
        np.savez(input_path, **data)
        started = time.monotonic()
        result = solve(data, steps=256)
        elapsed = time.monotonic() - started
        np.savez(reference_path, **result)
        baseline = weak(data)
        scales = {key: max(float(np.sqrt(np.mean(np.abs(result[key] - baseline[key])**2))), 1e-8) for key in result}
        record = {'id': name, 'family': f'g{group}_' + ('reverse' if duration < 0 else 'forward'),
                  'regime': regime, 'seed': seed, 'size': size, 'input': input_path.name,
                  'reference': reference_path.name, 'weak_error': scales, 'reference_seconds': elapsed}
        cases.append(record)
        (output / 'manifest.json').write_text(json.dumps(cases, indent=2))
        print(json.dumps(record), flush=True)
        if args.quick:
            finer = solve(data, steps=512)
            convergence = {key: float(np.sqrt(np.mean(np.abs(result[key] - finer[key])**2))) / scales[key] for key in result}
            (HERE / 'reference/convergence.json').write_text(json.dumps(convergence, indent=2))
            print('convergence', convergence, flush=True)
    if args.pool == 'initial' and not args.quick:
        public = HERE.parent / 'participant/input'
        for index, group in enumerate((1, 3)):
            np.savez(public / f'smoke_{index}.npz', **case(31 + index, (4, 4), group, 0.1, 0.1))


if __name__ == '__main__':
    main()
