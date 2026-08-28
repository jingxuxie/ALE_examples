import copy
import hashlib
import json
import pathlib
import secrets
import subprocess
import sys
import tempfile
import numpy as np

from reference.oracle import solve as oracle
from metrics import errors, GROUPS

ROOT = pathlib.Path(__file__).resolve().parents[1]
POOL = ROOT / 'private/challenge_pool'
FAMILIES = ['compensated_noncollinear', 'empty_sparse', 'reversal_interfaces']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, separators=(',', ':'), allow_nan=False)+'\n')


def make_case(family, seed, large=False, ordinal=0):
    random = np.random.default_rng(seed)
    if family == 'compensated_noncollinear':
        num_sublattices = 4 if large else 2
    elif family == 'empty_sparse':
        num_sublattices = 6 if large else 4
    else:
        num_sublattices = 4 if large else 3
    num_stacks = (2+ordinal % 3) if large else (1+ordinal % 2)
    depth = (20+4*(ordinal % 5)) if large else (5+ordinal % 3)
    base_count = (12+2*(ordinal % 3)) if large else 4
    materials = []
    for sublattice in range(num_sublattices):
        for variant in range(2):
            materials.append({'sublattice': sublattice, 'rho_ohm_m': float(10**random.uniform(-7.3, -5.8)), 'rho_spin_ohm_m': float(10**random.uniform(-7.3, -5.8)), 'moment_muB': 2.0 if family == 'compensated_noncollinear' else float(random.uniform(0.8, 4.5)), 'alpha': float(random.uniform(0.01, 0.25)), 'eta': float(random.uniform(0.15, 0.8)), 'beta': float(random.uniform(-0.22, 0.25))})
    atoms = []
    stacks = []
    for stack_id in range(num_stacks):
        stack = list(range(stack_id*depth, (stack_id+1)*depth))
        stacks.append(stack)
        for layer, cell in enumerate(stack):
            present = np.ones(num_sublattices, dtype=bool)
            if family == 'empty_sparse' and layer not in [0, depth-1]:
                present = random.random(num_sublattices) > (0.45+0.1*(ordinal % 3))
                if not present.any():
                    present[random.integers(num_sublattices)] = True
            for sublattice in range(num_sublattices):
                if not present[sublattice]:
                    continue
                count = base_count if family == 'compensated_noncollinear' else int(random.integers(max(2, base_count//2), base_count+3))
                polar = 0.35+0.41*layer+0.19*stack_id+0.3*(sublattice//2)
                azimuth = 0.27*layer+0.53*(sublattice//2)+0.11*stack_id
                if family != 'compensated_noncollinear':
                    azimuth += 0.7*sublattice
                for replica in range(count):
                    local_polar = polar+0.12*(replica-(count-1)/2)/count
                    spin = np.array([np.sin(local_polar)*np.cos(azimuth), np.sin(local_polar)*np.sin(azimuth), np.cos(local_polar)])
                    if family == 'compensated_noncollinear' and sublattice % 2:
                        spin = -spin
                    variant = int((layer+replica+stack_id) % 2)
                    if family == 'reversal_interfaces':
                        variant = int((layer >= depth//2) ^ (replica % 4 == 0))
                    atoms.append({'cell': cell, 'material': 2*sublattice+variant, 'spin': spin.tolist()})
    random.shuffle(atoms)
    return {'version': 1, 'case_id': hashlib.sha256(f'{family}:{seed}'.encode()).hexdigest()[:14], 'num_sublattices': num_sublattices, 'voltage_V': float(random.uniform(0.001, 0.045)), 'direction': -1 if ordinal % 2 else 1, 'cell_length_m': float(random.uniform(0.6e-9, 2.0e-9)), 'cell_area_m2': float(random.uniform(2.0e-18, 12e-18)), 'stacks': stacks, 'materials': materials, 'atoms': atoms}


def execute_trusted(script, case):
    with tempfile.TemporaryDirectory(prefix='transport-reference-') as scratch:
        source = pathlib.Path(scratch)/'case.json'
        destination = pathlib.Path(scratch)/'result.json'
        write_json(source, case)
        subprocess.run(['/usr/bin/python3', '-s', str(script), str(source), str(destination)], check=True, timeout=30, env={'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'PYTHONNOUSERSITE': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'})
        return json.loads(destination.read_text())


def compare(predicted, expected, label):
    error = errors(predicted, expected)
    if max(error.values()) > 2e-11:
        raise AssertionError((label, error))
    return max(error.values())


def invariant_checks(case, answer):
    currents = np.array(answer['channel_current_A'])
    fields = np.array(answer['atom_field_T'])
    derivatives = np.array(answer['atom_dspin_dt'])
    spins = np.array([atom['spin'] for atom in case['atoms']])
    for stack_id, stack in enumerate(case['stacks']):
        np.testing.assert_allclose(currents[stack].sum(axis=1), answer['stack_current_A'][stack_id], rtol=1e-12)
        np.testing.assert_allclose(answer['stack_resistance_ohm'][stack_id]*answer['stack_current_A'][stack_id], case['voltage_V'], rtol=1e-12)
        entrance = stack[0] if case['direction'] == 1 else stack[-1]
        selected = [index for index, atom in enumerate(case['atoms']) if atom['cell'] == entrance]
        np.testing.assert_equal(fields[selected], 0.0)
    np.testing.assert_allclose(sum(answer['stack_current_A']), answer['total_current_A'], rtol=1e-12)
    relative_tangency = np.max(np.abs(np.sum(spins*derivatives, axis=1)))/max(np.max(np.linalg.norm(derivatives, axis=1)), 1e-30)
    if relative_tangency > 1e-12:
        raise AssertionError('Derivative not tangent')
    occupancy = np.zeros(currents.shape, dtype=int)
    for atom in case['atoms']:
        occupancy[atom['cell'], case['materials'][atom['material']]['sublattice']] += 1
    np.testing.assert_equal(currents[occupancy == 0], 0.0)
    return float(relative_tangency)


def metamorphic_checks(case):
    source = ROOT/'private/reference/solve.py'
    answer = execute_trusted(source, case)
    changed = copy.deepcopy(case)
    changed['voltage_V'] *= 1.7
    expected = {key: np.asarray(value)*(1.7 if 'current' in key or key in ['atom_field_T', 'atom_dspin_dt'] else 1.0) for key, value in answer.items()}
    checks = {'voltage_linearity': compare(execute_trusted(source, changed), expected, 'voltage')}
    changed = copy.deepcopy(case)
    for material in changed['materials']:
        material['moment_muB'] *= 2.0
    expected = {key: np.asarray(value)*(0.5 if key in ['atom_field_T', 'atom_dspin_dt'] else 1.0) for key, value in answer.items()}
    checks['moment_normalization'] = compare(execute_trusted(source, changed), expected, 'moments')
    changed = copy.deepcopy(case)
    for atom in changed['atoms']:
        atom['spin'] = [atom['spin'][1], atom['spin'][2], atom['spin'][0]]
    expected = {key: np.asarray(value)[:, [1, 2, 0]] if key in ['atom_field_T', 'atom_dspin_dt'] else value for key, value in answer.items()}
    checks['rotation_covariance'] = compare(execute_trusted(source, changed), expected, 'rotation')
    changed = copy.deepcopy(case)
    for material in changed['materials']:
        material['sublattice'] = case['num_sublattices']-1-material['sublattice']
    expected = dict(answer)
    expected['channel_current_A'] = np.asarray(answer['channel_current_A'])[:, ::-1]
    checks['sublattice_permutation'] = compare(execute_trusted(source, changed), expected, 'sublattice labels')
    changed = copy.deepcopy(case)
    changed['atoms'].reverse()
    expected = dict(answer)
    for key in ['atom_field_T', 'atom_dspin_dt']:
        expected[key] = np.asarray(answer[key])[::-1]
    checks['atom_permutation'] = compare(execute_trusted(source, changed), expected, 'atom order')
    changed = copy.deepcopy(case)
    changed['direction'] *= -1
    mirrored_cells = list(range(sum(map(len, case['stacks']))))
    for stack in case['stacks']:
        for cell in stack:
            mirrored_cells[cell] = stack[0]+stack[-1]-cell
    for atom in changed['atoms']:
        atom['cell'] = mirrored_cells[atom['cell']]
    expected = dict(answer)
    for key in ['cell_resistance_ohm', 'channel_current_A']:
        expected[key] = np.asarray(answer[key])[mirrored_cells]
    checks['reversed_direction_mirrored_stack'] = compare(execute_trusted(source, changed), expected, 'current reversal')
    return checks


def analytic_check():
    material = {'sublattice': 0, 'rho_ohm_m': 2e-7, 'rho_spin_ohm_m': 4e-7, 'moment_muB': 2.0, 'alpha': 0.0, 'eta': 1.0, 'beta': 0.0}
    case = {'version': 1, 'case_id': 'analytic', 'num_sublattices': 1, 'voltage_V': 0.01, 'direction': 1, 'cell_length_m': 1e-9, 'cell_area_m2': 1e-18, 'stacks': [[0, 1]], 'materials': [material], 'atoms': [{'cell': 0, 'material': 0, 'spin': [0.0, 0.0, 1.0]}, {'cell': 1, 'material': 0, 'spin': [1.0, 0.0, 0.0]}]}
    current = 0.01/600.0
    amplitude = 35486911.9121*current/2.0
    expected = {'total_resistance_ohm': 600.0, 'total_current_A': current, 'stack_resistance_ohm': [600.0], 'stack_current_A': [current], 'cell_resistance_ohm': [200.0, 400.0], 'channel_current_A': [[current], [current]], 'atom_field_T': [[0.0, 0.0, 0.0], [0.0, -amplitude, 0.0]], 'atom_dspin_dt': [[0.0, 0.0, 0.0], [0.0, 0.0, 1.760859e11*amplitude]]}
    return compare(execute_trusted(ROOT/'private/reference/solve.py', case), expected, 'analytic orthogonal two-cell stack')


def main():
    if (POOL/'manifest.json').exists():
        raise SystemExit('Frozen manifest already exists; refusing to regenerate cases.')
    validation = {'analytic_two_cell_relative_error': analytic_check(), 'differential_cases': [], 'invariants': [], 'metamorphic': {}}
    entries = {split: [] for split in ['initial', 'challenge', 'confirmation']}
    calibrations = {family: {group: [] for group in GROUPS} for family in FAMILIES}
    for split_id, (split, repetitions) in enumerate([('initial', 2), ('challenge', 6), ('confirmation', 2)]):
        for family_id, family in enumerate(FAMILIES):
            for ordinal in range(repetitions):
                seed = 918273 + split_id*100003 + family_id*7919 + ordinal*997
                case = make_case(family, seed, large=split != 'initial', ordinal=ordinal)
                case_path = POOL/'cases'/(case['case_id']+'.json')
                expected_path = POOL/'expected'/(case['case_id']+'.npz')
                write_json(case_path, case)
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                expected = oracle(case)
                strong = execute_trusted(ROOT/'private/reference/solve.py', case)
                discrepancy = compare(strong, expected, case['case_id'])
                validation['differential_cases'].append({'id': case['case_id'], 'family': family, 'atoms': len(case['atoms']), 'max_group_relative_error': discrepancy})
                validation['invariants'].append({'id': case['case_id'], 'relative_tangency_error': invariant_checks(case, strong)})
                np.savez_compressed(expected_path, **expected)
                entries[split].append({'id': case['case_id'], 'family': family, 'seed': seed, 'case': str(case_path.relative_to(POOL)), 'expected': str(expected_path.relative_to(POOL)), 'case_sha256': digest(case_path), 'expected_sha256': digest(expected_path), 'atoms': len(case['atoms']), 'cells': sum(map(len, case['stacks']))})
                if split == 'initial':
                    weak = execute_trusted(ROOT/'participant/workspace/baseline.py', case)
                    weak_error = errors(weak, expected)
                    for group in GROUPS:
                        calibrations[family][group].append(weak_error[group])
                    if ordinal == 0:
                        validation['metamorphic'][family] = metamorphic_checks(case)
    calibration = {family: {group: max(float(np.mean(values)), 0.01) for group, values in groups.items()} for family, groups in calibrations.items()}
    write_json(POOL/'calibration.json', calibration)
    write_json(POOL/'reserved_seeds.json', {'status': 'unused; never passed to generator or reference', 'seeds': [secrets.randbits(48) for unused in range(24)]})
    write_json(ROOT/'private/reference/independent_validations.json', validation)
    for family_id, family in enumerate(FAMILIES):
        example = make_case(family, 3101+family_id, ordinal=family_id)
        write_json(ROOT/'participant/input'/('example_'+family+'.json'), example)
    manifest = {'format': 1, 'frozen': True, 'expected_origin': 'Independent NumPy implementation, cross-checked against extracted official C++ on every frozen case; analytic and metamorphic checks in reference/independent_validations.json.', 'calibration_sha256': digest(POOL/'calibration.json'), 'splits': entries, 'reserved_seeds_sha256': digest(POOL/'reserved_seeds.json')}
    write_json(POOL/'manifest.json', manifest)
    print(json.dumps({'frozen_counts': {split: len(rows) for split, rows in entries.items()}, 'max_differential_error': max(row['max_group_relative_error'] for row in validation['differential_cases'])}))


if __name__ == '__main__':
    main()
