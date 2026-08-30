import json
from search import OUT, SPEC, assess, waveforms


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('nonfinite JSON number: ' + value)


def main():
    path = OUT / 'witness.json'
    assert not path.is_symlink()
    assert path.is_file() and path.stat().st_size <= 16 * 1024
    candidate = json.loads(path.read_text(), object_pairs_hook=unique_object,
                           parse_constant=reject_constant)
    families = waveforms(candidate, SPEC)
    records = assess(candidate, robust=True)
    result = dict(witness=candidate, valid=True,
                  passed=all(record['passed'] for record in records.values()),
                  core_score=records['nominal']['score'],
                  worst_family_score=min(record['score'] for record in records.values()),
                  worst_margin=min(record['margin'] for record in records.values()),
                  resource_score=100 * 12 / candidate['depth'],
                  families=records,
                  maximum_slew=max(float(abs(angles[1:] - angles[:-1]).max())
                                   for angles in families.values()),
                  minimum_angle=min(float(angles.min()) for angles in families.values()),
                  maximum_angle=max(float(angles.max()) for angles in families.values()))
    (OUT / 'final_validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'families'}, indent=2))
    for name, record in records.items():
        print(name, 'spread', record['spread'], 'error', record['error'], 'passed', record['passed'])
    assert result['passed'], 'not all robustness families pass'


if __name__ == '__main__':
    main()
