import random
import itertools
import sys
from policy import LocalModel, Policy, TOPOLOGIES

sys.path.insert(0, '/tmp/cascade-c3-g1-v1-re90q176/participant/input')
from simulator import component_edges


class Oracle:
    def __init__(self, source, echo):
        self.source = source
        self.echo = echo
        self.queries = 0

    def exchange(self, request):
        if request['op'] == 'start':
            assert request['source'] == self.source
            return {}
        assert request['op'] == 'parity'
        assert set(request) == {'op', 'mask'}
        encoded = request['mask']
        assert 1 <= len(encoded) <= 64
        mask = int(encoded, 16)
        assert mask.bit_count() <= 64
        self.queries += 1
        assert self.queries <= 8
        residual = (3 << (8 * self.source + 4)) | (3 << (8 * self.echo + 2))
        return {'value': (mask & residual).bit_count() & 1}


def main():
    generator = random.Random(924580)
    checks = 0
    for known_count in range(32):
        for repetition in range(8):
            source = generator.randrange(32)
            sites = [site for site in range(32) if site != source]
            generator.shuffle(sites)
            counts = [[0] * 32 for unused in range(32)]
            for site in sites[:known_count]:
                counts[source][site] = generator.randrange(1, 30)
            for echo in sites:
                oracle = Oracle(source, echo)
                policy = Policy(oracle.exchange)
                policy.counts = [row[:] for row in counts]
                policy.start(source)
                assert policy.full_echo(source) == echo
                checks += 1
    for repetition in range(100):
        source = generator.randrange(32)
        candidates = [site for site in range(32) if site != source]
        excluded = generator.sample(candidates, generator.randrange(2, 6))
        for echo in candidates:
            if echo in excluded:
                continue
            oracle = Oracle(source, echo)
            policy = Policy(oracle.exchange)
            for site in excluded:
                policy.counts[source][site] = 3
            policy.start(source)
            assert policy.query(excluded) == 0
            assert policy.full_echo(source, excluded) == echo
            checks += 1
    for size in (5, 6):
        model = LocalModel(list(range(size)))
        assert len(TOPOLOGIES[size]) == 70
        assert sum(family == 0 for family, edges in TOPOLOGIES[size]) == 10
        for probabilities in model.probs:
            for source, row in enumerate(probabilities):
                assert row[source] == 0
                assert abs(sum(row) - 1) < 1e-12
                assert all(probability >= 0 for probability in row)
        for source in range(size):
            for echo in range(32):
                if echo == source:
                    continue
                oracle = Oracle(source, echo)
                policy = Policy(oracle.exchange)
                policy.start(source)
                assert policy.restricted_echo(source, model.core) == (echo if echo in model.core else -1)
                checks += 1
    policy = Policy(None)
    first = LocalModel(list(range(6)))
    second = LocalModel(list(range(6, 12)))
    probabilities, marginals, adjusted = policy.joint(first, second)
    assert all(abs(probability - 1 / 3) < 1e-12 for probability in probabilities)
    assert all(abs(probability - 0.5) < 1e-12 for probability in marginals)
    first.scores = [0 if family == 0 else -1000 for family in first.models]
    first.cached_weights = None
    probabilities, marginals, adjusted = policy.joint(first, second)
    assert abs(probabilities[0] - 2 / 3) < 1e-12
    assert abs(probabilities[1] - 1 / 3) < 1e-12
    assert probabilities[2] == 0
    assert abs(marginals[1] - 1 / 3) < 1e-12
    for family, kind in enumerate('RS'):
        adjacency = [set() for unused in range(16)]
        for first, second in component_edges(kind):
            adjacency[first].add(second)
            adjacency[second].add(first)
        for neighbors in adjacency:
            for size in (5, 6):
                patterns = {frozenset(tuple(sorted(edge)) for edge in edges) for label, edges in TOPOLOGIES[size] if label == family}
                for core in itertools.combinations(sorted(neighbors), size):
                    edges = frozenset((first, second) for first, second in itertools.combinations(range(size), 2) if core[second] in adjacency[core[first]])
                    assert edges in patterns
    print('Passed', checks, 'decoder cases and all topology probability checks.')


if __name__ == '__main__':
    main()
