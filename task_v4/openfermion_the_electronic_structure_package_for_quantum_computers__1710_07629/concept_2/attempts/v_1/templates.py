import argparse
import itertools
import time
from optimize import *


def natural_colorings(instance):
    size = instance['n_modes']
    neighbors = [set() for mode in range(size)]
    for first, second in instance['edges']:
        neighbors[first].add(second)
        neighbors[second].add(first)
    cycles = []
    def visit(path, used):
        if len(path) == size:
            if path[0] in neighbors[path[-1]] and path[1] < path[-1]:
                cycles.append(path)
            return
        for following in sorted(neighbors[path[-1]] - used):
            visit(path + [following], used | {following})
    visit([0], {0})
    all_edges = set(map(tuple, instance['edges']))
    results = []
    for cycle in cycles:
        cycle_edges = [tuple(sorted((cycle[index], cycle[(index + 1) % size]))) for index in range(size)]
        results.append([sorted(all_edges - set(cycle_edges)), cycle_edges[::2], cycle_edges[1::2]])
    if instance['family'] == 'ladder' and cycles:
        cycle = cycles[0]
        rungs = set(results[0][0])
        for edge in all_edges:
            if len(neighbors[edge[0]]) == 2 and len(neighbors[edge[1]]) == 2:
                rungs.add(edge)
        rails = all_edges - rungs
        first, second = [], []
        remaining = set(rails)
        while remaining:
            endpoint = next(mode for mode in range(size) if sum(mode in edge for edge in remaining) == 1)
            parity = 0
            while True:
                candidates = [edge for edge in remaining if endpoint in edge]
                if not candidates:
                    break
                edge = candidates[0]
                (first if parity == 0 else second).append(edge)
                remaining.remove(edge)
                endpoint = edge[1] if edge[0] == endpoint else edge[0]
                parity = 1 - parity
        results.append([sorted(rungs), first, second])
    return results


def remove_inactive(instance, edges):
    status = [int(mode in instance['initial_occupied']) for mode in range(instance['n_modes'])]
    kept = []
    for first, second in edges:
        if status[first] == status[second] and status[first] != -1:
            continue
        kept.append((first, second))
        status[first] = status[second] = -1
    return kept


def run(instance, maximum_layers=7, trials=2):
    random = np.random.default_rng(123)
    colors_list = natural_colorings(instance)
    started = time.monotonic()
    best = 100.0
    attempted = 0
    print(instance['id'], 'COLORINGS', len(colors_list), flush=True)
    for layers in range(5, maximum_layers + 1):
        words = [word for word in itertools.product(range(3), repeat=layers) if all(word[index] != word[index + 1] for index in range(layers - 1))]
        words.sort(key=lambda word: (sum(word[index] == word[index + 2] for index in range(layers - 2)), word))
        for colors in colors_list:
            for word in words:
                edges = remove_inactive(instance, [edge for color in word for edge in colors[color]])
                if len(edges) > instance['budgets']['max_gates']:
                    continue
                solver = Fit(instance, edges)
                for trial in range(trials):
                    parameters = random.normal(scale=0.5 if trial else 0.05, size=(len(edges), 2))
                    parameters, error = solver.solve(parameters, evaluations=180, tolerance=1e-11)
                    attempted += 1
                    if error < best:
                        best = error
                        print('BEST', instance['id'], attempted, layers, word, len(edges), error, 'time', round(time.monotonic() - started, 1), flush=True)
                        Path(instance['id'] + '_template_partial.json').write_text(json.dumps(pack(instance, edges, parameters)))
                    if error < 1e-8:
                        Path(instance['id'] + '_template.json').write_text(json.dumps(pack(instance, edges, parameters)))
                        print('SOLVED', instance['id'], flush=True)
                        return
    print('FAILED', instance['id'], attempted, best, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--layers', type=int, default=7)
    parser.add_argument('--trials', type=int, default=2)
    arguments = parser.parse_args()
    run(INSTANCES[arguments.index], arguments.layers, arguments.trials)
