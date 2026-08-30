import json
from pathlib import Path


output = Path(__file__).resolve().parent
deployment = json.loads(Path('/tmp/cascade-c2-v1-lrzw9x7v/participant/input/deployment.json').read_text())
artifact = output / 'witness.json'
errors = json.loads(artifact.read_text())['errors']
assert artifact.stat().st_size <= 65536
assert 1 <= len(errors) <= 24
assert all(type(position) is int and 0 <= position < deployment['n'] for position in errors)
assert len(errors) == len(set(errors))


def independent_replay(priority):
    remaining = set(errors)
    corrected = []
    blocks = []
    identifiers = {}
    boundaries = []
    initial_odd = 0

    def register(order, origin):
        members = frozenset(order)
        if members not in identifiers:
            identifiers[members] = len(blocks)
            blocks.append((tuple(order), members, origin))
        return identifiers[members]

    def odd(identifier):
        return len(blocks[identifier][1] & remaining) % 2

    def ranking(identifier):
        order, members, origin = blocks[identifier]
        if priority == 'earliest':
            return origin, len(order), identifier
        return len(order), origin, identifier

    for pass_index, specification in enumerate(deployment['passes']):
        permutation = specification['permutation']
        assert sorted(permutation) == list(range(deployment['n']))
        block_size = specification['block_size']
        for start in range(0, deployment['n'], block_size):
            identifier = register(permutation[start:start + block_size], pass_index)
            if pass_index == 0:
                initial_odd += odd(identifier)
        while True:
            choices = [identifier for identifier in range(len(blocks)) if odd(identifier)]
            if not choices:
                break
            selected = min(choices, key=ranking)
            while len(blocks[selected][0]) > 1:
                order, members, origin = blocks[selected]
                midpoint = len(order) // 2
                left = register(order[:midpoint], origin)
                right = register(order[midpoint:], origin)
                selected = left if odd(left) else right
            position = blocks[selected][0][0]
            assert position in remaining
            remaining.remove(position)
            corrected.append(position)
        assert len(remaining) >= 8
        boundaries.append({'pass': pass_index, 'residual_count': len(remaining), 'corrected_count': len(corrected)})
    assert initial_odd >= 6
    assert len(corrected) >= 6
    return {
        'priority': priority,
        'initial_odd': initial_odd,
        'corrected': sorted(corrected),
        'residual': sorted(remaining),
        'known_blocks': len(blocks),
        'pass_boundaries': boundaries,
    }


report = [independent_replay(priority) for priority in ('earliest', 'shortest')]
public_results = json.loads((output / 'validation.json').read_text())
for independent, public in zip(report, public_results):
    assert {key: independent[key] for key in public} == public
(output / 'independent_validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
