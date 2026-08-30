import argparse
from collections import deque
from local_compile import *
from turnover import simplify


class RelaxedCompiler(LocalCompiler):
    def freeze(self, matrix, active):
        return tuple(mode for mode in active if min(abs(matrix[mode, mode]), abs(matrix[mode, mode] - 1)) > 1e-11)

    def options(self, matrix, active, extra=0):
        for size in range(2, len(active) + 1):
            subsets = self.subsets(active, size)
            if not len(subsets):
                continue
            blocks = matrix[subsets[:, :, None], subsets[:, None, :]]
            values, vectors = np.linalg.eigh(blocks)
            found = False
            for group_index, eigen_index in zip(*np.where((abs(values) < 1e-12) | (abs(values - 1) < 1e-12))):
                subset = subsets[group_index]
                vector = vectors[group_index, :, eigen_index]
                for root in subset:
                    result, gates = self.eliminate(matrix, subset, vector, root)
                    after = self.freeze(result, active)
                    if not self.split_valid(result, after):
                        continue
                    found = True
                    yield result, gates, after, root
            if found:
                break


def transport(instance):
    start = sum(1 << mode for mode in instance['initial_occupied'])
    previous = {start: None}
    distance = {start: 0}
    queue = deque([start])
    edge_bits = [(1 << first, 1 << second, first, second) for first, second in instance['edges']]
    while queue:
        state = queue.popleft()
        for first_bit, second_bit, first, second in edge_bits:
            if bool(state & first_bit) == bool(state & second_bit):
                continue
            following = state ^ first_bit ^ second_bit
            if following not in previous:
                previous[following] = state, (first, second, np.pi / 2, 0.0)
                distance[following] = distance[state] + 1
                queue.append(following)
    states = np.array(list(distance), dtype=np.int64)
    costs = np.array([distance[state] for state in states])
    return previous, states, costs


def run(instance, trials=200):
    previous, states, costs = transport(instance)
    compiler = RelaxedCompiler(instance)
    compiler.random_trees = True
    best = 0.0
    for trial in range(trials):
        matrix = target(instance)
        active = tuple(range(len(matrix)))
        gates = []
        while active:
            choices = []
            for result, addition, after, root in compiler.options(matrix, active):
                combined = gates + addition
                depth = len(schedule(combined, len(matrix)))
                occupied_bits = sum(1 << mode for mode in range(len(matrix)) if mode not in after and result[mode, mode].real > 0.5)
                fixed_bits = sum(1 << mode for mode in range(len(matrix)) if mode not in after)
                moving = int(np.min(costs[(states & fixed_bits) == occupied_bits]))
                degree = len(compiler.neighbors[root] & set(active))
                count = len(addition) / (len(active) - len(after))
                impurity = np.sum(result.diagonal().real * (1 - result.diagonal().real))
                if trial % 4 == 0:
                    score = (count + 0.5 * moving + compiler.random.exponential(0.25), degree, depth, impurity)
                elif trial % 4 == 1:
                    score = (count + 0.3 * moving + compiler.random.exponential(0.4), depth, degree, impurity)
                elif trial % 4 == 2:
                    score = (depth + moving * 0.5 + compiler.random.exponential(0.4), count, impurity)
                else:
                    score = (count + compiler.random.exponential(0.8), moving, degree, depth)
                choices.append((score, result, addition, after))
            if not choices:
                break
            _, matrix, addition, active = min(choices, key=lambda item: item[0])
            gates.extend(addition)
        if active:
            continue
        state = sum(1 << mode for mode in range(len(matrix)) if matrix[mode, mode].real > 0.5)
        preparation = []
        while previous[state] is not None:
            state, gate = previous[state]
            preparation.append(gate)
        preparation.reverse()
        preparation.extend((first, second, -theta, phi) for first, second, theta, phi in reversed(gates))
        preparation = simplify(preparation, instance)
        layers = schedule(preparation, len(matrix))
        resource = min(1, instance['budgets']['max_gates'] / max(1, len(preparation)), instance['budgets']['max_depth'] / max(1, len(layers)))
        if resource > best:
            best = resource
            Path(instance['id'] + '_relaxed.json').write_text(json.dumps(dict(id=instance['id'], layers=layers)))
            print('BEST', instance['id'], trial, len(preparation), len(layers), resource, flush=True)
            if resource == 1:
                print('SOLVED', instance['id'], flush=True)
                return
        if trial % 20 == 0:
            print('TRIAL', instance['id'], trial, best, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--trials', type=int, default=200)
    arguments = parser.parse_args()
    run(INSTANCES[arguments.index], arguments.trials)
