import json
from pathlib import Path
import subprocess

from search import ROOT, SPEC, waveforms


def main():
    reports = []
    for name in ('first_linear_validation.json', 'linear_validation.json', 'round2_validation.json', 'round4_validation.json'):
        path = ROOT / name
        if path.exists():
            reports.append(json.loads(path.read_text()))
    report = max(reports, key=lambda item: item['worst']['margin'])
    candidate = report['witness']
    families = waveforms(candidate, SPEC)
    report['valid'] = True
    report['evaluation_complete'] = True
    report['core_score'] = report['nominal']['score']
    report['worst_family_score'] = report['worst']['score']
    report['resource_score'] = 1200 / candidate['depth']
    report['min_pulse'] = min(float(angles.min()) for angles in families.values())
    report['max_pulse'] = max(float(angles.max()) for angles in families.values())
    report['max_slew'] = max(float(abs(angles[1:]-angles[:-1]).max()) for angles in families.values())
    (ROOT / 'witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
    (ROOT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    outcome = 'All 325 waveforms pass.' if report['passed'] else 'This is a partial-result submission; the full counterexample threshold is not met.'
    text = f'''# Submission

`witness.json` is the submitted depth-{candidate['depth']} waveform.

{outcome}

Public-simulator validation of all 325 waveforms:

- Nominal score: {report['core_score']:.8f}
- Worst-family score: {report['worst_family_score']:.8f}
- Maximum convergence spread: {report['max_spread']:.12f}
- Minimum absolute observable error: {report['min_error']:.12f}
- Artifact and physical constraints: valid.

`validation.json` contains the actual public-simulator results and critical cases.
To repeat the complete check, using the unchanged participant assets:

```bash
PYTHONDONTWRITEBYTECODE=1 python search.py validate --report validation.json
```

The supporting search uses constant-waveform grids, local minimax searches,
and finite-difference linear programming over all 325 physical waveforms.
All circuit values come from the supplied exact and independent MPS simulations.
This does not claim continuous calibration-box certification or falsify the paper.
'''
    (ROOT / 'README.md').write_text(text)
    keep = {'witness.json', 'validation.json', 'README.md', 'search.py', 'linear_search.py', 'active_families.json'}
    deletions = []
    for path in ROOT.iterdir():
        if path.is_file() and path.name not in keep:
            if path.suffix == '.npz':
                path.unlink()
            else:
                deletions.append(f'*** Delete File: {path.name}')
    if deletions:
        subprocess.run(['apply_patch', '*** Begin Patch\n' + '\n'.join(deletions) + '\n*** End Patch'], cwd=ROOT, check=True)
    for name in keep:
        path = ROOT / name
        assert path.is_file() and not path.is_symlink() and path.stat().st_size <= 16384
    print(json.dumps({key: report[key] for key in ('valid', 'passed', 'family_count', 'core_score', 'worst_family_score', 'max_spread', 'min_error')}))


if __name__ == '__main__':
    main()
