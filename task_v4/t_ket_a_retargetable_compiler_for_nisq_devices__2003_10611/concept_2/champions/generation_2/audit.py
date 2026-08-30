import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def audit(path):
    raw = path.read_bytes()
    assert path.is_file() and not path.is_symlink() and len(raw) <= 1_000_000
    witness = json.loads(raw)
    assert set(witness) == {'version', 'hardware', 'gates', 'route', 'final_mapping'}
    assert type(witness['version']) is int and witness['version'] == 1
    graph = witness['hardware']
    if graph == 'ring16':
        edges = {(node, node+1) for node in range(15)} | {(0, 15)}
    elif graph == 'ladder16':
        edges = {(node, node+1) for node in range(16) if node % 8 < 7}
        edges |= {(node, node+8) for node in range(8)}
    elif graph == 'grid16':
        edges = {(node, node+1) for node in range(16) if node % 4 < 3}
        edges |= {(node, node+4) for node in range(12)}
    else:
        raise AssertionError('unsupported graph')
    gates = witness['gates']
    assert 48 <= len(gates) <= 200
    coverage, pairs = Counter(), Counter()
    neighbors = [set() for _ in range(16)]
    required = [[] for _ in range(16)]
    previous = [-1] * 16
    for index, gate in enumerate(gates):
        assert len(gate) == 2 and all(type(node) is int and 0 <= node < 16 for node in gate)
        first, second = gate
        assert first != second
        assert previous[first] != previous[second] or previous[first] == -1
        previous[first] = previous[second] = index
        for node in gate:
            coverage[node] += 1
            required[node].append(index)
        pairs[tuple(sorted(gate))] += 1
        neighbors[first].add(second)
        neighbors[second].add(first)
    assert len(coverage) == 16 and min(coverage.values()) >= 4
    assert max(coverage.values()) <= min(40, (len(gates)+3)//4)
    assert len(pairs) >= 16 and max(pairs.values()) <= 8
    assert min(map(len, neighbors)) >= 2
    reached = {0}
    while True:
        expanded = reached | {neighbor for node in reached for neighbor in neighbors[node]}
        if reached == expanded:
            break
        reached = expanded
    assert len(reached) == 16
    occupants = list(range(16))
    executed = [[] for _ in range(16)]
    seen = set()
    swaps = 0
    swap_slots = []
    assert len(witness['route']) <= 20_000
    for operation in witness['route']:
        assert operation[0] in {'swap', 'gate'}
        if operation[0] == 'swap':
            assert len(operation) == 3
            first, second = operation[1:]
            assert tuple(sorted((first, second))) in edges
            occupants[first], occupants[second] = occupants[second], occupants[first]
            swaps += 1
            swap_slots.append({'executed_gates': len(seen), 'physical_edge': [first, second]})
        else:
            assert len(operation) == 4
            index, first, second = operation[1:]
            assert 0 <= index < len(gates) and index not in seen
            assert tuple(sorted((first, second))) in edges
            assert [occupants[first], occupants[second]] == gates[index]
            seen.add(index)
            for node in gates[index]:
                executed[node].append(index)
                assert executed[node] == required[node][:len(executed[node])]
    assert seen == set(range(len(gates)))
    assert executed == required
    assert 8 <= swaps <= 200
    final_mapping = [occupants.index(node) for node in range(16)]
    assert final_mapping == witness['final_mapping']
    suffix_degrees = {}
    for cutoff in (0, 4, 8, 12, 16, 24):
        suffix_neighbors = [set() for _ in range(16)]
        for first, second in gates[cutoff:]:
            suffix_neighbors[first].add(second)
            suffix_neighbors[second].add(first)
        suffix_degrees[cutoff] = max(map(len, suffix_neighbors))
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'file_bytes': len(raw),
            'hardware': graph, 'gate_count': len(gates), 'swap_count': swaps,
            'native_2q_count': len(gates)+3*swaps,
            'wire_coverage': [coverage[node] for node in range(16)],
            'wire_partner_counts': list(map(len, neighbors)),
            'distinct_interaction_pairs': len(pairs), 'maximum_pair_occurrences': max(pairs.values()),
            'suffix_maximum_degrees': suffix_degrees, 'swap_schedule': swap_slots,
            'final_mapping': final_mapping, 'independent_audit_passed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('witness', type=Path, nargs='?', default=Path('witness.json'))
    arguments = parser.parse_args()
    print(json.dumps(audit(arguments.witness), indent=2))
