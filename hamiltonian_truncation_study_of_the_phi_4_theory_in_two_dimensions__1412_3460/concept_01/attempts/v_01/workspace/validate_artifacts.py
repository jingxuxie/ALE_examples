import csv
import json
import math
import sys
from pathlib import Path


def validate(destination):
    destination = Path(destination)
    records = []
    for filename in ['results.csv', 'ablation.csv']:
        records.extend(csv.DictReader((destination / filename).open()))
    indexed = {row['row_id']: row for row in records}
    assert len(indexed) == len(records), 'Duplicate spectrum row IDs'
    for row in records:
        assert math.isfinite(float(row['energy'])) and math.isfinite(float(row['gap']))
        assert abs(float(row['energy']) - float(row['vacuum_energy']) - float(row['gap'])) < 1e-10
    claims = json.loads((destination / 'claims.json').read_text())['claims']
    for claim in claims:
        rows = [indexed[row_id] for row_id in claim['rows']]
        quantity = claim['quantity']
        expected = abs(float(rows[1][quantity]) - float(rows[0][quantity])) / max(
            abs(float(rows[3][quantity]) - float(rows[2][quantity])), 1e-12)
        assert abs(expected - claim['value']) < 1e-10
        assert claim['conclusion'] == ('improved' if expected < 1 else 'not_improved')
        assert len({(row['case'], row['sector'], row['level']) for row in rows}) == 1
    source = list(csv.DictReader((destination / 'figures' / 'source.csv').open()))
    for point in source:
        row = indexed[point['row_id']]
        assert float(point['x']) == float(row[point['x_quantity']])
        assert float(point['y']) == float(row[point['y_quantity']])
    for filename in ['primary_result.png', 'robustness_or_scaling.png']:
        assert (destination / 'figures' / filename).stat().st_size > 100
    print(f'Validated {len(records)} unique rows, {len(claims)} claims, {len(source)} plotted points.')


if __name__ == '__main__':
    validate(sys.argv[1])
