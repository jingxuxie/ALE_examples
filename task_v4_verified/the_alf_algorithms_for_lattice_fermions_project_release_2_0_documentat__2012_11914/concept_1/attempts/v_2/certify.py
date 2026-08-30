import argparse
import json
from pathlib import Path

import mpmath as mp


def certify(path):
    root = Path(__file__).resolve().parent
    model = json.loads((root.parents[1] / 'participant/input/model.json').read_text())
    payload_bytes = path.read_bytes()
    assert len(payload_bytes) <= model['max_artifact_bytes']
    payload = json.loads(payload_bytes)
    assert isinstance(payload, dict) and set(payload) == {'fields'}
    fields = payload['fields']
    assert isinstance(fields, list) and len(fields) == 16
    assert all(isinstance(row, list) and len(row) == 16 for row in fields)
    assert all(type(entry) is int and entry in (-1, 1) for row in fields for entry in row)
    records = []
    for point in model['certification_points']:
        values = []
        for digits in model['precision_digits']:
            with mp.workdps(digits):
                beta = mp.mpf(str(model['beta'])) * mp.mpf(str(point['beta_multiplier']))
                chemical = mp.mpf(str(model['chemical_potential'])) + mp.mpf(str(point['chemical_shift']))
                delta = beta / model['time_slices']
                coupling = mp.acosh(mp.exp(delta * mp.mpf(str(model['interaction'])) / 2))
                kinetic = mp.matrix(16)
                for horizontal in range(4):
                    for vertical in range(4):
                        source = 4 * horizontal + vertical
                        for delta_horizontal, delta_vertical in [(1, 0), (0, 1)]:
                            target = 4 * ((horizontal + delta_horizontal) % 4) + (vertical + delta_vertical) % 4
                            kinetic[source, target] = kinetic[target, source] = -mp.mpf(str(model['hopping']))
                half_kinetic = mp.expm(-delta * kinetic / 2)
                signs = []
                log_weight = mp.mpf(0)
                for spin in [1, -1]:
                    product = mp.eye(16)
                    for row in fields:
                        diagonal = mp.diag([mp.exp(spin * coupling * entry + delta * chemical) for entry in row])
                        slice_matrix = half_kinetic * diagonal * half_kinetic
                        product = slice_matrix * product
                    determinant = mp.det(mp.eye(16) + product)
                    signs.append(int(mp.sign(determinant)))
                    log_weight += mp.log(abs(determinant))
                record = {'point': point, 'digits': digits, 'flavor_signs': signs, 'weight_sign': signs[0] * signs[1], 'logabs_weight': mp.nstr(log_weight, digits)}
                records.append(record)
                values.append(log_weight)
                print(json.dumps(record), flush=True)
                assert signs[0] * signs[1] == -1, 'Weight is not negative'
        with mp.workdps(max(model['precision_digits'])):
            difference = abs(values[0] - values[1])
            assert difference < mp.mpf(str(model['log_weight_agreement_tolerance'])), str(difference)
            print('Log agreement:', mp.nstr(difference, 8), flush=True)
    (root / 'certification.json').write_text(json.dumps(records, indent=2) + '\n')
    print('PASS: all three points at both required precisions', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=Path, nargs='?', default=Path(__file__).resolve().parent / 'witness.json')
    certify(parser.parse_args().path)
