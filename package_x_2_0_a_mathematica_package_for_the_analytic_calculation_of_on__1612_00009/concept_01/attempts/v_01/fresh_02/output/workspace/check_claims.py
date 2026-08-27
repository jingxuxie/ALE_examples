import csv
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    claims = json.loads((root / 'claims.json').read_text())['claims']
    comparisons = 0
    for claim in claims:
        rows = list(csv.DictReader((root / claim['table']).open()))
        selected = claim['case_ids']
        indexed = {}
        for row in rows:
            if selected and row['case_id'] not in selected:
                continue
            key = (row['case_id'], row.get('integral_id', ''), row.get('order', ''))
            indexed.setdefault(row['profile'], {})[key] = float(row[claim['metric']])
        left, right = indexed[claim['left_profile']], indexed[claim['right_profile']]
        if set(left) != set(right):
            raise AssertionError((claim['id'], 'unmatched rows'))
        for key, value in left.items():
            valid = value <= right[key] if claim['relation'] == '<=' else value >= right[key]
            if not valid:
                raise AssertionError((claim['id'], key, value, right[key]))
            comparisons += 1
        print(claim['id'], 'PASS', len(left), 'row comparisons')
    print(len(claims), 'claims;', comparisons, 'row comparisons passed')


if __name__ == '__main__':
    main()
