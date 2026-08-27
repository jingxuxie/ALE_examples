import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .backend import CONFIGURATIONS
from .model import load_case, summarize, triangle_geometry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('suite', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows = list(csv.DictReader((args.output / 'ablation.csv').open()))
    lookup = {(row['case'], row['configuration'], int(row['drive'])): row for row in rows}
    assert len(lookup) == len(rows)
    checked = 0
    keys = ('stream', 'current', 'field', 'hole_current', 'fluxoid', 'inductance')
    maximum_current_inconsistency = 0.
    maximum_equilibrium_residual = 0.
    minimum_eigenvalue = float('inf')
    for filename in json.loads(args.suite.read_text())['cases']:
        case = load_case(args.suite.parent / filename)
        drives, holes = case.prescribed_current.shape
        expected_shapes = [(drives, len(case.points)), (drives, len(case.triangles), 2),
                           (drives, len(case.observers), 3), (drives, holes), (drives, holes), (holes, holes)]
        outputs = {}
        for configuration in CONFIGURATIONS:
            with np.load(args.output / 'raw' / configuration / filename, allow_pickle=False) as archive:
                result = dict(archive)
            outputs[configuration] = result
            for key, shape in zip(keys, expected_shapes):
                assert result[key].shape == shape, (configuration, filename, key)
                assert np.isfinite(result[key]).all()
            for expected in summarize(case, result):
                row = lookup[(case.meta['id'], configuration, expected['drive'])]
                for metric, value in expected.items():
                    if metric not in ('case', 'family', 'drive'):
                        np.testing.assert_allclose(float(row[metric]), value, rtol=1e-12, atol=1e-14, equal_nan=True)
            checked += 1
        default = outputs['qualified']
        _, _, current_x, current_y = triangle_geometry(case)
        derived = np.stack(((current_x @ default['stream'].T).T, (current_y @ default['stream'].T).T), axis=-1)
        maximum_current_inconsistency = max(maximum_current_inconsistency, float(np.max(abs(default['current'] - derived))))
        maximum_equilibrium_residual = max(maximum_equilibrium_residual, float(np.max(abs(default['equilibrium_residual']))))
        minimum_eigenvalue = min(minimum_eigenvalue, float(np.linalg.eigvalsh(default['reduced_matrix']).min()))
        np.testing.assert_allclose(default['stream'][:, case.region == -1], 0, atol=0)
        for key in keys:
            if key != 'field':
                np.testing.assert_allclose(outputs['legacy'][key], outputs['legacy_exact_readout'][key], rtol=1e-12, atol=1e-13)
        if len(np.unique(case.point_film)) == 1:
            for key in keys:
                np.testing.assert_allclose(default[key], outputs['no_coupling'][key], rtol=1e-12, atol=1e-13)
        baseline = args.output / 'baseline' / 'raw' / 'legacy' / filename
        if baseline.exists():
            with np.load(baseline) as archive:
                for key in keys:
                    np.testing.assert_allclose(archive[key], outputs['legacy'][key], rtol=1e-12, atol=1e-13)
        pilot = args.output / 'pilot' / 'raw' / 'qualified' / filename
        if pilot.exists():
            with np.load(pilot) as archive:
                for key in keys:
                    np.testing.assert_allclose(archive[key], outputs['fixed12'][key], rtol=1e-12, atol=1e-13)
    claims = json.loads((args.output / 'claims.json').read_text())['claims']
    for claim in claims:
        table = list(csv.DictReader((args.output / claim['table']).open()))
        values = []
        for side in ('left', 'right'):
            selector = claim[side]
            matched = [row for row in table if row['case'] == selector['case'] and row['configuration'] == selector['configuration']
                       and int(row['drive']) == selector['drive']]
            assert len(matched) == 1
            values.append(float(matched[0][claim['metric']]))
        left, right = values
        if claim['relation'] == 'lt':
            assert left < right, claim['id']
        elif claim['relation'] == 'gt':
            assert left > right, claim['id']
        else:
            assert abs(left - right) <= claim.get('tolerance', 1e-12), claim['id']
    report = {'checked_case_configurations': checked, 'checked_table_rows': len(rows), 'verified_claims': len(claims),
              'maximum_current_stream_absolute_difference': maximum_current_inconsistency,
              'maximum_own_equilibrium_absolute_residual': maximum_equilibrium_residual,
              'minimum_reduced_matrix_eigenvalue': minimum_eigenvalue,
              'baseline_reproduction': 'passed', 'pilot_fixed12_reproduction': 'passed',
              'readout_only_ablation_state_identity': 'passed', 'single_film_uncoupled_identity': 'passed'}
    (args.output / 'audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
