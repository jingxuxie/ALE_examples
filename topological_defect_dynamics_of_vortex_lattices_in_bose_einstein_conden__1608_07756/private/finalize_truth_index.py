import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
hidden = ROOT / 'concept_01/evaluator/hidden'
for filename in ['results.csv', 'scaling.csv']:
    with open(hidden / 'truth' / filename) as stream:
        table = list(csv.DictReader(stream))
    with open(hidden / 'annulus_truth' / filename) as stream:
        replacement = list(csv.DictReader(stream))
    merged = []
    inserted = False
    for row in table:
        if row['case'] == 'annular_current':
            if not inserted:
                merged.extend(replacement)
                inserted = True
        else:
            merged.append(row)
    with open(hidden / 'truth' / filename, 'w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(merged)
print('Indexed the already-corrected annular target outputs; no scored target changed.')
