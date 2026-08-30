from optimize import *

BETAS = np.array([0.75, 0.78, 0.82, 0.88, 0.96, 1.08, 1.3, 1.6])
COUPLINGS = np.arccosh(np.exp(BETAS / 8))
KINETICS = np.array([expm(-beta / 16 * KINETIC_MATRIX) for beta in BETAS])


def objective(fields):
    products = np.broadcast_to(np.eye(16), (len(BETAS), fields.shape[1], 16, 16)).copy()
    diagonals = np.exp(COUPLINGS[:, None, None, None] * fields)
    for time_index in range(16):
        products = KINETICS[:, None] @ (diagonals[:, :, time_index, :, None] * products)
    eigenvalues = np.linalg.eigvals(products)
    margins = []
    for sign in [1, -1]:
        target = np.exp(sign * BETAS)[:, None, None]
        margins.append(np.prod((eigenvalues + target) / (np.abs(eigenvalues) + target), axis=-1).real)
    margins = np.array(margins)
    scores = margins.min(axis=0)
    scores = np.where(np.all(margins < 0, axis=0), -scores, scores)
    return scores, np.sign(margins).prod(axis=0)


def main():
    random = np.random.default_rng(1125479)
    started = time.monotonic()
    walkers = 48
    best = 1.0
    best_field = np.array(json.loads((ROOT / 'best_775544.json').read_text())['fields'], dtype=np.int8)
    for restart in range(100):
        fields = random.choice(np.array([-1, 1], dtype=np.int8), size=(len(BETAS), walkers, 16, 16))
        fields[:, :walkers // 2] = best_field
        fields[:, 1:walkers // 2][random.random((len(BETAS), walkers // 2 - 1, 16, 16)) < 0.05] *= -1
        scores, signs = objective(fields)
        temperatures = np.geomspace(0.0003, 0.12, walkers)[None]
        for iteration in range(12000):
            candidates = fields.copy()
            flat = candidates.reshape(-1, 16, 16)
            batch = len(flat)
            rows = np.arange(batch)
            mutation_type = random.random()
            if mutation_type < 0.2:
                sites = random.integers(4, size=batch)
                time_index = random.integers(16, size=batch)
                for offset in range(random.integers(1, 6)):
                    for horizontal_offset in [0, 2]:
                        for vertical_offset in [0, 2]:
                            positions = (sites // 2 + horizontal_offset) * 4 + sites % 2 + vertical_offset
                            flat[rows, (time_index + offset) % 16, positions] *= -1
            elif mutation_type < 0.35:
                sites = random.integers(16, size=batch)
                time_index = random.integers(16, size=batch)
                for offset in range(random.integers(2, 9)):
                    flat[rows, (time_index + offset) % 16, sites] *= -1
            elif mutation_type < 0.4:
                first = random.integers(16, size=batch)
                second = (first + random.choice([-2, -1, 1, 2], size=batch)) % 16
                saved = flat[rows, first].copy()
                flat[rows, first] = flat[rows, second]
                flat[rows, second] = saved
            else:
                for mutation_index in range(random.choice([1, 2, 4, 8, 16], p=[0.65, 0.2, 0.1, 0.04, 0.01])):
                    positions = random.integers(256, size=batch)
                    flat.reshape(batch, 256)[rows, positions] *= -1
            proposed, signs = objective(candidates)
            for candidate in candidates[0, signs[0] < 0]:
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_temper.json')
                    save(candidate, 'witness.json')
                    print('FOUND', round(time.monotonic() - started, 1), flush=True)
                    return
            minimum = float(proposed[0].min())
            if minimum < best - 1e-10:
                best = minimum
                best_field = candidates[0, proposed[0].argmin()].copy()
                save(best_field, 'best_temper.json')
                print('Best', best, restart, iteration, round(time.monotonic() - started, 1), flush=True)
            accepted = (proposed < scores) | (random.random(scores.shape) < np.exp(np.minimum(0, (scores - proposed) / temperatures)))
            fields[accepted] = candidates[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 30 == 29:
                offset = iteration // 30 % 2
                swapped = fields.copy()
                for level in range(offset, len(BETAS) - 1, 2):
                    swapped[level] = fields[level + 1]
                    swapped[level + 1] = fields[level]
                exchanged, _ = objective(swapped)
                for level in range(offset, len(BETAS) - 1, 2):
                    difference = scores[level] + scores[level + 1] - exchanged[level] - exchanged[level + 1]
                    accepted_swap = random.random(walkers) < np.exp(np.minimum(0, difference / temperatures[0]))
                    for selected_level in [level, level + 1]:
                        fields[selected_level, accepted_swap] = swapped[selected_level, accepted_swap]
                        scores[selected_level, accepted_swap] = exchanged[selected_level, accepted_swap]
            if iteration % 1000 == 0:
                print('Progress', restart, iteration, scores.min(axis=1).tolist(), round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > 1600:
                return


if __name__ == '__main__':
    main()
