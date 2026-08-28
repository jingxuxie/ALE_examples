import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
from pathlib import Path
import sys
import time
import warnings

sys.dont_write_bytecode = True
PILOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PILOT / 'participant/workspace'))

import numpy as np
import scipy.optimize

from author_tools import store_json
from compat import load_source
from geometry import assemble
from hamiltonian import solve_request


def geometry(**changes):
    return dict(
        dict(W=80, L_x=80, L_sc_up=30, L_sc_down=40, z_x=80, z_y=0, a=10,
             transverse_soi=True, mu_from_bottom_of_spin_orbit_bands=True,
             k_x_in_sc=True, infinite=True), **changes
    )


def model(**changes):
    return dict(
        dict(mu=2, V=6, Delta_left=0.8, Delta_right=0.7,
             alpha_middle=20, alpha_left=10, alpha_right=12,
             g_factor_middle=10, g_factor_left=2, g_factor_right=3,
             B_x=0.1, B_y=0, B_z=0, phase=1.2), **changes
    )


def request(kind, shape, parameters):
    result = dict(version=1, kind=kind, geometry=shape, model=parameters)
    if kind == 'barrier':
        count_x = round(shape['L_x'] / shape['a'])
        result['probes'] = [[horizontal, vertical]
                            for horizontal in range(count_x)
                            for vertical in range(-12, 13)]
    else:
        result['grid_points'] = 33
    return result


def candidates():
    return [
        ('finite_straight', 'boundary_finite', request('barrier', geometry(infinite=False), model())),
        ('finite_saw', 'boundary_finite', request('barrier', geometry(z_y=20, infinite=False), model(V=3))),
        ('finite_two_cells', 'boundary_finite', request('barrier', geometry(a=8, W=64, L_x=128, z_x=64, z_y=16, L_sc_up=24, L_sc_down=32, infinite=False), model(V=9))),
        ('wrapped_straight', 'boundary_wrapped', request('barrier', geometry(), model())),
        ('wrapped_saw', 'boundary_wrapped', request('barrier', geometry(z_y=20), model(V=4))),
        ('wrapped_scaled', 'boundary_wrapped', request('barrier', geometry(a=12, W=96, L_x=96, z_x=96, z_y=12, L_sc_up=36, L_sc_down=24), model(V=8))),
        ('low_mu_straight', None, request('gap', geometry(W=60), model(mu=0.1, V=3, B_x=0.05, phase=0.2))),
        ('low_mu_saw', None, request('gap', geometry(z_y=10), model(mu=0.2, V=4, B_x=0.08, phase=0.5))),
        ('low_mu_long', None, request('gap', geometry(W=60, L_x=100, z_x=100, z_y=10, transverse_soi=False), model(mu=0.3, V=5, B_x=0.05, phase=0.7))),
        ('dispersive_straight', None, request('gap', geometry(), model(mu=4, V=3, phase=1.4))),
        ('dispersive_saw', None, request('gap', geometry(W=60, z_y=20), model(mu=5, V=4, phase=1.8))),
        ('dispersive_scaled', None, request('gap', geometry(a=12, W=96, L_x=96, z_x=96, z_y=12, L_sc_up=36, L_sc_down=36, mu_from_bottom_of_spin_orbit_bands=False), model(mu=6, V=7, B_x=0.05, phase=2.1))),
    ]


def locate_gap(source, case):
    system = assemble(source, case['geometry'])
    params = dict(source.constants, **case['model'])

    def objective(momentum):
        return float(np.min(np.abs(source.spectrum(system, dict(params, k_x=float(momentum)), k=4)[0])))

    momenta = np.linspace(0, np.pi, 65)
    values = np.array([objective(momentum) for momentum in momenta])
    minima = [(float(values[0]), 0.0), (float(values[-1]), float(np.pi))]
    for index in range(1, len(momenta) - 1):
        if values[index] <= min(values[index - 1], values[index + 1]):
            refined = scipy.optimize.minimize_scalar(
                objective, bounds=(momenta[index - 1], momenta[index + 1]),
                method='bounded', options={'xatol': 1e-10}
            )
            minima.append((float(refined.fun), float(refined.x)))
    gap, momentum = min(minima)
    return gap, momentum, len(system.sites)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    arguments = parser.parse_args()
    reference = load_source(PILOT / 'private/reference/upstream/zigzag.py', PILOT / 'private/reference')
    baseline = load_source(PILOT / 'participant/workspace/upstream/zigzag.py', PILOT / 'private/reference')
    manifest = dict(version=1, score_factor=99.0, timeout_seconds=60, memory_mib=2048, cases=[])
    for name, family, case in candidates():
        started = time.perf_counter()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            expected = solve_request(reference, case)
            weak = solve_request(baseline, case)
            system = assemble(reference, case['geometry'])
            diagnostics = dict(sites=len(system.sites), orbitals=4 * len(system.sites))
            if case['kind'] == 'gap':
                independent_gap, momentum, unused_count = locate_gap(reference, case)
                diagnostics.update(refined_gap=independent_gap, minimizer=momentum,
                                   estimator_error=abs(expected['gap'] - independent_gap))
                if abs(expected['gap'] - independent_gap) > 2e-5:
                    raise AssertionError((name, expected, diagnostics))
                if independent_gap < 1e-4:
                    raise AssertionError('Exclude nearly closed gap: ' + name)
                family = 'gap_endpoint' if min(momentum, np.pi - momentum) < 1e-5 else 'gap_interior'
            if diagnostics['sites'] > 600:
                raise AssertionError('Too large: ' + name)
        key = 'response' if case['kind'] == 'barrier' else 'gap'
        distance = float(np.sqrt(np.mean((np.asarray(expected[key]) - np.asarray(weak[key])) ** 2)))
        if distance <= 1e-8:
            raise AssertionError('Uninformative weak calibration: ' + name)
        record = dict(name=name, family=family, request='requests/' + name + '.json',
                      expected='expected/' + name + '.json', weak='weak/' + name + '.json',
                      weak_rmse=distance, reference_seconds=time.perf_counter() - started,
                      diagnostics=diagnostics)
        manifest['cases'].append(record)
        print(json.dumps(record, allow_nan=False), flush=True)
        if arguments.write:
            store_json('private/challenge_pool/' + record['request'], case)
            store_json('private/challenge_pool/' + record['expected'], expected)
            store_json('private/challenge_pool/' + record['weak'], weak)
    if arguments.write:
        store_json('private/challenge_pool/manifest.json', manifest)
        example = request('barrier', geometry(infinite=False), model())
        example['probes'] = [[2, 0], [2, 3], [2, 4], [4, -4], [9, 0]]
        store_json('participant/input/example.json', example)


if __name__ == '__main__':
    main()
