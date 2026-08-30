from optimize import *
from itertools import combinations, islice


def main():
    random = np.random.default_rng(546347)
    started = time.monotonic()
    best = 2.0
    current = None
    for name in ['best_775544.json', 'best_cell8.json', 'best_temper.json', 'best_basin.json']:
        if (ROOT / name).exists():
            candidate = np.array(json.loads((ROOT / name).read_text())['fields'], dtype=np.int8)
            score = evaluate(candidate[None])[0][0]
            if score < best:
                best = score
                current = candidate.copy()
    print('Initial', best, flush=True)
    for restart in range(100):
        single_candidates = np.broadcast_to(current, (256, 16, 16)).copy()
        single_candidates.reshape(256, 256)[np.arange(256), np.arange(256)] *= -1
        single_scores = evaluate(single_candidates)[0]
        ordering = np.argsort(single_scores + random.uniform(0, 1e-9, 256))
        stages = [(1, range(256)), (2, range(256)), (3, ordering[:96]), (4, ordering[:64]), (3, range(256)), (4, ordering[:96])]
        improved = False
        for count, positions in stages:
            iterator = combinations(positions, count)
            tested = 0
            while True:
                mutations = list(islice(iterator, 512))
                if not mutations:
                    break
                candidates = np.broadcast_to(current, (len(mutations), 16, 16)).copy()
                flat = candidates.reshape(len(mutations), 256)
                for mutation_index in range(count):
                    flat[np.arange(len(mutations)), np.array(mutations)[:, mutation_index]] *= -1
                scores, signs = evaluate(candidates)
                for candidate in candidates[signs < 0]:
                    if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                        save(candidate, 'found_combinations.json')
                        save(candidate, 'witness.json')
                        print('FOUND', round(time.monotonic() - started, 1), flush=True)
                        return
                minimum = float(scores.min())
                if minimum < best - 1e-8:
                    best = minimum
                    current = candidates[scores.argmin()].copy()
                    save(current, 'best_combinations.json')
                    print('Best', best, 'count', count, 'restart', restart, 'tested', tested, 'seconds', round(time.monotonic() - started, 1), flush=True)
                    improved = True
                    break
                tested += len(mutations)
                if time.monotonic() - started > 1400:
                    return
            print('Stage', count, len(positions), tested, best, round(time.monotonic() - started, 1), flush=True)
            if improved:
                break
        if not improved:
            print('No improvement', restart, flush=True)
            return


if __name__ == '__main__':
    main()
