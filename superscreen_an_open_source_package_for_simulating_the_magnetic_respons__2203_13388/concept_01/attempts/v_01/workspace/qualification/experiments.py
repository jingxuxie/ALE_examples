import argparse
import copy
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np

from .cli import write_csv
from .evidence import relative_error
from .galerkin import SheetModel, evaluate_field, quadrature, solve, warm_kernels
from .model import MU0, PHI0, DeviceCase, load_case, triangle_geometry


def save_case(case, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **case.data)
    path.with_suffix('.json').write_text(json.dumps(case.meta, indent=2))


def changed_case(original, identifier):
    case = DeviceCase({key: value.copy() for key, value in original.data.items()}, copy.deepcopy(original.meta))
    case.meta['id'] = identifier
    return case


def stress(inputs, output):
    original = load_case(inputs / 'dev_stack.npz')
    rows = []
    for gap in (0.008, 0.0008, 0.000008):
        for material_scale in (1.0, 0.01):
            identifier = f'gap_{gap:g}_lambda_{material_scale:g}'
            case = changed_case(original, identifier)
            case.data['points'][case.point_film == 1, 2] = gap
            case.data['lambdas'] *= material_scale
            case.meta['films'][1]['z0'] = gap
            for spec in case.meta['films']:
                spec['nominal_lambda'] *= material_scale
            save_case(case, output / 'experiments' / 'inputs' / f'{identifier}.npz')
            results = {}
            for configuration in ('fixed12', 'qualified', 'reference', 'high_reference'):
                if configuration == 'high_reference' and (gap != 0.000008 or material_scale != 0.01):
                    continue
                start = time.perf_counter()
                result = solve(case, config=configuration)
                elapsed = time.perf_counter() - start
                target = output / 'raw' / configuration / f'{identifier}.npz'
                target.parent.mkdir(exist_ok=True, parents=True)
                np.savez_compressed(target, **result)
                results[configuration] = result
                rows.append({'case': identifier, 'gap_um': gap, 'lambda_scale': material_scale,
                             'configuration': configuration, 'seconds': elapsed,
                             'setup_seconds': float(result['timing_setup']),
                             'max_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024})
                print(identifier, configuration, round(elapsed, 3), flush=True)
            reference_name = 'high_reference' if 'high_reference' in results else 'reference'
            for row in rows:
                if row['case'] == identifier:
                    for key in ('stream', 'current', 'field', 'inductance'):
                        row[f'{key}_relative_error'] = relative_error(results[row['configuration']][key], results[reference_name][key])
                    row['comparison_configuration'] = reference_name
    write_csv(output / 'stress.csv', rows)


def reuse(inputs, output):
    rows = []
    warm_kernels()
    for path in sorted(inputs.glob('dev_*.npz')):
        case = load_case(path)
        model = SheetModel(case)
        first = model.solve()
        durations, solve_times, field_times = [], [], []
        altered = changed_case(case, case.meta['id'])
        for repetition in range(30):
            altered.data['drive_H'] = case.drive_H * (1 + repetition / 100)
            altered.data['vortex_load'] = case.vortex_load * (1 + repetition / 100)
            start = time.perf_counter()
            result = model.solve(altered)
            durations.append(time.perf_counter() - start)
            solve_times.append(float(result['timing_solve']))
            field_times.append(float(result['timing_readout']))
        rows.append({'case': case.meta['id'], 'vertices': len(case.points), 'triangles': len(case.triangles),
                     'drives_per_batch': len(case.drive_H), 'batches': len(durations),
                     'setup_seconds': model.setup_seconds, 'first_readout_seconds': float(first['timing_readout']),
                     'repeat_batch_median_seconds': float(np.median(durations)),
                     'repeat_batch_max_seconds': float(np.max(durations)),
                     'repeat_solve_median_seconds': float(np.median(solve_times)),
                     'repeat_readout_median_seconds': float(np.median(field_times))})
        target = output / 'raw' / 'reuse'
        target.mkdir(exist_ok=True, parents=True)
        np.savez_compressed(target / path.name, **result, batch_seconds=np.array(durations))
    write_csv(output / 'reuse.csv', rows)


def diagnostics(inputs, output):
    rows = []
    original = load_case(inputs / 'dev_ring.npz')
    case = changed_case(original, 'vortex_ring')
    _, _, current_x, current_y = triangle_geometry(case)
    eligible = np.flatnonzero(np.all(case.region[case.triangles] == 0, axis=1))
    face = eligible[len(eligible) // 2]
    weights = np.array([0.2, 0.3, 0.5])
    for drive, strength in enumerate((1., 1., -0.5, 0.35)):
        case.data['vortex_load'][drive, case.triangles[face]] += strength * PHI0 / MU0 * weights
    position = weights @ case.points[case.triangles[face], :2]
    case.meta['vortices'] = [{'drive': drive, 'film': 0, 'position': position.tolist(), 'nPhi0': strength}
                            for drive, strength in enumerate((1., 1., -0.5, 0.35))]
    save_case(case, output / 'experiments' / 'inputs' / 'vortex_ring.npz')
    actual = solve(case)
    reference = solve(case, 'reference')
    for configuration, result in [('qualified', actual), ('reference', reference)]:
        np.savez_compressed(output / 'raw' / configuration / 'vortex_ring.npz', **result)
    rounded = changed_case(case, 'rounded_vortex_ring')
    rounded.data['vortex_load'][:] = 0
    nearest = np.argmin(np.linalg.norm(case.points[:, :2] - position, axis=1))
    for drive, strength in enumerate((1., 1., -0.5, 0.35)):
        rounded.data['vortex_load'][drive, nearest] = strength * PHI0 / MU0
    rounded_result = solve(rounded)
    save_case(rounded, output / 'experiments' / 'inputs' / 'rounded_vortex_ring.npz')
    np.savez_compressed(output / 'raw' / 'qualified' / 'rounded_vortex_ring.npz', **rounded_result)
    for key in ('stream', 'current', 'field'):
        rows.append({'experiment': 'source_rounding', 'metric': key + '_relative_difference',
                     'value': relative_error(rounded_result[key], actual[key])})
    for key in ('stream', 'current', 'field', 'inductance', 'hole_current'):
        rows.append({'experiment': 'integrated_vortex', 'metric': key + '_relative_error', 'value': relative_error(actual[key], reference[key])})
    rows.append({'experiment': 'integrated_vortex', 'metric': 'max_equilibrium_residual', 'value': float(np.max(abs(actual['equilibrium_residual'])))})
    permuted = changed_case(case, 'permuted_vortex_ring')
    generator = np.random.default_rng(12345)
    permutation = generator.permutation(len(case.points))
    inverse = np.argsort(permutation)
    face_permutation = generator.permutation(len(case.triangles))
    for key in ('points', 'region', 'point_film'):
        permuted.data[key] = case.data[key][permutation]
    for key in ('drive_H', 'vortex_load'):
        permuted.data[key] = case.data[key][:, permutation]
    for key in ('lambdas', 'triangle_film'):
        permuted.data[key] = case.data[key][face_permutation]
    permuted.data['triangles'] = inverse[np.roll(case.triangles[face_permutation], 1, axis=1)]
    reordered = solve(permuted)
    for key, reordered_value in [('stream', reordered['stream'][:, inverse]),
                                  ('current', reordered['current'][:, np.argsort(face_permutation)]),
                                  ('field', reordered['field'])]:
        rows.append({'experiment': 'permutation_and_cyclic_faces', 'metric': key + '_relative_error', 'value': relative_error(reordered_value, actual[key])})
    target = output / 'raw' / 'diagnostics'
    target.mkdir(exist_ok=True, parents=True)
    np.savez_compressed(target / 'permuted_vortex_ring.npz', **reordered)
    save_case(permuted, output / 'experiments' / 'inputs' / 'permuted_vortex_ring.npz')
    model = SheetModel(original)
    base = model.solve()
    vertices, _, _, _ = triangle_geometry(original)
    face = np.flatnonzero(original.lambdas > 0)[10]
    center = vertices[face].mean(axis=0)
    observers = center + np.array([[0., 0., 1e-9], [0., 0., -1e-9], [0., 0., 0.]])
    fields = evaluate_field(observers, vertices, base['current'])
    expected = MU0 * np.column_stack((base['current'][:, face, 1], -base['current'][:, face, 0], np.zeros(len(base['current']))))
    rows.append({'experiment': 'full_mesh_sheet_jump', 'metric': 'relative_error', 'value': relative_error(fields[:, 0] - fields[:, 1], expected)})
    rows.append({'experiment': 'full_mesh_sheet_pv', 'metric': 'relative_error', 'value': relative_error(fields[:, 2], (fields[:, 0] + fields[:, 1]) / 2)})
    np.savez_compressed(target / 'sheet_jump.npz', observers=observers, field=fields, expected_jump=expected)
    case = changed_case(original, 'kinetic_limit')
    for coefficient in (15., 1500.):
        case.data['lambdas'][original.lambdas > 0] = coefficient
        case.meta['films'][0]['nominal_lambda'] = coefficient
        result = solve(case)
        outer = np.asarray(case.meta['films'][0]['outer'])
        inner = np.asarray(case.meta['films'][0]['holes'][0])
        outer_radius = np.mean(np.linalg.norm(outer, axis=1))
        inner_radius = np.mean(np.linalg.norm(inner, axis=1))
        analytic = 2 * np.pi * MU0 * coefficient / np.log(outer_radius / inner_radius)
        rows.append({'experiment': f'kinetic_limit_lambda_{coefficient:g}', 'metric': 'continuum_relative_difference', 'value': abs(result['inductance'][0, 0] / analytic - 1)})
        np.savez_compressed(target / f'kinetic_limit_{coefficient:g}.npz', **result, continuum_inductance=analytic)
        save_case(case, output / 'experiments' / 'inputs' / f'kinetic_limit_{coefficient:g}.npz')
    write_csv(output / 'diagnostics.csv', rows)


def larger_case(inputs, output):
    original = load_case(inputs / 'dev_ring.npz')
    case = changed_case(original, 'double_ring_330')
    shift = np.array([7., 0., 0.])
    case.data['points'] = np.concatenate((original.points, original.points + shift))
    case.data['triangles'] = np.concatenate((original.triangles, original.triangles + len(original.points)))
    case.data['region'] = np.concatenate((original.region, np.where(original.region > 0, original.region + 1, original.region)))
    case.data['point_film'] = np.concatenate((original.point_film, original.point_film + 1))
    case.data['triangle_film'] = np.concatenate((original.triangle_film, original.triangle_film + 1))
    case.data['lambdas'] = np.tile(original.lambdas, 2)
    for key in ('drive_H', 'vortex_load', 'prescribed_current', 'target_fluxoid'):
        case.data[key] = np.tile(original.data[key], (1, 2))
    case.data['observers'] = np.concatenate((original.observers, original.observers + shift))
    spec = copy.deepcopy(case.meta['films'][0])
    spec['name'] += '_second'
    spec['outer'] = (np.array(spec['outer']) + shift[:2]).tolist()
    spec['holes'] = [(np.array(contour) + shift[:2]).tolist() for contour in spec['holes']]
    spec['hole_ids'] = [1]
    case.meta['films'].append(spec)
    case_path = output / 'experiments' / 'inputs' / 'double_ring_330.npz'
    save_case(case, case_path)
    raw_path = output / 'raw' / 'qualified' / case_path.name
    start = time.perf_counter()
    subprocess.run([sys.executable, '-m', 'qualification.cli', 'case', str(case_path), str(raw_path)], check=True)
    metrics = json.loads(raw_path.with_suffix('.metrics.json').read_text())
    metrics['process_wall_seconds'] = time.perf_counter() - start
    raw_path.with_suffix('.metrics.json').write_text(json.dumps(metrics, indent=2))
    write_csv(output / 'extended_scaling.csv', [metrics])


def energy_readout(inputs, output):
    rows = []
    target = output / 'raw' / 'energy_checks'
    target.mkdir(exist_ok=True, parents=True)
    for filename in ('dev_ring.npz', 'dev_stack.npz'):
        case = load_case(inputs / filename)
        with np.load(output / 'raw' / 'qualified' / filename) as archive:
            result = dict(archive)
        vertices, areas, _, _ = triangle_geometry(case)
        reduced = np.concatenate((result['stream'][0, case.region == 0], result['hole_current'][0]))
        kinetic = MU0 / 2 * np.sum(areas[:, None] * case.lambdas[:, None] * result['current'][0] ** 2)
        expected = MU0 / 2 * reduced @ result['reduced_matrix'] @ reduced - kinetic
        hole_faces = np.all(case.region[case.triangles] > 0, axis=1) & np.all(
            case.region[case.triangles] == case.region[case.triangles[:, :1]], axis=1)
        for order in (6, 12, 24):
            start = time.perf_counter()
            rule, weights = quadrature(order)
            positions = np.einsum('qv,tvk->tqk', rule, vertices).reshape(-1, 3)
            stream_values = np.einsum('qv,tv->tq', rule, result['stream'][0, case.triangles])
            integrated = np.empty(len(positions))
            for start_index in range(0, len(positions), 128):
                field = evaluate_field(positions[start_index:start_index + 128], vertices, result['current'][:1])
                integrated[start_index:start_index + 128] = field[0, :, 2]
            triangle_energy = areas / 2 * np.sum(weights * stream_values * integrated.reshape(len(vertices), -1), axis=1)
            actual = triangle_energy.sum()
            no_holes = triangle_energy[~hole_faces].sum()
            rows.append({'case': case.meta['id'], 'quadrature_order': order,
                         'matrix_magnetic_energy': float(expected), 'readout_magnetic_energy': float(actual),
                         'relative_difference': float(abs(actual / expected - 1)),
                         'omit_hole_relative_difference': float(abs(no_holes / expected - 1)),
                         'seconds': time.perf_counter() - start})
            np.savez_compressed(target / f'{case.meta["id"]}_order_{order}.npz',
                                triangle_energy=triangle_energy, matrix_magnetic_energy=expected,
                                hole_faces=hole_faces, quadrature_order=order)
            print('energy', case.meta['id'], order, rows[-1]['relative_difference'], flush=True)
    write_csv(output / 'energy_consistency.csv', rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inputs', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--experiment', choices=['all', 'stress', 'reuse', 'diagnostics', 'larger', 'energy'], default='all')
    args = parser.parse_args()
    for name, function in [('stress', stress), ('reuse', reuse), ('diagnostics', diagnostics), ('larger', larger_case), ('energy', energy_readout)]:
        if args.experiment in ('all', name):
            function(args.inputs, args.output)


if __name__ == '__main__':
    main()
