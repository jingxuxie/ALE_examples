import hashlib
import json
import sys
from collections import Counter, deque
from pathlib import Path

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/concept_2/adversary/generation_3/participant/input')
sys.path.insert(0, str(ASSETS))
from router import graph_data, relabelings, settings, transform
from validation import load_witness, replay, validate

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('witness.json')
witness = load_witness(path)
count, edges, gates, reference = validate(witness)
neighbors, distances = graph_data(count, edges)
colors = [-1] * count
colors[0] = 0
pending = deque([0])
while pending:
    node = pending.popleft()
    for adjacent in neighbors[node]:
        if colors[adjacent] < 0:
            colors[adjacent] = 1 - colors[node]
            pending.append(adjacent)
        assert colors[adjacent] != colors[node]
last_pairs = {tuple(sorted(gate)) for gate in gates[-3:]}
last_wires = set(wire for gate in gates[-3:] for wire in gate)
assert len(last_pairs) == 3 and len(last_wires) == 3
assert len(gates) % 4 == 3
assert len(settings()) == 62 and len(relabelings(count)) == 6
for name, logical, physical in relabelings(count):
    mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
    operations = []
    for operation in witness['route']:
        if operation[0] == 'swap':
            operations.append(['swap', physical[operation[1]], physical[operation[2]]])
        else:
            operations.append(['gate', operation[1], physical[operation[2]], physical[operation[3]]])
    final = [0] * count
    for wire in range(count):
        final[logical[wire]] = physical[witness['final_mapping'][wire]]
    assert replay(mapped_gates, count, mapped_edges, operations, final, initial) == reference
coverage = Counter(wire for gate in gates for wire in gate)
pairs = Counter(tuple(sorted(gate)) for gate in gates)
partners = [set() for _ in range(count)]
for first, second in gates:
    partners[first].add(second)
    partners[second].add(first)
report = {
    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'hardware': witness['hardware'],
    'gate_count': len(gates),
    'reference': reference,
    'coverage': [coverage[wire] for wire in range(count)],
    'distinct_partners': [len(values) for values in partners],
    'distinct_interactions': len(pairs),
    'maximum_pair_multiplicity': max(pairs.values()),
    'terminal_triangle': sorted(last_wires),
    'hardware_bipartite': True,
    'every_embedding_cut_retains_triangle': True,
    'reference_replays_passed': 6,
}
print(json.dumps(report, indent=2))
