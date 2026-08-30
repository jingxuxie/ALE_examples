from optimize import *
from itertools import combinations, islice


def update_matrices(fields):
    delta = MODEL['beta'] / 16
    coupling = np.arccosh(np.exp(2 * delta))
    kinetic = expm(-delta * KINETIC_MATRIX)
    updates = []
    for spin in [1, -1]:
        inverse_diagonal = np.exp(-spin * coupling * fields.reshape(-1) - delta * MODEL['chemical_potential'])
        matrix = np.diag(inverse_diagonal)
        for time_index in range(16):
            previous = (time_index - 1) % 16
            matrix[time_index * 16:(time_index + 1) * 16, previous * 16:(previous + 1) * 16] = kinetic * (1 if time_index == 0 else -1)
        difference = np.exp(spin * coupling * fields.reshape(-1) - delta * MODEL['chemical_potential']) - inverse_diagonal
        updates.append(np.eye(256) + difference[:, None] * np.linalg.inv(matrix))
    return np.array(updates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='best_775544.json')
    parser.add_argument('--defects', action='store_true')
    parser.add_argument('--seconds', type=int, default=1200)
    args = parser.parse_args()
    random = np.random.default_rng(626554)
    started = time.monotonic()
    base = np.array(json.loads((ROOT / args.base).read_text())['fields'], dtype=np.int8)
    updates = update_matrices(base)
    initial_sign, initial_log = evaluate(base[None])[1][0], None
    import sys
    sys.path.insert(0, str(PARTICIPANT / 'workspace'))
    from physics import weight_batch
    base_sign, base_log = weight_batch(base)
    for count in [1, 2, 4, 8, 16]:
        selected = random.choice(256, count, replace=False)
        candidate = base.copy()
        candidate.reshape(-1)[selected] *= -1
        signs, logs = np.linalg.slogdet(updates[:, selected[:, None], selected[None]])
        direct_sign, direct_log = weight_batch(candidate)
        print('Validation', count, signs.prod(), direct_sign[0] / base_sign[0], logs.sum(), direct_log[0] - base_log[0], flush=True)
        assert signs.prod() == direct_sign[0] / base_sign[0]
        assert abs(logs.sum() - (direct_log[0] - base_log[0])) < 1e-7
    single = np.diagonal(updates, axis1=-2, axis2=-1)
    normalized = updates / single[:, :, None]
    singles = np.broadcast_to(base, (256, 16, 16)).copy()
    singles.reshape(256, 256)[np.arange(256), np.arange(256)] *= -1
    single_scores = evaluate(singles)[0]
    ordering = np.argsort(single_scores + random.uniform(0, 1e-9, 256))
    if args.defects:
        allowed = np.flatnonzero(base.reshape(-1) == 1)
        ordering = np.array([position for position in ordering if position in allowed])
        stages = [(count, ordering[:32]) for count in range(4, 10)] + [(6, ordering[:64]), (7, ordering[:40]), (8, ordering[:40]), (10, ordering[:32]), (11, ordering[:32])]
    else:
        stages = [(2, range(256)), (3, range(256)), (4, range(256)), (5, ordering[:96]), (6, ordering[:64]), (8, ordering[:32])]
    for count, positions in stages:
        iterator = combinations(positions, count)
        tested = 0
        lowest = 1.0
        while True:
            selected = np.array(list(islice(iterator, 8192)), dtype=np.int64)
            if len(selected) == 0:
                break
            minors = updates[:, selected[:, :, None], selected[:, None, :]]
            signs, logs = np.linalg.slogdet(minors)
            sign_product = signs.prod(axis=0) * base_sign[0]
            for mutations in selected[sign_product < 0]:
                candidate = base.copy()
                candidate.reshape(-1)[mutations] *= -1
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_minors.json')
                    save(candidate, 'witness.json')
                    print('FOUND', mutations.tolist(), count, tested, round(time.monotonic() - started, 1), flush=True)
                    return
            tested += len(selected)
            if tested % (8192 * 1000) == 0:
                print('Progress', count, len(positions), tested, round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > args.seconds:
                return
        print('Stage', count, len(positions), tested, round(time.monotonic() - started, 1), flush=True)


if __name__ == '__main__':
    main()
