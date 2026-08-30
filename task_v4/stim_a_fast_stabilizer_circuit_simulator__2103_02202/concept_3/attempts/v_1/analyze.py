import collections
import json
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_3/participant')
OUT = Path(__file__).resolve().parent


def extract_swaps(gates):
    following = [{} for _ in gates]
    previous = {}
    for index, (name, targets) in enumerate(gates):
        for qubit in targets:
            if qubit in previous:
                following[previous[qubit]][qubit] = index
            previous[qubit] = index
    removed = set()
    updated = []
    swaps = 0
    for index, (name, targets) in enumerate(gates):
        if index in removed:
            continue
        if name == 'CX':
            first, second = targets
            middle = following[index].get(first, -1)
            if middle >= 0 and following[index].get(second) == middle and gates[middle] == ('CX', (second, first)):
                last = following[middle].get(first, -1)
                if last >= 0 and following[middle].get(second) == last and gates[last] == (name, targets):
                    updated.append(('SWAP', targets))
                    removed.update((middle, last))
                    swaps += 1
                    continue
        updated.append((name, targets))
    return updated, swaps


def virtualize(gates):
    mapping = list(range(36))
    output = []
    for name, targets in gates:
        if name == 'SWAP':
            first, second = targets
            mapping[first], mapping[second] = mapping[second], mapping[first]
        else:
            output.append((name, tuple(mapping[qubit] for qubit in targets)))
    return output, mapping


def main():
    artifact = json.loads((ROOT / 'baseline/circuit.json').read_text())
    gates = [(gate['gate'], tuple(gate['targets'])) for layer in artifact['layers'] for gate in layer]
    for iteration in range(4):
        gates, count = extract_swaps(gates)
        gates, mapping = virtualize(gates)
        print('iteration', iteration, 'swaps', count, 'remaining', collections.Counter(name for name, _ in gates), 'mapping', mapping)
        edges = {tuple(sorted(edge)) for edge in json.loads((ROOT / 'input/constraints.json').read_text())['edges']}
        print('nonnative', sum(name == 'CX' and tuple(sorted(targets)) not in edges for name, targets in gates))
        (OUT / f'logical{iteration}.json').write_text(json.dumps({'gates': gates, 'mapping': mapping}))
        if not count:
            break
    for index, gate in enumerate(gates[:150]):
        print(index, gate)


if __name__ == '__main__':
    main()
