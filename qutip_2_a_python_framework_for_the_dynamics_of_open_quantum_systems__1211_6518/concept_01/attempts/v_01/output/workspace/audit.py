import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from oqs.diagnostics import diagnostics, distance


def load_raw(directory):
    with np.load(directory / 'result.npz', allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def main():
    root = Path(sys.argv[1])
    count = 0
    tables = {}
    for filename in ['results.csv', 'ablation.csv', 'scaling.csv', 'controlled.csv']:
        rows = list(csv.DictReader((root / filename).open()))
        tables[filename] = {row['row_id']: row for row in rows}
        for row in rows:
            directory = root / 'runs' / row['row_id']
            if filename == 'scaling.csv' and row['study'] == 'supplied_cutoff':
                directory = directory / 'production'
            raw = load_raw(directory)
            metrics = json.loads((directory / 'metrics.json').read_text())
            for key, value in diagnostics(raw).items():
                assert np.isclose(float(row[key]), value, rtol=2e-12, atol=2e-12), (filename, row['row_id'], key)
            options = json.loads((directory / 'options.json').read_text())
            digest = hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()
            assert row['config_digest'] == metrics['config_digest'] == digest
            with np.load(directory / 'input.npz', allow_pickle=False) as inputs:
                expected = np.asarray([[np.trace(operator @ state) for operator in inputs['e_ops']] for state in raw['states']])
                assert np.allclose(raw['expectations'], expected, atol=1e-12, rtol=1e-12)
                assert np.array_equal(raw['times'], inputs['times'])
                assert np.linalg.norm(raw['states'][0] - inputs['rho0']) < 1e-10
                if 'channel' in raw:
                    dimension = len(inputs['rho0'])
                    predicted = raw['channel'] @ inputs['rho0'].ravel(order='F')
                    assert np.linalg.norm(predicted - raw['states'][-1].ravel(order='F')) < 1e-8
                    for row_index in range(dimension):
                        for column_index in range(dimension):
                            block = raw['choi'][row_index * dimension:(row_index + 1) * dimension,
                                                column_index * dimension:(column_index + 1) * dimension]
                            expected = raw['channel'][:, row_index + dimension * column_index].reshape(dimension, dimension, order='F')
                            assert np.allclose(block, expected, atol=1e-13, rtol=1e-13)
            if 'distance_to_refined' in row:
                refined = load_raw(root / 'runs' / row['case'] / 'refined')
                assert np.isclose(float(row['distance_to_refined']), distance(raw, refined), atol=1e-13, rtol=1e-10)
            elif filename == 'controlled.csv':
                comparator = load_raw(root / 'runs' / row['comparator'])
                assert np.isclose(float(row['distance_to_comparator']), distance(raw, comparator), atol=1e-13, rtol=1e-10)
            elif filename == 'scaling.csv':
                if row['study'] == 'supplied_cutoff':
                    original_id = row['case'].rsplit('_size_', 1)[0]
                    comparator = load_raw(root / 'runs' / original_id / 'production')
                    dimension = raw['states'].shape[-1]
                    embedded = np.zeros_like(comparator['states'])
                    embedded[:, :dimension, :dimension] = raw['states']
                    actual = float(np.max(np.linalg.norm(embedded - comparator['states'], axis=(1, 2))))
                else:
                    comparator = load_raw(root / 'runs' / row['case'] / 'structured')
                    if row['implementation'] == 'rotated_structured':
                        from oqs.studies import random_basis
                        basis = random_basis(raw['states'].shape[-1])
                        raw = dict(raw, states=basis.conj().T @ raw['states'] @ basis)
                    actual = distance(raw, comparator)
                assert np.isclose(float(row['distance_to_comparator']), actual, atol=1e-13, rtol=1e-9)
            count += 1
    claims = json.loads((root / 'claims.json').read_text())
    for claim in claims:
        table = tables[claim['table']]
        left = float(table[claim['left']][claim['metric']])
        right = float(table[claim['right']][claim['metric']])
        assert (left <= right) if claim['relation'] == 'le' else (left > right), claim['id']
    sources = json.loads((root / 'figures' / 'sources.json').read_text())
    for figure, source in sources.items():
        assert (root / 'figures' / figure).is_file()
        assert all(row in tables[source['table']] for row in source['rows'])
    result = {'rows_recomputed': count, 'claims_checked': len(claims), 'successful': True}
    (root / 'audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
