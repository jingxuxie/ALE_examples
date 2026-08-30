from reduced import *
from itertools import product


def compositions(total, count, minimum=1):
    if count == 1:
        if total >= minimum:
            yield (total,)
        return
    for first in range(minimum, total - minimum * (count - 1) + 1):
        for tail in compositions(total - first, count - 1, minimum):
            yield (first,) + tail


def schedules(count):
    tail = np.indices((16,) * (count - 1), dtype=np.int8).reshape(count - 1, -1).T
    sequences = np.concatenate([np.column_stack([np.full(len(tail), first, dtype=np.int8), tail]) for first in [0, 1, 3, 6]])
    sequences = sequences[np.all(sequences != np.roll(sequences, 1, axis=1), axis=1)]
    radix = 16 ** np.arange(count - 1, -1, -1, dtype=np.int64)
    codes = sequences @ radix
    canonical = np.ones(len(sequences), dtype=bool)
    for rotation in range(4):
        for reflection in range(2):
            mapping = []
            for site in range(4):
                horizontal, vertical = divmod(site, 2)
                if reflection:
                    horizontal = 1 - horizontal
                for step in range(rotation):
                    horizontal, vertical = vertical, 1 - horizontal
                mapping.append(2 * horizontal + vertical)
            lookup = np.array([sum(((state >> site) & 1) << mapping[site] for site in range(4)) for state in range(16)], dtype=np.int8)
            for inversion in [0, 15]:
                transformed = lookup[sequences] ^ inversion
                comparable = transformed[:, 0] == sequences[:, 0]
                canonical &= ~comparable | (codes <= transformed @ radix)
                reversed_sequence = transformed[:, [0] + list(range(count - 1, 0, -1))]
                canonical &= ~comparable | (codes <= reversed_sequence @ radix)
    return sequences[canonical]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--segments', type=int, default=4)
    parser.add_argument('--minimum', type=int, default=1)
    args = parser.parse_args()
    started = time.monotonic()
    state_fields = np.array([[1 if state & (1 << site) else -1 for site in range(4)] for state in range(16)], dtype=np.int8)
    matrices = np.empty((17, 16, 2, 4, 4))
    matrices[0] = np.eye(4)
    for state in range(16):
        for spin_index, spin in enumerate([1, -1]):
            factor = KINETIC * np.exp(spin * COUPLING * state_fields[state])[None]
            for length in range(1, 17):
                matrices[length, state, spin_index] = factor @ matrices[length - 1, state, spin_index]
    sequences = schedules(args.segments)
    lengths_list = sorted(compositions(16, args.segments, args.minimum), key=lambda lengths: sum(length * length for length in lengths))
    print('Sequences', len(sequences), 'lengths', len(lengths_list), 'seconds', round(time.monotonic() - started, 1), flush=True)
    best = 2.0
    for length_index, lengths in enumerate(lengths_list):
        for start in range(0, len(sequences), 16384):
            selected = sequences[start:start + 16384]
            products = np.broadcast_to(np.eye(4), (len(selected), 2, 4, 4)).copy()
            for phase, length in enumerate(lengths):
                products = matrices[length, selected[:, phase]] @ products
            trace_plus = np.trace(products[:, 0], axis1=-2, axis2=-1)
            trace_minus = np.trace(products[:, 1], axis1=-2, axis2=-1)
            determinant = np.exp(COUPLING * (state_fields[selected].sum(axis=2) * np.array(lengths)[None]).sum(axis=1))
            coefficient_two = (trace_plus ** 2 - np.einsum('bij,bji->b', products[:, 0], products[:, 0])) / 2
            coefficient_three = determinant * trace_minus
            scores = []
            for target in [FUGACITY, 1 / FUGACITY]:
                rest = target ** 2 + trace_plus * target + coefficient_three / target + determinant / target ** 2
                scores.append(1 + coefficient_two / rest)
            scores = np.array(scores).T
            signs = np.sign(scores).prod(axis=1)
            for sequence in selected[signs < 0]:
                reduced = np.repeat(state_fields[sequence], lengths, axis=0)
                candidate = reduced[:, MAPPING]
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_enumerated.json')
                    save(candidate, 'witness.json')
                    print('FOUND', sequence.tolist(), lengths, round(time.monotonic() - started, 1), flush=True)
                    return
            position = np.unravel_index(scores.argmin(), scores.shape)[0]
            score = scores[position].min()
            if score < best - 1e-9:
                best = score
                reduced = np.repeat(state_fields[selected[position]], lengths, axis=0)
                save(reduced[:, MAPPING], f'best_enumerated_{args.segments}.json')
                print('Best', best, selected[position].tolist(), lengths, round(time.monotonic() - started, 1), flush=True)
        if length_index % 20 == 0:
            print('Progress', length_index, best, round(time.monotonic() - started, 1), flush=True)
    print('DONE', best, round(time.monotonic() - started, 1), flush=True)


if __name__ == '__main__':
    main()
