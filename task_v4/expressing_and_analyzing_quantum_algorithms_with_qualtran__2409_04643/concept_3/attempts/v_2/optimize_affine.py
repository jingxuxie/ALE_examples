import json
import random
import time
import sys
import os
from pathlib import Path
from compact import usage, SUITE

PATTERNS = {0: [], 2: [], 4: [], 7: []}
for first in range(2, 8):
    for second in range(first + 1, 8):
        if (first & 6) == (second & 6):
            continue
        truth = []
        for assignment in range(4):
            first_value = (first & 1) ^ ((first >> 1) & 1) * (assignment & 1) ^ ((first >> 2) & 1) * (assignment >> 1)
            second_value = (second & 1) ^ ((second >> 1) & 1) * (assignment & 1) ^ ((second >> 2) & 1) * (assignment >> 1)
            truth.append((first_value & second_value) ^ (assignment == 3))
        delta = truth[0] | ((truth[0] ^ truth[1]) << 1) | ((truth[0] ^ truth[2]) << 2)
        PATTERNS[delta].append((first, second))

def bits(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low

def optimize(circuit, width, seconds=20):
    count = len(circuit['gates'])
    expressions = [sum(1 << reference for reference in gate[side]) for gate in circuit['gates'] for side in ('left', 'right')]
    expressions.extend(sum(1 << reference for reference in output) for output in circuit['outputs'])
    users = [set() for _ in range(width + 1 + count)]
    for index, expression in enumerate(expressions):
        for reference in bits(expression):
            users[reference].add(index)
    depths = [0] * (width + 1)
    for gate in range(count):
        depths.append(1 + max((depths[reference] for reference in bits(expressions[2 * gate] | expressions[2 * gate + 1])), default=0))
    def update(index, expression):
        old = expressions[index]
        for reference in bits(old ^ expression):
            if (expression >> reference) & 1:
                users[reference].add(index)
            else:
                users[reference].remove(index)
        expressions[index] = expression
    randomizer = random.Random(72)
    started = time.monotonic()
    total = sum(expression.bit_count() for expression in expressions)
    best = expressions.copy()
    best_total = total
    iteration = 0
    while time.monotonic() - started < seconds:
        ordering = list(range(count))
        randomizer.shuffle(ordering)
        changes = 0
        for gate in ordering:
            left, right = expressions[2 * gate:2 * gate + 2]
            forms = [0, 1, left, left ^ 1, right, right ^ 1, left ^ right, left ^ right ^ 1]
            gate_users = list(users[width + 1 + gate])
            old_cost = left.bit_count() + right.bit_count()
            best_change = 0
            options = [(left, right, 0)]
            for delta, representations in PATTERNS.items():
                replacement = forms[delta]
                delta_cost = sum((expressions[index] ^ replacement).bit_count() - expressions[index].bit_count() for index in gate_users)
                for first, second in representations:
                    change = delta_cost + forms[first].bit_count() + forms[second].bit_count() - old_cost
                    if change < best_change:
                        best_change = change
                        options = [(forms[first], forms[second], replacement)]
                    elif change == best_change:
                        options.append((forms[first], forms[second], replacement))
            new_left, new_right, replacement = randomizer.choice(options)
            if (new_left, new_right, replacement) != (left, right, 0):
                changes += 1
                update(2 * gate, new_left)
                update(2 * gate + 1, new_right)
                if replacement:
                    for index in gate_users:
                        update(index, expressions[index] ^ replacement)
                total += best_change
        for gate in ordering:
            gate_users = list(users[width + 1 + gate])
            best_change = 0
            best_option = None
            for prior in range(gate):
                if depths[width + 1 + prior] > depths[width + 1 + gate]:
                    continue
                for side in (0, 1):
                    common = expressions[2 * gate + side]
                    other_index = 2 * gate + 1 - side
                    other = expressions[other_index]
                    for previous_side in (0, 1):
                        complement = common ^ expressions[2 * prior + previous_side]
                        if complement not in (0, 1):
                            continue
                        previous_other = expressions[2 * prior + 1 - previous_side]
                        replacement = (1 << (width + 1 + prior)) ^ (previous_other if complement else 0)
                        new_other = other ^ previous_other
                        change = new_other.bit_count() - other.bit_count()
                        change += sum((expressions[index] ^ replacement).bit_count() - expressions[index].bit_count() for index in gate_users)
                        if change < best_change:
                            best_change = change
                            best_option = other_index, new_other, replacement
            if best_option:
                other_index, new_other, replacement = best_option
                update(other_index, new_other)
                for index in gate_users:
                    update(index, expressions[index] ^ replacement)
                total += best_change
                changes += 1
        if total < best_total:
            best_total = total
            best = expressions.copy()
            print(circuit['id'], 'iteration', iteration, 'affine', total, flush=True)
        iteration += 1
        if not changes:
            break
        if iteration > 100 and total == best_total:
            break
    gates = [{'left': list(bits(best[2 * gate])), 'right': list(bits(best[2 * gate + 1]))} for gate in range(count)]
    outputs = [list(bits(expression)) for expression in best[2 * count:]]
    return {'id': circuit['id'], 'gates': gates, 'outputs': outputs}

if __name__ == '__main__':
    sys.path.insert(0, os.environ['ROOT'] + '/workspace')
    from verify import check
    data = json.loads(Path('circuits.json').read_text())
    for index, instance in enumerate(SUITE):
        candidate = optimize(data['circuits'][index], instance['n'], float(sys.argv[1]) if len(sys.argv) > 1 else 20)
        assert check(instance, candidate)['exact']
        assert usage(candidate, instance['n'])['depth'] <= instance['caps']['depth']
        data['circuits'][index] = candidate
        print(usage(data['circuits'][index], instance['n']), flush=True)
        Path('circuits.json').write_text(json.dumps(data, separators=(',', ':')))
