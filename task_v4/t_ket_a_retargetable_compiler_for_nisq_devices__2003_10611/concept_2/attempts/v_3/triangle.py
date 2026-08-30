import copy
import json
import sys
from pathlib import Path

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/concept_2/adversary/generation_3/participant/input')
sys.path.insert(0, str(ASSETS))
from router import hardware
from validation import InvalidWitness, validate

for graph in ('grid16', 'ladder16', 'ring16'):
    source = Path(graph + '_round1.json')
    witness = json.loads(source.read_text())
    count, edges = hardware(graph)
    directory = Path('triangle_' + graph)
    directory.mkdir(exist_ok=True)
    (directory / (graph + '.dat')).write_bytes(Path(graph + '.dat').read_bytes())
    occupants = [0] * count
    for wire, physical in enumerate(witness['final_mapping']):
        occupants[physical] = wire
    found = False
    for center in range(count):
        adjacent = [second if first == center else first for first, second in edges if center in (first, second)]
        for side in adjacent:
            for other in adjacent:
                if side == other:
                    continue
                candidate = copy.deepcopy(witness)
                first, second, third = occupants[center], occupants[side], occupants[other]
                index = len(candidate['gates'])
                candidate['gates'].extend([[first, third], [first, second], [second, third]])
                candidate['route'].extend([['gate', index, center, other], ['gate', index + 1, center, side],
                                           ['swap', center, side], ['gate', index + 2, center, other]])
                candidate['final_mapping'][first], candidate['final_mapping'][second] = side, center
                try:
                    costs = validate(candidate)[3]
                except InvalidWitness:
                    continue
                (directory / 'seed.json').write_text(json.dumps(candidate) + '\n')
                with open(directory / 'seed.ops', 'w') as output:
                    for operation in candidate['route']:
                        endpoints = operation[1:] if operation[0] == 'swap' else operation[2:]
                        print(int(operation[0] == 'swap'), edges.index(tuple(sorted(endpoints))), file=output)
                print(graph, costs, 'gates', len(candidate['gates']), 'triangle', [first, second, third], flush=True)
                found = True
                break
            if found:
                break
        if found:
            break
    if not found:
        raise RuntimeError('No valid triangle for ' + graph)
