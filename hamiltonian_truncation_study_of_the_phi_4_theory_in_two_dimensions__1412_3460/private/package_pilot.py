import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parent.parent
CONCEPT = ROOT / 'concept_01'
PARTICIPANT = CONCEPT / 'participant' / 'v_01'
SOLUTION = CONCEPT / 'solution' / 'v_01'
sys.path.insert(0, str(ROOT / 'private'))
sys.path.insert(0, str(ROOT / 'private' / 'engine'))
from build_cases import cases
from physics import finite_volume


def add_code(path, content):
    if path.exists():
        if path.read_text() == content:
            return
        raise RuntimeError(f'Refusing to overwrite code without an explicit patch: {path}')
    patch = f'*** Begin Patch\n*** Add File: {path}\n'
    patch += ''.join('+' + line + '\n' for line in content.splitlines())
    patch += '*** End Patch\n'
    subprocess.run(['apply_patch', patch], check=True, stdout=subprocess.DEVNULL)


def trim_archive(source, destination, cutoff):
    destination.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((source / 'manifest.json').read_text())
    manifest['cutoff'] = cutoff
    indices = {}
    for sector in manifest['sectors']:
        filename = sector['name'] + '_basis.npz'
        basis = np.load(source / filename)
        keep = np.flatnonzero(basis['free_energy'] <= cutoff + 1e-9)
        indices[sector['name']] = keep
        np.savez_compressed(destination / filename, modes=basis['modes'], frequencies=basis['frequencies'],
                            occupations=basis['occupations'][keep], free_energy=basis['free_energy'][keep])
        sector['size'] = len(keep)
    for operator in manifest['operators']:
        keep = indices[operator['sector']]
        matrix = sparse.load_npz(source / operator['file'])
        sparse.save_npz(destination / operator['file'], matrix[keep][:, keep])
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2))


def observable_vector(levels):
    ground_sector = min(levels, key=lambda sector: levels[sector][0])
    vacuum = levels[ground_sector][0]
    values = [vacuum]
    keys = ['vacuum']
    for sector in sorted(levels):
        for index, energy in enumerate(levels[sector]):
            if sector == ground_sector and index == 0:
                continue
            keys.append(f'{sector}:{index}')
            values.append(energy - vacuum)
    return keys, np.asarray(values)


def main():
    targets = []
    audit = []
    for group in ['public', 'hidden']:
        destination = PARTICIPANT / 'input' if group == 'public' else CONCEPT / 'evaluator' / 'hidden' / 'input'
        destination.mkdir(parents=True, exist_ok=True)
        cap = 24 if group == 'public' else 28
        campaign = cases(group)
        for case in campaign:
            case['archive'] = 'block_' + case['id']
            if group == 'hidden':
                case['cutoffs'] = [12.0, 14.0, 16.0]
            source = ROOT / 'private' / 'generated' / group / f"{case['id']}_{cap}"
            trim_archive(source, destination / 'archives' / case['archive'], 16.0)
            scans = json.loads(source.with_name(source.name + '_scan.json').read_text())
            lookup = {(row['cutoff'], row['method']): row for row in scans}
            keys, target = observable_vector(lookup[(float(cap), 'improved')]['levels'])
            nearby = observable_vector(lookup[(float(cap - 2), 'improved')]['levels'])[1]
            local = observable_vector(lookup[(float(cap), 'local')]['levels'])[1]
            uncertainty = np.abs(target - nearby) + 0.25 * np.abs(target - local) + 0.0001
            if case['family'] == 'quadratic':
                uncertainty[:] = 1e-9
            item = {'case': case['id'], 'family': case['family'], 'keys': keys,
                    'target': target.tolist(), 'uncertainty': uncertainty.tolist(),
                    'high_cutoff': cap, 'baselines': {}}
            for cutoff in case['cutoffs']:
                raw = observable_vector(lookup[(cutoff, 'raw')]['levels'])[1]
                reference = observable_vector(lookup[(cutoff, 'improved')]['levels'])[1]
                raw_loss = float(np.mean(np.maximum(np.abs(raw - target) - uncertainty, 0)))
                reference_loss = float(np.mean(np.maximum(np.abs(reference - target) - uncertainty, 0)))
                item['baselines'][str(cutoff)] = {'raw_loss': raw_loss, 'reference_loss': reference_loss,
                                                'reference': reference.tolist()}
                audit.append({'group': group, 'case': case['id'], 'cutoff': cutoff,
                              'raw_loss': raw_loss, 'reference_loss': reference_loss,
                              'remaining_error_fraction': reference_loss / max(raw_loss, 1e-12)})
            if group == 'hidden':
                targets.append(item)
        (destination / 'campaign.json').write_text(json.dumps({'archive_root': 'archives', 'cases': campaign}, indent=2))
    hidden = CONCEPT / 'evaluator' / 'hidden'
    (hidden / 'targets.json').write_text(json.dumps(targets, indent=2))
    (ROOT / 'private' / 'reference_accuracy_audit.json').write_text(json.dumps(audit, indent=2))

    mass = math.sqrt(1.2)
    vacuum = 4.0 * (mass**2 * (1 - math.log(mass**2)) - 1) / (8 * math.pi)
    vacuum += finite_volume(4.0, mass, 'periodic')[1]
    calibration = {'length': 4.0, 'mass': 1.0, 'boundary': 'periodic',
                   'couplings': [{'degree': 2, 'value': 0.1}],
                   'vacuum_energy': vacuum, 'lowest_odd_gap': mass,
                   'description': 'One exact untruncated Gaussian calibration; not a truncated-matrix target.'}
    (PARTICIPANT / 'input' / 'calibration.json').write_text(json.dumps(calibration, indent=2))

    for filename in ['statefuncs.py', 'oscillators.py']:
        content = (ROOT / 'private' / 'official_port' / filename).read_text()
        content = content[content.index('import scipy'):]
        add_code(PARTICIPANT / 'workspace' / 'legacy' / filename, content)
    for filename in ['basis.py', 'archive.py', 'physics.py', 'renormalization.py']:
        add_code(SOLUTION / 'workspace' / filename, (ROOT / 'private' / 'engine' / filename).read_text())
    add_code(SOLUTION / 'workspace' / 'core.py', (ROOT / 'private' / 'engine' / 'solver.py').read_text())
    add_code(SOLUTION / 'workspace' / 'solver.py', "from core import solve as compute\n\n\ndef solve(case, archive, cutoff, method='production'):\n    mapping = {'production': 'improved', 'raw': 'raw', 'local': 'local'}\n    result = compute(case, archive, cutoff, mapping[method])\n    result['method'] = method\n    return result\n")
    for filename in ['experiment.py', 'plotting.py']:
        content = (PARTICIPANT / 'workspace' / filename).read_text()
        content = content.replace("['production', 'raw', 'scalar_twice']", "['production', 'raw', 'local']")
        add_code(SOLUTION / 'workspace' / filename, content)
    add_code(SOLUTION / 'run.sh', '#!/usr/bin/env bash\nset -euo pipefail\nHERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)\nexport OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONNOUSERSITE=1\npython3 "$HERE/workspace/experiment.py" "$1" "$2"\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
