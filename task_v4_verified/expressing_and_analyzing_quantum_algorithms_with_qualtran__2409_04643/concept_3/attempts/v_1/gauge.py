import json
import math
import os
import random
import sys

from compact import unpack


def abstract_form(code, first, second, constant=1):
    return (constant if code & 1 else 0) ^ (first if code & 2 else 0) ^ (second if code & 4 else 0)


VARIANTS = []
for first_code in range(2, 8):
    for second_code in range(first_code + 1, 8):
        if first_code & 6 == second_code & 6:
            continue
        difference = (abstract_form(first_code, 10, 12, 15) & abstract_form(second_code, 10, 12, 15)) ^ 8
        constant = difference & 1
        shift_code = constant | ((((difference >> 1) & 1) ^ constant) << 1) | ((((difference >> 2) & 1) ^ constant) << 2)
        VARIANTS.append((first_code, second_code, shift_code))


def optimize(circuit, width, passes=20, seed=41, temperature=0):
    gate_count = len(circuit['gates'])
    expressions = [sum(1 << reference for reference in gate[key]) for gate in circuit['gates'] for key in ('left', 'right')]
    expressions += [sum(1 << reference for reference in output) for output in circuit['outputs']]
    initial = sum(expression.bit_count() for expression in expressions)
    generator = random.Random(seed)
    for iteration in range(passes):
        changed = False
        order = list(range(gate_count))
        if iteration or temperature:
            generator.shuffle(order)
        for gate in order:
            first, second = expressions[2 * gate:2 * gate + 2]
            reference = 1 << (width + 1 + gate)
            affected = [index for index in range(2 * gate + 2, len(expressions)) if expressions[index] & reference]
            old_cost = first.bit_count() + second.bit_count()
            best_delta, best = 0, None
            for first_code, second_code, shift_code in VARIANTS:
                new_first = abstract_form(first_code, first, second)
                new_second = abstract_form(second_code, first, second)
                shift = abstract_form(shift_code, first, second)
                delta = new_first.bit_count() + new_second.bit_count() - old_cost
                if shift:
                    delta += sum((expressions[index] ^ shift).bit_count() - expressions[index].bit_count() for index in affected)
                ranking = delta + (temperature * math.log(-math.log(generator.random())) if temperature and iteration == 0 else 0)
                if ranking < best_delta:
                    best_delta, best = ranking, (new_first, new_second, shift)
            if best is not None:
                new_first, new_second, shift = best
                expressions[2 * gate:2 * gate + 2] = [new_first, new_second]
                for index in affected:
                    expressions[index] ^= shift
                changed = True
        if not changed:
            break
    result = {'id': circuit['id'], 'gates': [{'left': unpack(expressions[2 * gate]), 'right': unpack(expressions[2 * gate + 1])} for gate in range(gate_count)], 'outputs': [unpack(expression) for expression in expressions[2 * gate_count:]]}
    print('gauge', circuit['id'], initial, sum(expression.bit_count() for expression in expressions), 'passes', iteration + 1, flush=True)
    return result


if __name__ == '__main__':
    sys.path.insert(0, os.environ['PART'] + '/workspace')
    from verify import check
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    instances = {instance['id']: instance for instance in suite['instances']}
    circuits = []
    for circuit in json.load(open('circuits.json'))['circuits']:
        instance = instances[circuit['id']]
        result = optimize(circuit, instance['n'])
        record = check(instance, result)
        assert record['exact']
        assert record['usage']['depth'] <= instance['caps']['depth']
        circuits.append(result)
    json.dump({'circuits': circuits}, open('circuits.json', 'w'))
