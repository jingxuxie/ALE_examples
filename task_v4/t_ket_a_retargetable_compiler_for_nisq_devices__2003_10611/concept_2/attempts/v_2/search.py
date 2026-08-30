import argparse
import ctypes
import json
import math
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/concept_2/adversary/generation_2/participant')
sys.path.insert(0, str(ASSETS / 'input'))
from router import hardware, relabelings, route, settings, transform
from validation import validate, InvalidWitness


class Engine:
    def __init__(self, graph):
        self.graph = graph
        self.count, self.edges = hardware(graph)
        self.lib = ctypes.CDLL(str(Path(__file__).with_name('fast_router.so')))
        self.configs = []
        horizons, decays, modes, ranks, labels = [], [], [], [], []
        families = relabelings(16)
        seen = set()
        for family_name, logical, physical in families:
            if tuple(physical) in seen:
                continue
            seen.add(tuple(physical))
            mapped = sorted(tuple(sorted((physical[left], physical[right]))) for left, right in self.edges)
            for setting in settings()[:-1]:
                ranked = mapped[:]
                if setting['tie'] == 'descending':
                    ranked.reverse()
                elif setting['tie'] == 'seeded':
                    random.Random(1729).shuffle(ranked)
                rank = {edge: index for index, edge in enumerate(ranked)}
                ranks.extend(rank[tuple(sorted((physical[left], physical[right])))] for left, right in self.edges)
                labels.extend(physical)
                horizons.append(setting['horizon'])
                decays.append(setting['decay'])
                modes.append(int(setting['mode'] == 'lexicographic'))
                self.configs.append((family_name, logical, physical, setting))
        integers = lambda values: (ctypes.c_int * len(values))(*values)
        self.lib.initialize(len(self.edges), integers([node for edge in self.edges for node in edge]),
                            len(self.configs), integers(horizons),
                            (ctypes.c_double * len(decays))(*decays), integers(modes),
                            integers(ranks), integers(labels))
        self.lib.evaluate.restype = ctypes.c_int
        self.order = list(range(len(self.configs)))

    def evaluate(self, gates, cap=10000, reject_below=-1, order=None):
        order = self.order if order is None else order
        data = (ctypes.c_int * (2*len(gates)))(*(node for gate in gates for node in gate))
        indices = (ctypes.c_int * len(order))(*order)
        output = (ctypes.c_int * len(order))()
        used = self.lib.evaluate(len(gates), data, len(order), indices, cap, reject_below, output)
        results = [output[index] for index in range(used)]
        return results, order[:used]

    def differential(self, witness):
        counts, order = self.evaluate(witness['gates'])
        mismatches = []
        for count, index in zip(counts, order):
            family_name, logical, physical, setting = self.configs[index]
            gates, edges, initial = transform(witness['gates'], self.edges, logical, physical)
            expected = route(gates, 16, edges, initial, setting)['swaps']
            if count != expected:
                mismatches.append((family_name, setting['name'], count, expected))
        return mismatches


def materialize(engine, physical, swaps, generator=None, repair=False):
    occupants = list(range(16))
    previous = [-1] * 16
    coverage = [0] * 16
    partners = [set() for _ in range(16)]
    pair_counts = Counter()
    events = {}
    for slot, edge in sorted(swaps):
        events.setdefault(slot, []).append(edge)
    gates, operations = [], []
    physical = physical[:]
    for index, encoded in enumerate(physical):
        for swap_edge in events.get(index, []):
            left, right = engine.edges[swap_edge]
            occupants[left], occupants[right] = occupants[right], occupants[left]
            operations.append(['swap', left, right])
        def admissible(encoded):
            left, right = engine.edges[encoded//2]
            first, second = occupants[left], occupants[right]
            return (previous[first] != previous[second] or previous[first] == -1) and pair_counts[tuple(sorted((first, second)))] < 8
        if encoded < 0 or not admissible(encoded):
            if not repair:
                return None
            allowed = [candidate for candidate in range(2*len(engine.edges)) if admissible(candidate)]
            if not allowed:
                return None
            weights = []
            for candidate in allowed:
                left, right = engine.edges[candidate//2]
                weights.append(1/(1+coverage[occupants[left]]+coverage[occupants[right]])**2)
            encoded = generator.choices(allowed, weights=weights)[0]
            physical[index] = encoded
        left, right = engine.edges[encoded//2]
        if encoded % 2:
            left, right = right, left
        first, second = occupants[left], occupants[right]
        gates.append([first, second])
        operations.append(['gate', index, left, right])
        previous[first] = previous[second] = index
        coverage[first] += 1
        coverage[second] += 1
        partners[first].add(second)
        partners[second].add(first)
        pair_counts[tuple(sorted((first, second)))] += 1
    if min(coverage) < 4 or max(coverage) > min(40, (len(gates)+3)//4) or min(map(len, partners)) < 2 or len(pair_counts) < 16:
        return None
    reached, queue = {0}, [0]
    while queue:
        node = queue.pop()
        for other in partners[node] - reached:
            reached.add(other)
            queue.append(other)
    if len(reached) != 16:
        return None
    suffix_neighbors = [set() for _ in range(16)]
    for first, second in gates[24:]:
        suffix_neighbors[first].add(second)
        suffix_neighbors[second].add(first)
    maximum_degree = max(sum(node in edge for edge in engine.edges) for node in range(16))
    if max(map(len, suffix_neighbors)) <= maximum_degree:
        return None
    position = [0]*16
    for node, logical in enumerate(occupants):
        position[logical] = node
    witness = {'version': 1, 'hardware': engine.graph, 'gates': gates,
               'route': operations, 'final_mapping': position}
    return witness, physical


def random_candidate(engine, generator, gate_count, swap_count):
    for attempt in range(1000):
        style = generator.randrange(4)
        if style == 0:
            slots = [generator.randrange(gate_count) for _ in range(swap_count)]
        elif style == 1:
            slots = [0] * (swap_count-2) + [generator.randrange(25, gate_count) for _ in range(2)]
        elif style == 2:
            slots = [generator.randrange(gate_count//2) for _ in range(swap_count-1)] + [generator.randrange(25, gate_count)]
        else:
            boundary = generator.randrange(28, gate_count-10)
            slots = [0] * (swap_count//2) + [boundary] * (swap_count-swap_count//2)
        swaps = [(slot, generator.randrange(len(engine.edges))) for slot in slots]
        result = materialize(engine, [-1]*gate_count, swaps, generator, True)
        if result:
            witness, physical = result
            return witness, physical, swaps
    raise RuntimeError('initial generation failed')


def mutate(engine, physical, swaps, generator):
    physical, swaps = physical[:], swaps[:]
    count = len(physical)
    mode = generator.randrange(100)
    if mode < 48:
        changes = generator.choices([1, 2, 3, 5, 10], weights=[55, 25, 12, 6, 2])[0]
        for _ in range(changes):
            index = generator.randrange(count)
            physical[index] = generator.randrange(2*len(engine.edges))
    elif mode < 66:
        index = generator.randrange(len(swaps))
        slot, edge = swaps[index]
        swaps[index] = (slot, generator.randrange(len(engine.edges)))
    elif mode < 82:
        index = generator.randrange(len(swaps))
        slot, edge = swaps[index]
        if generator.random() < .8:
            slot = max(0, min(count-1, slot + generator.choice([-8, -4, -2, -1, 1, 2, 4, 8])))
        else:
            slot = generator.randrange(count)
        swaps[index] = (slot, edge)
    elif mode < 94:
        first = generator.randrange(count)
        second = max(0, min(count-1, first+generator.choice([-8, -3, -2, -1, 1, 2, 3, 8])))
        physical[first], physical[second] = physical[second], physical[first]
    else:
        first = generator.randrange(count)
        length = generator.randrange(2, 12)
        physical[first:first+length] = list(reversed(physical[first:first+length]))
    result = materialize(engine, physical, swaps, generator, True)
    if result:
        witness, physical = result
        return witness, physical, swaps
    return None


def fitness(counts):
    minimum = min(counts)
    return minimum + .8*(1-sum(math.exp(-(count-minimum)/3) for count in counts)/len(counts))


def run(arguments):
    engine = Engine(arguments.graph)
    generator = random.Random(arguments.seed)
    start = time.monotonic()
    deadline = start + arguments.seconds
    best = -1
    iteration = 0
    restarts = 0
    target = max(arguments.goal, math.ceil(max(2.5*arguments.swaps, arguments.swaps+16, 1.35*arguments.swaps+7*arguments.gates/60)))
    prefix = Path(arguments.prefix)
    elite = []
    if arguments.resume:
        state = json.loads(Path(arguments.resume).read_text())
        state['swaps'] = [tuple(event) for event in state['swaps']]
        seeded = materialize(engine, state['physical'], state['swaps'])
        if seeded is None:
            raise RuntimeError('invalid resume state')
        witness, physical = seeded
        counts, _ = engine.evaluate(witness['gates'], cap=target+15)
        elite.append((fitness(counts), (witness, physical, state['swaps'])))
    while time.monotonic() < deadline:
        if elite and generator.random() < .85:
            current = generator.choice(elite)[1]
            for _ in range(generator.randrange(1, 6)):
                mutated = mutate(engine, current[1], current[2], generator)
                if mutated:
                    current = mutated
        else:
            current = random_candidate(engine, generator, arguments.gates, arguments.swaps)
        counts, indices = engine.evaluate(current[0]['gates'], cap=target+15)
        current_score = fitness(counts)
        stall = 0
        restarts += 1
        for local_iteration in range(1000):
            if time.monotonic() >= deadline:
                break
            iteration += 1
            mutated = mutate(engine, current[1], current[2], generator)
            if mutated is None:
                continue
            threshold = math.floor(current_score)-1
            counts, indices = engine.evaluate(mutated[0]['gates'], cap=target+15, reject_below=threshold)
            if len(counts) < len(engine.configs):
                engine.order.remove(indices[-1])
                engine.order.insert(0, indices[-1])
                continue
            score = fitness(counts)
            engine.order = [index for _, index in sorted(zip(counts, indices))]
            temperature = .08 if local_iteration < 500 else .20
            if score > current_score or generator.random() < math.exp(min(0, (score-current_score)/temperature)):
                current, current_score = mutated, score
            if score > best:
                best = score
                validate(mutated[0])
                prefix.with_suffix('.json').write_text(json.dumps(mutated[0], separators=(',', ':'))+'\n')
                prefix.with_suffix('.state.json').write_text(json.dumps({'physical': mutated[1], 'swaps': mutated[2]}))
                summary = {'elapsed': round(time.monotonic()-start, 2), 'iterations': iteration,
                           'restarts': restarts, 'score': score, 'minimum': min(counts),
                           'target': target, 'mean': sum(counts)/len(counts)}
                prefix.with_suffix('.summary.json').write_text(json.dumps(summary))
                print(json.dumps(summary), flush=True)
                elite.append((score, mutated))
                elite.sort(key=lambda item: item[0], reverse=True)
                elite = elite[:12]
                stall = 0
            else:
                stall += 1
            if min(counts) >= target:
                print('TARGET REACHED', prefix, flush=True)
                return
            if stall > 700:
                break
    print('DONE', prefix, 'best', best, 'iterations', iteration, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--graph', default='ring16')
    parser.add_argument('--gates', type=int, default=80)
    parser.add_argument('--swaps', type=int, default=8)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('--prefix', default='candidate')
    parser.add_argument('--goal', type=int, default=0)
    parser.add_argument('--resume')
    parser.add_argument('--differential', action='store_true')
    arguments = parser.parse_args()
    if arguments.differential:
        witness = json.loads((ASSETS/'baseline/witness.json').read_text())
        started = time.monotonic()
        engine = Engine(witness['hardware'])
        print('MISMATCHES', engine.differential(witness), 'seconds', time.monotonic()-started, flush=True)
        witness = random_candidate(Engine('ring16'), random.Random(77), 80, 8)[0]
        engine = Engine('ring16')
        print('MISMATCHES RING', engine.differential(witness), 'seconds', time.monotonic()-started, flush=True)
    else:
        run(arguments)
