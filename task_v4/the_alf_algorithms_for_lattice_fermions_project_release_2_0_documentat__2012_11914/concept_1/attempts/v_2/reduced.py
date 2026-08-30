from optimize import *

MAPPING = np.array([(horizontal % 2) * 2 + vertical % 2 for horizontal in range(4) for vertical in range(4)])
REDUCED_KINETIC = np.array([[0, -2, -2, 0], [-2, 0, 0, -2], [-2, 0, 0, -2], [0, -2, -2, 0]], dtype=float)
DELTA = MODEL['beta'] / 16
COUPLING = np.arccosh(np.exp(2 * DELTA))
KINETIC = expm(-DELTA * REDUCED_KINETIC)
FUGACITY = np.exp(MODEL['beta'])


def reduced_evaluate(fields):
    products = np.broadcast_to(np.eye(4), (len(fields), 2, 4, 4)).copy()
    diagonals = np.exp(COUPLING * fields[:, :, None] * np.array([1, -1])[None, None, :, None])
    for time_index in range(16):
        products = KINETIC @ (diagonals[:, time_index, :, :, None] * products)
    trace_plus = np.trace(products[:, 0], axis1=-2, axis2=-1)
    trace_minus = np.trace(products[:, 1], axis1=-2, axis2=-1)
    determinant = np.exp(COUPLING * fields.sum(axis=(1, 2)))
    coefficient_two = (trace_plus ** 2 - np.einsum('bij,bji->b', products[:, 0], products[:, 0])) / 2
    coefficient_three = determinant * trace_minus
    scores = []
    for target in [FUGACITY, 1 / FUGACITY]:
        rest = target ** 2 + trace_plus * target + coefficient_three / target + determinant / target ** 2
        scores.append(1 + coefficient_two / rest)
    scores = np.array(scores).T
    return scores.min(axis=1), np.sign(scores).prod(axis=1)


def main():
    random = np.random.default_rng(377344)
    started = time.monotonic()
    walkers = 512
    best_field = np.array(json.loads((ROOT / 'best_991122.json').read_text())['fields'], dtype=np.int8)[:, [0, 1, 4, 5]]
    best = float(reduced_evaluate(best_field[None])[0][0])
    print('Initial', best, flush=True)
    for restart in range(100):
        fields = random.choice(np.array([-1, 1], dtype=np.int8), size=(walkers, 16, 4))
        fields[:walkers // 2] = best_field
        fields[:walkers // 2][random.random((walkers // 2, 16, 4)) < 0.1] *= -1
        fields[0] = best_field
        scores, signs = reduced_evaluate(fields)
        temperatures = np.geomspace(0.0001, 0.08, walkers)
        for iteration in range(8000):
            candidates = fields.copy()
            mutation_type = random.random()
            if mutation_type < 0.15:
                sites = random.integers(4, size=walkers)
                offsets = random.choice([-3, -2, -1, 1, 2, 3], size=walkers)
                for walker in range(walkers):
                    candidates[walker, :, sites[walker]] = np.roll(candidates[walker, :, sites[walker]], offsets[walker])
            elif mutation_type < 0.4:
                sites = random.integers(4, size=walkers)
                time_index = random.integers(16, size=walkers)
                for offset in range(random.integers(2, 9)):
                    candidates[np.arange(walkers), (time_index + offset) % 16, sites] *= -1
            else:
                for mutation_index in range(random.choice([1, 2, 4, 8], p=[0.65, 0.22, 0.10, 0.03])):
                    positions = random.integers(64, size=walkers)
                    candidates.reshape(walkers, 64)[np.arange(walkers), positions] *= -1
            proposed, signs = reduced_evaluate(candidates)
            for reduced in candidates[signs < 0]:
                candidate = reduced[:, MAPPING]
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_reduced.json')
                    save(candidate, 'witness.json')
                    print('FOUND', round(time.monotonic() - started, 1), flush=True)
                    return
            minimum = float(proposed.min())
            if minimum < best - 1e-10:
                best = minimum
                best_field = candidates[proposed.argmin()].copy()
                save(best_field[:, MAPPING], 'best_reduced.json')
                print('Best', best, restart, iteration, round(time.monotonic() - started, 1), flush=True)
            accepted = (proposed < scores) | (random.random(walkers) < np.exp(np.minimum(0, (scores - proposed) / temperatures)))
            fields[accepted] = candidates[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 100 == 99:
                elite = np.argsort(scores)[:16]
                destinations = random.choice(walkers, 16, replace=False)
                fields[destinations] = fields[elite]
                scores[destinations] = scores[elite]
            if iteration % 1000 == 0:
                print('Progress', restart, iteration, float(scores.min()), round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > 1800:
                return


if __name__ == '__main__':
    main()
