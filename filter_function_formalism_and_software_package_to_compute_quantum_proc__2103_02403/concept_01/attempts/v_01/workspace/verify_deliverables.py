import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from pipeline.physics import load_case, observables


ROOT = Path(__file__).resolve().parent.parent


def read_table(name):
    with (ROOT / name).open() as stream:
        return {row['row_id']: row for row in csv.DictReader(stream)}


def main():
    checks = []
    for name, expected in [('results.csv', 14), ('ablation.csv', 21)]:
        rows = read_table(name)
        assert len(rows) == expected
        for row in rows.values():
            case, arrays = load_case(ROOT / 'input' / 'cases' / (row['case_id'] + '.json'))
            destination = ROOT / row['artifact']
            process = dict(np.load(destination / 'process.npz'))
            metrics = json.loads((destination / 'metrics.json').read_text())
            size = arrays['H'].shape[-1] ** 2
            assert process['channel'].shape == (size, size)
            assert process['k2'].shape == (size, size)
            assert np.isfinite(process['channel']).all() and np.isfinite(process['k2']).all()
            recomputed = observables(process['channel'], arrays)
            recomputed.update(k2_norm=float(np.linalg.norm(process['k2'])))
            for key, value in recomputed.items():
                np.testing.assert_allclose(float(row[key]), value, atol=5e-12, rtol=2e-10)
                np.testing.assert_allclose(metrics[key], value, atol=5e-12, rtol=2e-10)
            for key in ['seconds', 'peak_rss_mb']:
                assert float(row[key]) == metrics[key]
            assert metrics['case_id'] == row['case_id'] and metrics['mode'] == row['mode']
            checks.append(dict(check='artifact_and_metrics', table=name, row_id=row['row_id'], passed=True))
    for claim in json.loads((ROOT / 'claims.json').read_text()):
        table = read_table(claim['table'])
        values = [float(table[row][claim['metric']]) for row in claim['rows']]
        operation = claim['operation']
        value = values[0] if operation == 'value' else (
            values[0] - values[1] if operation == 'difference' else values[0] / values[1])
        np.testing.assert_allclose(claim['value'], value, atol=1e-14, rtol=1e-12)
        checks.append(dict(check='claim', claim_id=claim['claim_id'], passed=True))
    for filename, panels in json.loads((ROOT / 'figures' / 'sources.json').read_text()).items():
        assert (ROOT / 'figures' / filename).stat().st_size > 10000
        for sources in panels.values():
            for source in sources:
                table = read_table(source['table'])
                assert all(row in table for row in source['rows'])
        checks.append(dict(check='figure_sources', artifact='figures/' + filename, passed=True))
    for path, checksum in json.loads((ROOT / 'manifest.json').read_text()).items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == checksum
    checks.append(dict(check='input_and_predictor_manifest', passed=True))
    tests = json.loads((ROOT / 'validation' / 'tests.json').read_text())
    assert all(test['passed'] for test in tests)
    launches = json.loads((ROOT / 'launches.json').read_text())
    assert len(launches) == 28 and all(launch['returncode'] == 0 for launch in launches)
    checks.append(dict(check='tests_and_complete_launches', passed=True))
    (ROOT / 'validation' / 'deliverables.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(f'Validated {len(checks)} artifact, claim, provenance, source, and execution checks.')


if __name__ == '__main__':
    main()
