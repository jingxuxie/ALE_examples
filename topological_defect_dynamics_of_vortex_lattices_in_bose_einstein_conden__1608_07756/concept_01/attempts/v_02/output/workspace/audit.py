import csv
import json
import sys
from pathlib import Path

import numpy as np


def sample(image, positions, axis_x, axis_y):
    columns = np.clip(np.rint((positions[:, 0] - axis_x[0]) / (axis_x[1] - axis_x[0])).astype(int), 0, len(axis_x) - 1)
    rows = np.clip(np.rint((positions[:, 1] - axis_y[0]) / (axis_y[1] - axis_y[0])).astype(int), 0, len(axis_y) - 1)
    return image[rows, columns]


def audit(manifest_path, run_path, output_path):
    manifest_path, run_path = Path(manifest_path), Path(run_path)
    records = []
    tables = {(row['case'], int(row['frame'])): row for row in csv.DictReader((run_path / 'results.csv').open())}
    for case in json.loads(manifest_path.read_text())['cases']:
        with np.load(manifest_path.parent / case['asset']) as asset:
            axis_x, axis_y = asset['x'], asset['y']
            dx, dy = axis_x[1] - axis_x[0], axis_y[1] - axis_y[0]
            grid_x, grid_y = np.meshgrid(axis_x, axis_y)
            initial = asset['psi']
            potential, roi, bulk = asset['potential'], asset['roi'], asset['bulk']
        wave_x = 2 * np.pi * np.fft.fftfreq(len(axis_x), dx)[None, :]
        wave_y = 2 * np.pi * np.fft.fftfreq(len(axis_y), dy)[:, None]
        wave2 = wave_x ** 2 + wave_y ** 2
        with np.load(run_path / (case['id'] + '.npz')) as saved:
            frames, times = saved['psi'], saved['times']
        np.testing.assert_array_equal(times, case['times'])
        assert frames.dtype == np.complex128
        assert frames.shape == (len(times), len(axis_y), len(axis_x))
        assert np.isfinite(frames).all()
        expected = initial.copy()
        for operation in case.get('imprints', []):
            expected *= np.exp(1j * operation['charge'] * np.arctan2(grid_y - operation['y'], grid_x - operation['x']))
        np.testing.assert_allclose(frames[0], expected, atol=1e-14, rtol=1e-13)
        diagnostics = json.loads((run_path / (case['id'] + '.json')).read_text())
        for frame_index, (time, psi, diagnostics_frame) in enumerate(zip(times, frames, diagnostics)):
            density = abs(psi) ** 2
            transformed = np.fft.fft2(psi)
            derivative_x = np.fft.ifft2(1j * wave_x * transformed)
            derivative_y = np.fft.ifft2(1j * wave_y * transformed)
            kinetic = 0.5 * (abs(derivative_x) ** 2 + abs(derivative_y) ** 2)
            angular = np.real(-1j * psi.conj() * (grid_x * derivative_y - grid_y * derivative_x))
            trap = potential.copy()
            drive = case.get('drive')
            if drive:
                phase = np.sin(drive['frequency'] * time)
                distance2 = ((grid_x - drive['center'][0] - drive['travel'] * phase) ** 2
                             + (grid_y - drive['center'][1]) ** 2)
                trap += drive['amplitude'] * phase ** 2 * np.exp(-distance2 / (2 * drive['width'] ** 2))
            energy = dx * dy * np.sum(kinetic + trap * density + 0.5 * case['g'] * density ** 2 - case['omega'] * angular)
            amplitude = np.sqrt(density)
            weighted = []
            for derivative in (derivative_x, derivative_y):
                component = np.zeros_like(density)
                occupied = density > 1e-12 * density.max()
                component[occupied] = np.imag(psi.conj()[occupied] * derivative[occupied]) / amplitude[occupied]
                weighted.append(component)
            transformed_x, transformed_y = (np.fft.fft2(component) for component in weighted)
            wave2_safe = np.where(wave2 == 0, 1, wave2)
            dot = (wave_x * transformed_x + wave_y * transformed_y) / wave2_safe
            longitudinal_x, longitudinal_y = wave_x * dot, wave_y * dot
            transverse_x, transverse_y = transformed_x - longitudinal_x, transformed_y - longitudinal_y
            factor = dx * dy / (2 * psi.size)
            compressible = factor * (abs(longitudinal_x) ** 2 + abs(longitudinal_y) ** 2)
            incompressible = factor * (abs(transverse_x) ** 2 + abs(transverse_y) ** 2)
            root_fft = np.fft.fft2(amplitude)
            quantum = dx * dy / 2 * np.sum(abs(np.fft.ifft2(1j * wave_x * root_fft)) ** 2
                                          + abs(np.fft.ifft2(1j * wave_y * root_fft)) ** 2)
            physics = diagnostics_frame['physics']
            row = tables[case['id'], frame_index]
            errors = [abs(physics['norm'] - dx * dy * density.sum()), abs(physics['energy'] - energy),
                      abs(physics['r2'] - dx * dy * np.sum((grid_x ** 2 + grid_y ** 2) * density)),
                      abs(physics['Ec'] - compressible.sum()), abs(physics['Ei'] - incompressible.sum()),
                      abs(physics['Eq'] - quantum)]
            magnitude = np.sqrt(wave2)
            for bin_index, (lower, upper) in enumerate(zip(case['spectrum_edges'][:-1], case['spectrum_edges'][1:])):
                shell = (magnitude >= lower) & (magnitude < upper)
                errors.extend([abs(physics['Ec_bins'][bin_index] - compressible[shell].sum()),
                               abs(physics['Ei_bins'][bin_index] - incompressible[shell].sum())])
            for name in ('norm', 'energy', 'r2', 'Ec', 'Ei', 'Eq'):
                errors.append(abs(float(row[name]) - physics[name]))
            cores = np.asarray(diagnostics_frame['cores']).reshape((-1, 3))
            selected = sample(bulk, cores[:, :2], axis_x, axis_y)
            assert int(row['nplus']) == np.sum(selected & (cores[:, 2] > 0))
            assert int(row['nminus']) == np.sum(selected & (cores[:, 2] < 0))
            assert np.all(sample(roi, cores[:, :2], axis_x, axis_y) > 0)
            positions = cores[cores[:, 2] > 0, :2]
            topology = diagnostics_frame['topology']
            bulk_positive = sample(bulk, positions, axis_x, axis_y)
            neighbors = [set() for position in positions]
            for first, second in topology['edges']:
                label = sample(roi, positions[[first]], axis_x, axis_y)[0]
                count = max(2, 1 + int(np.ceil(np.linalg.norm(positions[second] - positions[first]) / (min(dx, dy) / 2))))
                segment = np.linspace(positions[first], positions[second], count)
                assert np.all(sample(roi, segment, axis_x, axis_y) == label)
                neighbors[first].add(second)
                neighbors[second].add(first)
            local = np.zeros(len(positions), dtype=complex)
            for index, adjacent in enumerate(neighbors):
                if adjacent:
                    vectors = positions[list(adjacent)] - positions[index]
                    unit = (vectors[:, 0] + 1j * vectors[:, 1]) / np.linalg.norm(vectors, axis=1)
                    local[index] = np.mean(unit ** 6)
            selected_positions = positions[bulk_positive]
            selected_local = local[bulk_positive]
            first_indices, second_indices = np.triu_indices(len(selected_positions), 1)
            distances = np.linalg.norm(selected_positions[first_indices] - selected_positions[second_indices], axis=1)
            products = np.real(selected_local[first_indices] * np.conj(selected_local[second_indices]))
            for bin_index, (lower, upper) in enumerate(zip(case['correlation_edges'][:-1], case['correlation_edges'][1:])):
                contained = (distances >= lower) & (distances < upper)
                assert int(contained.sum()) == topology['pair_counts'][bin_index]
                expected_correlation = float(products[contained].mean()) if contained.any() else 0.0
                errors.append(abs(expected_correlation - topology['correlations'][bin_index]))
            degree = np.array([len(adjacent) for adjacent in neighbors], dtype=int)
            np.testing.assert_array_equal(np.bincount(degree[bulk_positive], minlength=13)[:13], topology['counts'])
            defect_positions = positions[bulk_positive & (degree != 6)]
            center = np.asarray(case.get('intervention_center', [0, 0]))
            radius = np.sqrt(np.mean(np.sum((defect_positions - center) ** 2, axis=1))) if len(defect_positions) else 0
            errors.append(abs(topology['defect_radius'] - radius))
            assert max(errors) < 1e-9, (case['id'], frame_index, max(errors))
            velocity_energy = dx * dy / 2 * sum(np.sum(component ** 2) for component in weighted)
            records.append(dict(case=case['id'], frame=frame_index, time=float(time),
                                norm_direct=float(dx * dy * density.sum()), energy_direct=float(energy),
                                max_measurement_residual=float(max(errors)),
                                helmholtz_parseval_residual=float(abs(physics['Ec'] + physics['Ei'] - velocity_energy)),
                                kinetic_partition_residual=float(dx * dy * kinetic.sum() - physics['Ec'] - physics['Ei'] - physics['Eq']),
                                imprint_density_relative=float(np.linalg.norm(abs(frames[0]) ** 2 - abs(initial) ** 2) / np.linalg.norm(abs(initial) ** 2))))
    with Path(output_path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f'Audited {len(records)} frames: maximum measurement residual {max(row["max_measurement_residual"] for row in records):.3g}')
    return records


if __name__ == '__main__':
    audit(*sys.argv[1:])
