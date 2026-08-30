from optimize import *


def main():
    random = np.random.default_rng(849279)
    started = time.monotonic()
    best = 2.0
    walkers = 192
    for restart in range(100):
        segments = [4, 4, 4, 8, 6, 5][restart % 6]
        edges = np.rint(np.linspace(0, 16, segments + 1)).astype(int)
        labels = np.repeat(np.arange(segments), np.diff(edges))
        blocks = random.choice(np.array([-1, 1], dtype=np.int8), size=(walkers, segments, 16))
        scores = evaluate(blocks[:, labels])[0]
        temperatures = np.geomspace(0.0001, 0.035, walkers)
        for iteration in range(4000):
            candidates = blocks.copy()
            count = random.choice([1, 2, 3, 4, 8], p=[0.65, 0.20, 0.08, 0.05, 0.02])
            for mutation_index in range(count):
                positions = random.integers(segments * 16, size=walkers)
                candidates.reshape(walkers, segments * 16)[np.arange(walkers), positions] *= -1
            fields = candidates[:, labels]
            proposed, signs = evaluate(fields)
            for candidate in fields[signs < 0]:
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_blocks.json')
                    save(candidate, 'witness.json')
                    print('FOUND', round(time.monotonic() - started, 1), flush=True)
                    return
            minimum = float(proposed.min())
            if minimum < best:
                best = minimum
                save(fields[np.argmin(proposed)], 'best_blocks.json')
                print('Best', best, restart, segments, iteration, round(time.monotonic() - started, 1), flush=True)
            accepted = (proposed < scores) | (random.random(walkers) < np.exp(np.minimum(0, (scores - proposed) / temperatures)))
            blocks[accepted] = candidates[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 250 == 249:
                elite = np.argsort(scores)[:8]
                destinations = random.choice(walkers, 8, replace=False)
                blocks[destinations] = blocks[elite]
                scores[destinations] = scores[elite]
            if iteration % 1000 == 0:
                print('Progress', restart, segments, iteration, float(scores.min()), round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > 1000:
                return


if __name__ == '__main__':
    main()
