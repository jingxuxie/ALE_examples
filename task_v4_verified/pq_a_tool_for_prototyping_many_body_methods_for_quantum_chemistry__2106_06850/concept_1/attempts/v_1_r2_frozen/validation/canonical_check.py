import itertools
import json
import random
from collections import defaultdict

from benchmark import REPORTS
from solve import canonical
from stress import permute, randomized_case


def naive(factors, boundary):
    groups = defaultdict(list)
    for name, axes in factors:
        groups[name].append(axes)
    names = sorted(groups)
    options = [itertools.permutations(groups[name]) for name in names]
    best = None
    for ordering in itertools.product(*options):
        labels = {}
        encoded = []
        for name, block in zip(names, ordering):
            for axes in block:
                converted = []
                for axis in axes:
                    if axis not in labels:
                        labels[axis] = len(labels)
                    converted.append(2 * labels[axis] + (axis in boundary))
                encoded.append((name, tuple(converted)))
        key = tuple(encoded)
        if best is None or key < best:
            best = key
    return best


def main():
    generator = random.Random(271971)
    forwards = {}
    backwards = {}
    checked = 0
    for iteration in range(30):
        case = randomized_case(generator)
        for term in case['terms'][:12]:
            for transformed in (term, permute(term, case['index_types'], generator)):
                factors = transformed['inputs']
                for mask in range(1, 1 << len(factors)):
                    selected = [factor for position, factor in enumerate(factors) if mask & (1 << position)]
                    inside = set().union(*(set(axes) for name, axes in selected))
                    outside = set(transformed['output'])
                    for position, (name, axes) in enumerate(factors):
                        if not mask & (1 << position):
                            outside.update(axes)
                    boundary = inside & outside
                    old_key = naive(selected, boundary)
                    new_key, axes = canonical(selected, boundary)
                    assert forwards.setdefault(old_key, new_key) == new_key
                    assert backwards.setdefault(new_key, old_key) == old_key
                    assert set(axes) == boundary
                    checked += 1
    result = {'checked_subnetworks': checked, 'distinct_networks': len(forwards), 'valid': True}
    (REPORTS / 'canonical_results.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
