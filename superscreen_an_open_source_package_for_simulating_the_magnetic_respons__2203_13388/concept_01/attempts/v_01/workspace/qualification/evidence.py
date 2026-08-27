import json
from pathlib import Path

import numpy as np

from .model import MU0, applied_load, load_case, triangle_geometry


def relative_error(actual, expected):
    return float(np.linalg.norm(actual - expected) / max(np.linalg.norm(expected), 1e-14))


def augment(paths, directory, rows):
    directory = Path(directory)
    lookup = {}
    for path in paths:
        case = load_case(path)
        with np.load(directory / 'raw' / 'reference' / path.name) as archive:
            reference = dict(archive)
        _, areas, current_x, current_y = triangle_geometry(case)
        lift = np.min(abs(case.observers[:, 2, None] - np.unique(case.points[:, 2])), axis=1)
        scale = np.median(np.sqrt(areas))
        near, far = lift < 0.1 * scale, lift > scale
        free = np.flatnonzero(case.region == 0)
        holes = case.prescribed_current.shape[1]
        reduction = np.zeros((len(case.points), len(free) + holes))
        reduction[free, np.arange(len(free))] = 1
        for hole in range(holes):
            reduction[case.region == hole + 1, len(free) + hole] = 1
        source = (case.vortex_load - applied_load(case)) @ reduction
        for configuration in sorted({row['configuration'] for row in rows}):
            with np.load(directory / 'raw' / configuration / path.name) as archive:
                actual = dict(archive)
            reduced = np.column_stack((actual['stream'][:, free], actual['hole_current']))
            generalized = MU0 * (reduced @ reference['reduced_matrix'][len(free):].T - source[:, len(free):])
            residual = reduced @ reference['reduced_matrix'].T - source
            for drive in range(len(case.drive_H)):
                values = {}
                for key in ('stream', 'current', 'field', 'hole_current', 'fluxoid'):
                    values[f'{key}_relative_error'] = relative_error(actual[key][drive], reference[key][drive])
                values['inductance_relative_error'] = relative_error(actual['inductance'], reference['inductance'])
                values['near_field_relative_error'] = relative_error(actual['field'][drive, near], reference['field'][drive, near])
                values['far_field_relative_error'] = relative_error(actual['field'][drive, far], reference['field'][drive, far])
                for key in ('current', 'field'):
                    difference = np.linalg.norm(actual[key][drive] - reference[key][drive], axis=-1)
                    rms = np.sqrt(np.mean(np.sum(reference[key][drive] ** 2, axis=-1)))
                    values[f'{key}_max_scaled_error'] = float(np.max(difference) / max(rms, 1e-14))
                values['physical_residual_relative'] = float(np.linalg.norm(residual[drive, :len(free)]) / max(
                    np.linalg.norm((reduced @ reference['reduced_matrix'].T)[drive]), np.linalg.norm(source[drive]), 1e-14))
                values['generalized_fluxoid_mismatch'] = float(np.linalg.norm(actual['fluxoid'][drive] - generalized[drive]))
                unknown = ~np.isfinite(case.prescribed_current[drive])
                values['physical_fluxoid_constraint_error'] = float(np.linalg.norm(generalized[drive, unknown] - case.target_fluxoid[drive, unknown]))
                values['bare_flux_constraint_error'] = float(np.linalg.norm(actual['bare_flux'][drive, unknown] - case.target_fluxoid[drive, unknown])) if 'bare_flux' in actual else float('nan')
                values['minimum_symmetric_inductance_eigenvalue'] = float(np.linalg.eigvalsh((actual['inductance'] + actual['inductance'].T) / 2).min()) if holes else 0.0
                derived = np.stack((current_x @ actual['stream'][drive], current_y @ actual['stream'][drive]), axis=-1)
                values['current_stream_inconsistency'] = float(np.linalg.norm(actual['current'][drive] - derived))
                values['comparison_configuration'] = 'reference'
                lookup[(case.meta['id'], configuration, drive)] = values
    return [{**row, **lookup[(row['case'], row['configuration'], row['drive'])]} for row in rows]


def claims(directory, rows):
    comparisons = [
        ('reciprocity', 'The two-hole reciprocity defect decreases with the energy formulation.',
         'reciprocity_error', 'dev_holes', 'qualified', 'legacy', 0),
        ('readout', 'Exact triangle readout reduces legacy near-field error without changing its state.',
         'near_field_relative_error', 'dev_ring', 'legacy_exact_readout', 'legacy', 0),
        ('material', 'Keeping elementwise Lambda improves the patterned-film current response.',
         'current_relative_error', 'dev_pattern', 'qualified', 'smoothed_material', 2),
        ('coupling', 'Including magnetic cross-film blocks improves the stacked-device field response.',
         'field_relative_error', 'dev_stack', 'qualified', 'no_coupling', 2),
        ('quadrature', 'Higher-order integration reduces the current difference from the order-40 calculation.',
         'current_relative_error', 'dev_pattern', 'qualified', 'coarse', 0),
        ('state_control', 'Fluxoid control meets the physical constraint more accurately than bare-flux control.',
         'physical_fluxoid_constraint_error', 'dev_ring', 'qualified', 'bare_flux_control', 1),
    ]
    available = {(row['case'], row['configuration'], row['drive']) for row in rows}
    output = []
    for identifier, text, metric, case, left, right, drive in comparisons:
        if (case, left, drive) in available and (case, right, drive) in available:
            output.append({'id': identifier, 'text': text, 'table': 'ablation.csv', 'metric': metric,
                           'left': {'case': case, 'configuration': left, 'drive': drive},
                           'right': {'case': case, 'configuration': right, 'drive': drive}, 'relation': 'lt'})
    (Path(directory) / 'claims.json').write_text(json.dumps({'claims': output}, indent=2))
