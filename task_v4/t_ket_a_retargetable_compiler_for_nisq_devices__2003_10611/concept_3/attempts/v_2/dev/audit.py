import json
from fractions import Fraction
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate key: {key}')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(value)


root = Path('submission')
path = root / 'witness.json'
assert root.is_dir() and not root.is_symlink()
assert path.is_file() and not path.is_symlink()
assert path.stat().st_size <= 8388608
witness = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object,
                     parse_constant=reject_constant)
suite = json.loads(Path('dev/instances.json').read_text())
assert set(witness) == {'schema_version', 'circuits'}
assert type(witness['schema_version']) is int and witness['schema_version'] == 1
assert set(witness['circuits']) == {case['id'] for case in suite['instances']}
results = []
efficiencies = []
family_results = {}
for case in suite['instances']:
    size = case['n']
    gates = witness['circuits'][case['id']]
    assert type(gates) is list and len(gates) <= 50000
    rows = [tuple(int(wire == column) for column in range(size)) for wire in range(size)]
    visited = set(rows)
    edges = {frozenset(edge) for edge in case['edges']}
    latest = [-1] * size
    levels = []
    for gate in gates:
        assert type(gate) is list and len(gate) == 2
        assert all(type(wire) is int and 0 <= wire < size for wire in gate)
        control, target = gate
        assert control != target and frozenset(gate) in edges
        rows[target] = tuple(control_bit ^ target_bit for control_bit, target_bit in zip(rows[control], rows[target]))
        visited.add(rows[target])
        predecessors = [latest[wire] for wire in gate if latest[wire] >= 0]
        levels.append(1 + max((levels[index] for index in predecessors), default=0))
        latest[control] = latest[target] = len(levels) - 1
    assert rows == [tuple((mask >> column) & 1 for column in range(size)) for mask in case['target_rows']]
    assert all(tuple((mask >> column) & 1 for column in range(size)) in visited for mask in case['required_parities'])
    for input_wire in range(size):
        state = 1 << input_wire
        for control, target in gates:
            if state & (1 << control):
                state ^= 1 << target
        expected = sum(((mask >> input_wire) & 1) << output_wire for output_wire, mask in enumerate(case['target_rows']))
        assert state == expected
    count, depth = len(gates), max(levels, default=0)
    passed = count <= case['max_cnots'] and depth <= case['max_depth']
    efficiency = (min(Fraction(1), Fraction(case['max_cnots'], max(1, count))) +
                  min(Fraction(1), Fraction(case['max_depth'], max(1, depth)))) / 2
    efficiencies.append(efficiency)
    family_results.setdefault(case['family'], []).append(passed)
    results.append(dict(id=case['id'], valid=True, passed=passed, cnots=count, depth=depth,
                        max_cnots=case['max_cnots'], max_depth=case['max_depth'],
                        parities_visited=len(case['required_parities'])))
report = dict(valid=True, passed=all(result['passed'] for result in results),
              core_score=sum(result['passed'] for result in results) / len(results),
              worst_family_score=min(sum(values) / len(values) for values in family_results.values()),
              resource_score=float(sum(efficiencies) / len(efficiencies)),
              witness_bytes=path.stat().st_size, cases=results)
Path('dev/final_audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
