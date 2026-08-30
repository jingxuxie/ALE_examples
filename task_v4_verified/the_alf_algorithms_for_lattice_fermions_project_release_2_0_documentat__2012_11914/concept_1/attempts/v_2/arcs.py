from optimize import *


def expand(starts, lengths):
    return np.where((np.arange(16)[None, :, None] - starts[:, None]) % 16 < lengths[:, None], 1, -1).astype(np.int8)


def parameters(fields):
    starts = np.zeros(16, dtype=int)
    lengths = (fields == 1).sum(axis=0)
    for site in range(16):
        boundaries = np.flatnonzero((fields[:, site] == 1) & (np.roll(fields[:, site], 1) == -1))
        if len(boundaries):
            starts[site] = boundaries[0]
    return starts, lengths


def main():
    random = np.random.default_rng(371988)
    started = time.monotonic()
    walkers = 192
    best_field = np.array(json.loads((ROOT / 'best_775544.json').read_text())['fields'], dtype=np.int8)
    best_starts, best_lengths = parameters(best_field)
    best = float(evaluate(expand(best_starts[None], best_lengths[None]))[0][0])
    print('Initial', best, flush=True)
    temperatures = np.geomspace(0.0001, 0.06, walkers)
    for restart in range(100):
        starts = random.integers(16, size=(walkers, 16))
        lengths = random.integers(3, 14, size=(walkers, 16))
        starts[:walkers // 2] = best_starts
        lengths[:walkers // 2] = best_lengths
        for walker in range(1, walkers // 2):
            sites = random.choice(16, random.integers(1, 8), replace=False)
            starts[walker, sites] = (starts[walker, sites] + random.integers(-3, 4, len(sites))) % 16
            lengths[walker, sites] = np.clip(lengths[walker, sites] + random.integers(-3, 4, len(sites)), 0, 16)
        scores = evaluate(expand(starts, lengths))[0]
        for iteration in range(5000):
            proposed_starts = starts.copy()
            proposed_lengths = lengths.copy()
            if random.random() < 0.06:
                parents = random.choice(np.argsort(scores)[:walkers // 4], walkers)
                inherited = random.random((walkers, 16)) < 0.5
                proposed_starts[inherited] = starts[parents][inherited]
                proposed_lengths[inherited] = lengths[parents][inherited]
            else:
                count = random.choice([1, 2, 4, 8], p=[0.65, 0.23, 0.09, 0.03])
                for mutation_index in range(count):
                    sites = random.integers(16, size=walkers)
                    shifts = random.choice([-4, -3, -2, -1, 1, 2, 3, 4], size=walkers, p=[0.025, 0.025, 0.1, 0.35, 0.35, 0.1, 0.025, 0.025])
                    kind = random.integers(3)
                    if kind != 1:
                        proposed_starts[np.arange(walkers), sites] = (proposed_starts[np.arange(walkers), sites] + shifts) % 16
                    if kind != 0:
                        proposed_lengths[np.arange(walkers), sites] = np.clip(proposed_lengths[np.arange(walkers), sites] + (shifts if kind == 1 else -shifts), 0, 16)
            fields = expand(proposed_starts, proposed_lengths)
            proposed, signs = evaluate(fields)
            for candidate in fields[signs < 0]:
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_arcs.json')
                    save(candidate, 'witness.json')
                    print('FOUND', restart, iteration, round(time.monotonic() - started, 1), flush=True)
                    return
            minimum = float(proposed.min())
            if minimum < best - 1e-10:
                best = minimum
                position = proposed.argmin()
                best_starts = proposed_starts[position].copy()
                best_lengths = proposed_lengths[position].copy()
                save(fields[position], 'best_arcs.json')
                print('Best', best, restart, iteration, round(time.monotonic() - started, 1), flush=True)
            accepted = (proposed < scores) | (random.random(walkers) < np.exp(np.minimum(0, (scores - proposed) / temperatures)))
            starts[accepted] = proposed_starts[accepted]
            lengths[accepted] = proposed_lengths[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 100 == 99:
                elite = np.argsort(scores)[:8]
                destinations = random.choice(walkers, 8, replace=False)
                starts[destinations] = starts[elite]
                lengths[destinations] = lengths[elite]
                scores[destinations] = scores[elite]
            if iteration % 1000 == 0:
                print('Progress', restart, iteration, float(scores.min()), round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > 850:
                return


if __name__ == '__main__':
    main()
