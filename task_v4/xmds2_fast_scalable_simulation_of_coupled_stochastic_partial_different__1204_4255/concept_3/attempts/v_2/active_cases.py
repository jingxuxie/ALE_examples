from optimize import *

report = json.loads(Path(sys.argv[1]).read_text())
balanced = json.loads(Path('balanced_cases.json').read_text())
ranked = sorted(range(len(report['cases'])), key=lambda index: report['cases'][index]['fidelity'])[:20]
boundary = report['grids'][0]['diagnostics']['boundary_mass']
ranked += sorted(range(len(boundary)), key=lambda index: -boundary[index])[:8]
cases = balanced.copy()
keys = list(PROTOCOL['uncertainty'])
for index in ranked:
    case = report['cases'][index].copy()
    case.pop('fidelity', None)
    if not any(all(existing[key] == case[key] for key in keys) for existing in cases):
        cases.append(case)
for case in cases:
    case['weight'] = (1.5 if case['family'] == 'joint' else 1.0) / sum(other['family'] == case['family'] for other in cases)
Path(sys.argv[2]).write_text(json.dumps(cases, indent=2))
print('ACTIVE CASES', len(cases))
