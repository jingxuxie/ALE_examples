import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
design_bytes = (ROOT / 'design.json').read_bytes()
design = json.loads(design_bytes)
public = json.loads((ROOT / 'public_validation.json').read_text())
spec = json.loads((ROOT.parent.parent / 'participant/input/spec.json').read_text())
cache = {}
for line in (ROOT / 'observations.jsonl').read_text().splitlines():
    record = json.loads(line)
    cache[(record['bank'], tuple(record['order']), record['scale'], record['seed'])] = record

layouts = {layout['id']: layout for layout in design['layouts']}
assert set(layouts) == {bank['id'] for bank in spec['banks']}
for layout in layouts.values():
    for side in ['high', 'low']:
        assert all(type(index) is int for index in layout[side])
        assert sorted(layout[side]) == list(range(12))

trials = []
for offset in range(0, 40, 5):
    seeds = list(range(950000 + offset, 950005 + offset))
    families = []
    for bank_index, bank in enumerate(spec['banks']):
        layout = layouts[bank['id']]
        for scale in spec['scales']:
            differences = []
            separations = []
            for seed in seeds:
                high = cache[(bank_index, tuple(layout['high']), scale, seed)]
                low = cache[(bank_index, tuple(layout['low']), scale, seed)]
                differences.append(abs(high['r'] - low['r']))
                separations.append(high['f'] - low['f'])
            margins = [0.02 / max(statistics.mean(differences), 1e-15),
                       0.045 / max(max(differences), 1e-15),
                       statistics.mean(separations) / 0.28, min(separations) / 0.24]
            families.append({'bank': bank['id'], 'scale': scale,
                             'mean_abs_r_difference': statistics.mean(differences),
                             'max_abs_r_difference': max(differences),
                             'mean_f_separation': statistics.mean(separations),
                             'min_f_separation': min(separations),
                             'passed': min(margins) >= 1,
                             'score': 100 * max(0, min(1, min(margins)))})
    trials.append({'seeds': seeds, 'passed': all(family['passed'] for family in families),
                   'core_score': statistics.mean(family['score'] for family in families),
                   'worst_family_score': min(family['score'] for family in families),
                   'families': families})

summary = {'design_sha256': hashlib.sha256(design_bytes).hexdigest(),
           'public_passed': public['passed'], 'public_core_score': public['core_score'],
           'public_worst_family_score': public['worst_family_score'],
           'additional_draws_per_scale': 40, 'additional_trials': len(trials),
           'additional_samples_used_for_finalist_selection': True,
           'additional_trials_passed': sum(trial['passed'] for trial in trials),
           'additional_mean_core_score': statistics.mean(trial['core_score'] for trial in trials),
           'additional_mean_worst_family_score': statistics.mean(trial['worst_family_score'] for trial in trials),
           'trials': trials}
(ROOT / 'validation_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({name: value for name, value in summary.items() if name != 'trials'}, indent=2))
