import json
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2')
OUT = ROOT / 'attempts/v_6'
model = json.loads((ROOT / 'participant/input/model.json').read_text())
columns = [int(value, 16) for value in model['columns']]
observable = model['observable']

def check(support):
    syndrome = 0
    logical = 0
    for fault in support:
        syndrome ^= columns[fault]
        logical ^= observable[fault]
    if 0 < len(support) <= 36 and syndrome == 0 and logical:
        (OUT / 'structured_witness.json').write_text(json.dumps({'faults': sorted(support)}))
        print('FOUND', sorted(support), flush=True)
        raise SystemExit

def kernel(ids):
    basis = {}
    dependencies = []
    for fault in ids:
        value = columns[fault]
        support = 1 << fault
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (value, support)
                break
            reduced, tracked = basis[pivot]
            value ^= reduced
            support ^= tracked
        if value == 0:
            dependencies.append(support)
    return dependencies

def check_kernel(ids):
    dependencies = kernel(ids)
    if len(dependencies) > 18:
        return
    state = 0
    for number in range(1, 1 << len(dependencies)):
        change = (number & -number).bit_length() - 1
        state ^= dependencies[change]
        if state.bit_count() <= 36:
            check([fault for fault in ids if (state >> fault) & 1])

marker = [(column >> 77) & 1 for column in columns]
print('marker block totals', [sum(marker[start:start+32]) for start in range(0, 512, 32)], flush=True)
check_kernel([fault for fault in range(512) if not marker[fault]])
orders = [list(range(512)), sorted(range(512), key=lambda fault: columns[fault].bit_count()), sorted(range(512), key=lambda fault: columns[fault]), sorted(range(512), key=lambda fault: (observable[fault], fault)), [fault for fault in range(512) if marker[fault]]]
for order_index, order in enumerate(orders):
    doubled = order + order
    for start in range(len(order)):
        check_kernel(doubled[start:start+180])
    print('completed order', order_index, flush=True)
for step in range(1, 512):
    for start in range(512):
        support = [(start + offset * step) % 512 for offset in range(36)]
        if len(set(support)) == 36:
            check(support)
print('completed arithmetic supports', flush=True)
