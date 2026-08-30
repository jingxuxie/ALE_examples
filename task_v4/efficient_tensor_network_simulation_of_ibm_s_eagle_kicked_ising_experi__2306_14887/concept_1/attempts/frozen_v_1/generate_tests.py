import json
import random
import sys

import networkx as nx


def make(rows, columns, family, seed):
    rng = random.Random(seed)
    graph = nx.hexagonal_lattice_graph(rows, columns)
    labels = {vertex: index for index, vertex in enumerate(graph)}
    count = len(labels)
    edges = []
    for left, right in graph.edges():
        if family == 0:
            dimension = 16
        elif family == 1:
            dimension = 64 if left[0] != right[0] else 4
        else:
            dimension = rng.choice([4, 16, 64])
        edges.extend([dict(u=labels[left], v=count, dim=dimension),
                      dict(u=count, v=labels[right], dim=dimension)])
        count += 1
    permutation = list(range(count))
    rng.shuffle(permutation)
    for edge in edges:
        edge['u'] = permutation[edge['u']]
        edge['v'] = permutation[edge['v']]
    rng.shuffle(edges)
    return dict(n=count, edges=edges, memory_elements=2**24)


def suite(mode):
    if mode == 'large':
        shapes = [(3, 6), (5, 4), (5, 6)]
        return [make(rows, columns, family, 58291 + family + rows * 100 + columns)
                for family in range(3) for rows, columns in shapes]
    if mode == 'more':
        shapes = [(3, 3), (3, 4), (3, 5), (4, 5), (4, 6), (5, 5)]
        return [make(rows, columns, family, 65799 + rows * 100 + columns * 10 + family)
                for rows, columns in shapes for family in range(3)]
    if mode == 'stress':
        instances = []
        for rows, columns in [(3, 3), (5, 6)]:
            for dimension in [4, 64]:
                instance = make(rows, columns, 0, 67139)
                for edge in instance['edges']:
                    edge['dim'] = dimension
                instances.append(instance)
        for cap in [2**18, 2**20, 2**22]:
            instance = make(4, 5, 2, 1979)
            instance['memory_elements'] = cap
            instances.append(instance)
        return instances
    if mode == 'hard':
        return [suite('large')[2], suite('large')[8], suite('stress')[3]]
    raise ValueError('unknown test suite')


if __name__ == '__main__':
    mode = sys.argv[2] if len(sys.argv) > 2 else 'large'
    json.dump(suite(mode), open(sys.argv[1], 'w'))
