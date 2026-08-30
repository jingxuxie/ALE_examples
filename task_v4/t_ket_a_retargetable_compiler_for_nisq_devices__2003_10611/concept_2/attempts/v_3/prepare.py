import json
import random
import sys
from pathlib import Path

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/concept_2/adversary/generation_3/participant/input')
sys.path.insert(0, str(ASSETS))
from router import hardware, relabelings, settings

for graph in ('ring16', 'ladder16', 'grid16'):
    count, edges = hardware(graph)
    families = [family for family in relabelings(count) if family[0] != 'logical-47']
    with open(Path(__file__).parent / (graph + '.dat'), 'w') as output:
        print(len(edges), file=output)
        for first, second in edges:
            print(first, second, file=output)
        print(len(families), file=output)
        for name, logical, physical in families:
            print(*physical, file=output)
            mapped = [tuple(sorted((physical[first], physical[second]))) for first, second in edges]
            for tie in ('ascending', 'seeded', 'descending'):
                ordered = sorted(mapped)
                if tie == 'seeded':
                    random.Random(1729).shuffle(ordered)
                if tie == 'descending':
                    ordered.reverse()
                print(*(ordered.index(edge) for edge in mapped), file=output)
        policies = [setting for setting in settings() if setting['horizon']]
        print(len(policies), file=output)
        for setting in policies:
            print(setting['horizon'], setting['decay'], int(setting['mode'] == 'lexicographic'),
                  ('ascending', 'seeded', 'descending').index(setting['tie']), file=output)
