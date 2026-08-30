import json
from pathlib import Path
import time

import mpmath as mp


OUTPUT = Path(__file__).resolve().parent
PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/the_alf_algorithms_for_lattice_fermions_project_release_2_0_documentat__2012_11914/concept_1/participant')
MODEL = json.loads((PARTICIPANT / 'input' / 'model.json').read_text())


def compute(fields, point, digits):
    with mp.workdps(digits):
        beta = mp.mpf(str(MODEL['beta'])) * mp.mpf(str(point['beta_multiplier']))
        chemical = mp.mpf(str(MODEL['chemical_potential'])) + mp.mpf(str(point['chemical_shift']))
        delta = beta / MODEL['time_slices']
        coupling = mp.acosh(mp.exp(delta * mp.mpf(str(MODEL['interaction'])) / 2))
        hopping = mp.mpf(str(MODEL['hopping']))
        size = MODEL['linear_size']
        sites = size ** 2
        kinetic = mp.zeros(sites)
        for horizontal in range(size):
            for vertical in range(size):
                source = size * horizontal + vertical
                for shift_horizontal, shift_vertical in [(1, 0), (0, 1)]:
                    target = size * ((horizontal + shift_horizontal) % size) + (vertical + shift_vertical) % size
                    kinetic[source, target] = -hopping
                    kinetic[target, source] = -hopping
        half_step = mp.expm(-delta * kinetic / 2)
        determinants = []
        for spin in [1, -1]:
            product = mp.eye(sites)
            for time_index in range(MODEL['time_slices']):
                diagonal = mp.diag([mp.exp(spin * coupling * field + delta * chemical) for field in fields[time_index]])
                slice_matrix = half_step * diagonal * half_step
                product = slice_matrix * product
            determinants.append(mp.det(mp.eye(sites) + product))
        signs = [int(mp.sign(determinant)) for determinant in determinants]
        log_weight = sum(mp.log(abs(determinant)) for determinant in determinants)
        return {
            'digits': digits,
            'flavor_signs': signs,
            'weight_sign': signs[0] * signs[1],
            'logabs_weight': mp.nstr(log_weight, digits),
            'determinants': [mp.nstr(determinant, digits) for determinant in determinants],
        }


def main():
    start = time.monotonic()
    artifact = OUTPUT / 'witness.json'
    assert artifact.stat().st_size <= MODEL['max_artifact_bytes']
    payload = json.loads(artifact.read_text())
    assert set(payload) == {'fields'}
    fields = payload['fields']
    assert isinstance(fields, list) and len(fields) == 16
    assert all(isinstance(row, list) and len(row) == 16 for row in fields)
    assert all(type(field) is int and field in [-1, 1] for row in fields for field in row)
    reports = []
    for point in MODEL['certification_points']:
        results = [compute(fields, point, digits) for digits in MODEL['precision_digits']]
        with mp.workdps(max(MODEL['precision_digits'])):
            difference = abs(mp.mpf(results[0]['logabs_weight']) - mp.mpf(results[1]['logabs_weight']))
            passed = all(result['weight_sign'] == -1 for result in results) and difference < mp.mpf(str(MODEL['log_weight_agreement_tolerance']))
            report = {'point': point, 'results': results, 'logabs_difference': mp.nstr(difference, 20), 'passed': passed}
        reports.append(report)
        print(json.dumps(report), flush=True)
    (OUTPUT / 'verification.json').write_text(json.dumps({'points': reports, 'passed': all(report['passed'] for report in reports)}, indent=2) + '\n')
    assert all(report['passed'] for report in reports)
    print('All certification points passed in', round(time.monotonic() - start, 2), 'seconds', flush=True)


if __name__ == '__main__':
    main()
