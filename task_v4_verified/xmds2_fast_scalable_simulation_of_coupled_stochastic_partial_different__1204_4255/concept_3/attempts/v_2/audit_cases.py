from optimize import *

report = json.loads(Path(sys.argv[1]).read_text())
selected = set(range(5))
for family in ['interaction', 'calibration', 'trap', 'joint']:
    candidates = [index for index, case in enumerate(report['cases']) if case['family'] == family]
    selected.update(sorted(candidates, key=lambda index: report['cases'][index]['fidelity'])[:4])
for key, count in [('boundary_mass', 12), ('spectral_tail', 6)]:
    values = report['grids'][0]['diagnostics'][key]
    selected.update(np.argsort(values)[-count:].tolist())
cases = []
for index in sorted(selected):
    case = report['cases'][index].copy()
    case.pop('fidelity', None)
    case.pop('weight', None)
    cases.append(case)
Path(sys.argv[2]).write_text(json.dumps(cases, indent=2))
print('AUDIT CASES', len(cases))
