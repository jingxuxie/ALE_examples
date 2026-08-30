import hashlib
import itertools
import json
from pathlib import Path
import shutil
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / 'concept_2'
ARCHIVE = ROOT / 'authoring' / 'generations' / 'concept_2'


def main():
    public = CONCEPT / 'participant' / 'input' / 'contract.json'
    contract = json.loads(public.read_text())
    if contract['generation'] != 2:
        raise RuntimeError('generation 2 must be current; builder is one-shot')
    shutil.copy2(CONCEPT / 'status.json', ARCHIVE / 'generation_2' / 'completed_status.json')
    radius = contract['perturbation_radius']
    groups = {'mass_offset': list(range(9)), 'dispersion': list(range(9, 13)),
              'hybridization': list(range(13, 21)), 'mixed': list(range(21))}
    rows, labels = [], []
    generator = np.random.default_rng(970326183)
    for family, coordinates in groups.items():
        if family == 'mixed':
            patterns = list(dict.fromkeys(tuple(row) for row in generator.choice([-1., 1.], size=(520, 21))))[:512]
            if len(patterns) != 512:
                raise RuntimeError('insufficient unique corners')
        else:
            patterns = itertools.product([-1., 1.], repeat=len(coordinates))
        for pattern in patterns:
            displacement = np.zeros(25)
            displacement[coordinates] = radius * np.array(pattern)
            rows.append(displacement)
            labels.append(family)
    corners = np.array(rows)
    assert corners.shape == (1296, 25)
    assert np.unique(corners, axis=0).shape == corners.shape
    hidden = CONCEPT / 'evaluator' / 'hidden'
    np.save(hidden / 'corner_displacements.npy', corners)
    (hidden / 'corner_families.json').write_text(json.dumps(labels))
    contract.update(generation=3, corner_probe_count=len(corners),
                    corner_families={family: {'coordinates_zero_based': coordinates,
                                             'count': labels.count(family),
                                             'distribution': '512 distinct frozen uniformly drawn corners' if family == 'mixed'
                                             else 'complete corner enumeration'}
                                     for family, coordinates in groups.items()},
                    robustness_audit='42 axial probes,256 frozen uniform simultaneous probes,and1296 corners in the four declared families; phases fixed; perturbed values may extend beyond nominal bounds',
                    scope='finite frozen axial,interior,and corner manufacturing audit; not a universal certificate for the continuous uncertainty box')
    encoded = json.dumps(contract, indent=2) + '\n'
    public.write_text(encoded)
    (hidden / 'contract.json').write_text(encoded)
    task = CONCEPT / 'participant' / 'TASK.md'
    text = task.read_text()
    text = text.replace('256 frozen held-out simultaneous probes supplement the 42 axis probes.',
                        '256 frozen held-out interior probes and 1,296 corner probes supplement the 42 axis probes. '
                        'The corner audit covers all 512 mass/offset, 16 dispersion, and 256 hybridization corners, '
                        'plus 512 held-out simultaneous corners; exact coordinate families are in the contract. '
                        'The perturbation box and all response thresholds are unchanged.')
    task.write_text(text)
    destination = ARCHIVE / 'generation_3'
    destination.mkdir()
    for name in ('participant', 'evaluator'):
        shutil.copytree(CONCEPT / name, destination / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    hashes = {str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(destination.rglob('*')) if path.is_file()}
    (destination / 'frozen_hashes.json').write_text(json.dumps(hashes, indent=2))
    state = json.loads((CONCEPT / 'status.json').read_text())
    state.update(status='ready', generation=3, ratchet_generations=2,
                 target='All fixed nominal,42 axial,256 interior,and1296 corner conditions',
                 generation3_frozen_epoch=time.time(), solvability='unknown',
                 known_solution=None, privileged_positive_control=None,
                 fresh_agent_score=None, fresh_agent_worst_family_score=None,
                 reason='Final ratchet addresses independently reproduced cancellation failure at admissible corners; no fresh generation-3 result yet')
    (CONCEPT / 'status.json').write_text(json.dumps(state, indent=2))
    print(json.dumps({'generation': 3, 'count': len(corners),
                      'families': {name: labels.count(name) for name in groups},
                      'frozen_epoch': state['generation3_frozen_epoch']}, indent=2))


if __name__ == '__main__':
    main()
