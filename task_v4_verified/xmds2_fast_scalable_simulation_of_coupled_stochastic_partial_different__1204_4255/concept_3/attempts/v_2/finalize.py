from optimize import *

options = []
for prefix in ['guarded', 'refined']:
    report_path = Path(prefix + '_audit.json')
    if not report_path.exists():
        continue
    audit = json.loads(report_path.read_text())
    survey = json.loads(Path(prefix + '_corners.json').read_text())
    if not audit['valid']:
        continue
    candidate = fc.read_json(prefix + '_snapshot.json')
    fc.validate_artifact(candidate, PROTOCOL)
    options.append((survey['core_score'], survey['worst_family_score'], survey['worst_case_score'], prefix, audit, survey))
assert options
choice = max(options, key=lambda option: option[:3])
prefix, audit, survey = choice[3:]
write('control.json', load(prefix + '_snapshot.json'))
splines, diagnostics = fc.validate_artifact(fc.read_json('control.json'), PROTOCOL)
print(json.dumps({'selected': prefix, 'artifact_bytes': Path('control.json').stat().st_size, 'coarse_corner_survey': {key: survey[key] for key in ['core_score', 'worst_family_score', 'worst_case_score']}, 'audit_valid': audit['valid'], 'audited_cases': len(audit['cases']), 'public_audited_fidelity': audit['family_scores']['public'], 'stress_audited_minimum': audit['worst_case_score'], 'max_allowance': max(audit['allowance']), 'max_distance': np.max(audit['distance']), 'max_boundary_mass': max(max(grid['diagnostics']['boundary_mass']) for grid in audit['grids']), 'resource_score': fc.resource_score(splines, PROTOCOL)}, indent=2))
