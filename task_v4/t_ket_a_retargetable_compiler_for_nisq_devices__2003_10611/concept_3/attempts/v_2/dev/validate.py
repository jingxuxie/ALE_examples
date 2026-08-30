import json
from pathlib import Path


def validate(case, gates):
    size = case['n']
    rows = [1 << wire for wire in range(size)]
    clocks = [0] * size
    visited = set(rows)
    edges = {tuple(sorted(edge)) for edge in case['edges']}
    assert isinstance(gates, list) and len(gates) <= 50000
    for gate in gates:
        assert isinstance(gate, list) and len(gate) == 2
        control, target = gate
        assert type(control) is int and type(target) is int
        assert tuple(sorted(gate)) in edges
        rows[target] ^= rows[control]
        visited.add(rows[target])
        clocks[control] = clocks[target] = 1 + max(clocks[control], clocks[target])
    missing = sorted(set(case['required_parities']) - visited)
    valid = rows == case['target_rows'] and not missing
    count, depth = len(gates), max(clocks)
    passed = valid and count <= case['max_cnots'] and depth <= case['max_depth']
    return dict(id=case['id'], valid=valid, passed=passed, count=count, depth=depth,
                count_budget=case['max_cnots'], depth_budget=case['max_depth'], missing=missing,
                target_correct=rows == case['target_rows'])


if __name__ == '__main__':
    import sys
    path = Path(sys.argv[1] if len(sys.argv) > 1 else 'submission/witness.json')
    assert not path.is_symlink() and path.stat().st_size <= 8388608
    witness = json.loads(path.read_text())
    cases = json.loads(Path('dev/instances.json').read_text())['instances']
    assert set(witness) == {'schema_version', 'circuits'}
    assert type(witness['schema_version']) is int and witness['schema_version'] == 1
    assert set(witness['circuits']) == {case['id'] for case in cases}
    results = [validate(case, witness['circuits'][case['id']]) for case in cases]
    print(json.dumps(results, indent=2))
    Path('dev/validation.json').write_text(json.dumps(results, indent=2) + '\n')
