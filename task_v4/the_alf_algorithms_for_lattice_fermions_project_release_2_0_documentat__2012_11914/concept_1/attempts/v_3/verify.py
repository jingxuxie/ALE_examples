import json
from pathlib import Path
import mpmath as mp

OUT = Path(__file__).resolve().parent
POINTS = [('1.0', '0.0'), ('0.999', '-0.001'), ('1.001', '0.001')]

def check(fields, multiplier, shift, digits):
    with mp.workdps(digits):
        beta = mp.mpf('0.75') * mp.mpf(multiplier)
        chemical = mp.mpf('1.0') + mp.mpf(shift)
        delta = beta / 16
        coupling = mp.acosh(mp.exp(delta * 2))
        cosine = mp.cosh(delta / 2)
        sine = mp.sinh(delta / 2)
        entries = [cosine**2, cosine*sine, sine**2, cosine*sine]
        half = mp.matrix(16)
        for source in range(16):
            for target in range(16):
                half[source, target] = entries[(source // 4 - target // 4) % 4] * entries[(source % 4 - target % 4) % 4]
        signs = []
        logs = []
        for spin in [1, -1]:
            product = mp.eye(16)
            for row in fields:
                diagonal = mp.diag([mp.exp(spin * coupling * field + delta * chemical) for field in row])
                sliced = half * diagonal * half
                product = sliced * product
            determinant = mp.det(mp.eye(16) + product)
            signs.append(int(mp.sign(determinant)))
            logs.append(mp.log(abs(determinant)))
        return {'digits': digits, 'flavor_signs': signs, 'weight_sign': signs[0] * signs[1], 'logabs_weight': mp.nstr(sum(logs), digits)}

def main():
    artifact = OUT / 'witness.json'
    assert artifact.stat().st_size <= 32768
    payload = json.loads(artifact.read_text())
    assert set(payload) == {'fields'}
    fields = payload['fields']
    assert isinstance(fields, list) and len(fields) == 16
    assert all(isinstance(row, list) and len(row) == 16 for row in fields)
    assert all(type(field) is int and field in [-1, 1] for row in fields for field in row)
    results = []
    for multiplier, shift in POINTS:
        checks = [check(fields, multiplier, shift, digits) for digits in [65, 95]]
        with mp.workdps(100):
            agreement = abs(mp.mpf(checks[0]['logabs_weight']) - mp.mpf(checks[1]['logabs_weight']))
            assert agreement < mp.mpf('1e-25')
        passes = all(result['weight_sign'] == -1 for result in checks)
        result = {'beta_multiplier': multiplier, 'chemical_shift': shift, 'checks': checks, 'log_weight_difference': str(agreement), 'passes': passes}
        results.append(result)
        print(json.dumps(result), flush=True)
    passes = all(result['passes'] for result in results)
    report = {'passes': passes, 'points': results}
    (OUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: all three points negative at both precisions.' if passes else 'FAIL: this candidate is not a negative-weight witness.', flush=True)
    raise SystemExit(0 if passes else 1)

if __name__ == '__main__':
    main()
