from optimize import *

MAPPING = np.tile(np.arange(8), 2)
CELL_KINETIC = np.zeros((8, 8))
for horizontal in range(2):
    for vertical in range(4):
        source = horizontal * 4 + vertical
        CELL_KINETIC[source, (1 - horizontal) * 4 + vertical] = -2
        for offset in [-1, 1]:
            CELL_KINETIC[source, horizontal * 4 + (vertical + offset) % 4] = -1
COUPLING = np.arccosh(np.exp(MODEL['beta'] / 8))
KINETIC = expm(-MODEL['beta'] / 16 * CELL_KINETIC)


def objective(fields):
    products = np.broadcast_to(np.eye(8), (len(fields), 8, 8)).copy()
    diagonals = np.exp(COUPLING * fields)
    for time_index in range(16):
        products = KINETIC @ (diagonals[:, time_index, :, None] * products)
    eigenvalues = np.linalg.eigvals(products)
    margins = np.array([np.prod((eigenvalues + target) / (np.abs(eigenvalues) + target), axis=-1).real for target in [np.exp(MODEL['beta']), np.exp(-MODEL['beta'])]])
    return margins.min(axis=0), np.sign(margins).prod(axis=0)


def main():
    random = np.random.default_rng(619755)
    started = time.monotonic()
    walkers = 256
    best_field = np.array(json.loads((ROOT / 'best_775544.json').read_text())['fields'], dtype=np.int8)[:, :8]
    best = float(objective(best_field[None])[0][0])
    print('Initial', best, flush=True)
    for restart in range(100):
        groups = [16, 8, 4, 6][restart % 4]
        edges = np.rint(np.linspace(0, 16, groups + 1)).astype(int)
        labels = np.repeat(np.arange(groups), np.diff(edges))
        blocks = random.choice(np.array([-1, 1], dtype=np.int8), size=(walkers, groups, 8))
        blocks[:walkers // 2] = best_field[edges[:-1]]
        blocks[:walkers // 2][random.random((walkers // 2, groups, 8)) < 0.1] *= -1
        blocks[0] = best_field[edges[:-1]]
        scores, signs = objective(blocks[:, labels])
        temperatures = np.geomspace(0.0002, 0.08, walkers)
        for iteration in range(8000):
            candidates = blocks.copy()
            mutation_type = random.random()
            rows = np.arange(walkers)
            if mutation_type < 0.2:
                sites = random.integers(8, size=walkers)
                time_index = random.integers(groups, size=walkers)
                for offset in range(random.integers(1, min(8, groups) + 1)):
                    candidates[rows, (time_index + offset) % groups, sites] *= -1
            elif mutation_type < 0.35:
                sites = random.integers(8, size=walkers)
                time_index = random.integers(groups, size=walkers)
                for offset in range(random.integers(1, min(4, groups) + 1)):
                    candidates[rows, (time_index + offset) % groups, sites] *= -1
                    partners = sites // 4 * 4 + (sites % 4 + 2) % 4
                    candidates[rows, (time_index + offset) % groups, partners] *= -1
            elif mutation_type < 0.4:
                first = random.integers(groups, size=walkers)
                second = (first + random.choice([-1, 1], size=walkers)) % groups
                saved = candidates[rows, first].copy()
                candidates[rows, first] = candidates[rows, second]
                candidates[rows, second] = saved
            else:
                for mutation_index in range(random.choice([1, 2, 4, 8], p=[0.65, 0.22, 0.10, 0.03])):
                    positions = random.integers(groups * 8, size=walkers)
                    candidates.reshape(walkers, groups * 8)[rows, positions] *= -1
            fields = candidates[:, labels]
            proposed, signs = objective(fields)
            for cell in fields[signs < 0]:
                candidate = cell[:, MAPPING]
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_cell8.json')
                    save(candidate, 'witness.json')
                    print('FOUND', round(time.monotonic() - started, 1), flush=True)
                    return
            minimum = float(proposed.min())
            if minimum < best - 1e-10:
                best = minimum
                best_field = fields[proposed.argmin()].copy()
                save(best_field[:, MAPPING], 'best_cell8.json')
                print('Best', best, restart, groups, iteration, round(time.monotonic() - started, 1), flush=True)
            accepted = (proposed < scores) | (random.random(walkers) < np.exp(np.minimum(0, (scores - proposed) / temperatures)))
            blocks[accepted] = candidates[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 200 == 199:
                elite = np.argsort(scores)[:8]
                destinations = random.choice(walkers, 8, replace=False)
                blocks[destinations] = blocks[elite]
                scores[destinations] = scores[elite]
            if iteration % 1000 == 0:
                print('Progress', restart, groups, iteration, float(scores.min()), round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > 1500:
                return


if __name__ == '__main__':
    main()
