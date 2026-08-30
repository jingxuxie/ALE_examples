from arcs import *


def main():
    random = np.random.default_rng(245837)
    started = time.monotonic()
    walkers = 256
    best_field = np.array(json.loads((ROOT / 'best_775544.json').read_text())['fields'], dtype=np.int8)
    best_starts, best_lengths = parameters(best_field)
    best_starts = (best_starts - best_starts[0]) % 16
    best_parameters = np.concatenate([best_starts, best_lengths])
    best = float(evaluate(expand(best_starts[None], best_lengths[None]))[0][0])
    print('Initial', best, flush=True)
    for restart in range(100):
        population = random.integers(16, size=(walkers, 32))
        population[:walkers // 2] = best_parameters
        population[1:walkers // 2] += random.integers(-4, 5, size=(walkers // 2 - 1, 32))
        population[:, :16] %= 16
        population[:, :16] = (population[:, :16] - population[:, :1]) % 16
        population[:, 16:] = np.clip(population[:, 16:], 0, 16)
        scores = evaluate(expand(population[:, :16], population[:, 16:]))[0]
        for iteration in range(4000):
            first, second, third = random.integers(walkers, size=(3, walkers))
            difference = population[second] - population[third]
            difference[:, :16] = (difference[:, :16] + 8) % 16 - 8
            scale = random.choice([0.5, 0.8, 1.0, 1.2])
            if random.random() < 0.5:
                mutant = population[first] + np.rint(scale * difference).astype(int)
            else:
                towards = best_parameters[None] - population
                towards[:, :16] = (towards[:, :16] + 8) % 16 - 8
                mutant = population + np.rint(scale * (difference + towards)).astype(int)
            cross = random.random((walkers, 32)) < random.choice([0.2, 0.5, 0.8])
            cross[np.arange(walkers), random.integers(32, size=walkers)] = True
            candidates = np.where(cross, mutant, population)
            candidates[:, :16] %= 16
            candidates[:, :16] = (candidates[:, :16] - candidates[:, :1]) % 16
            candidates[:, 16:] = np.clip(candidates[:, 16:], 0, 16)
            fields = expand(candidates[:, :16], candidates[:, 16:])
            proposed, signs = evaluate(fields)
            for candidate in fields[signs < 0]:
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_arc_de.json')
                    save(candidate, 'witness.json')
                    print('FOUND', restart, iteration, round(time.monotonic() - started, 1), flush=True)
                    return
            minimum = float(proposed.min())
            if minimum < best - 1e-10:
                best = minimum
                best_parameters = candidates[proposed.argmin()].copy()
                save(fields[proposed.argmin()], 'best_arc_de.json')
                print('Best', best, restart, iteration, round(time.monotonic() - started, 1), flush=True)
            accepted = proposed <= scores + 1e-12
            population[accepted] = candidates[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 500 == 499:
                destinations = np.argsort(scores)[walkers // 2:]
                population[destinations] = best_parameters + random.integers(-4, 5, size=(len(destinations), 32))
                population[destinations, :16] %= 16
                population[destinations, :16] = (population[destinations, :16] - population[destinations, :1]) % 16
                population[destinations, 16:] = np.clip(population[destinations, 16:], 0, 16)
                scores[destinations] = evaluate(expand(population[destinations, :16], population[destinations, 16:]))[0]
            if iteration % 1000 == 0:
                print('Progress', restart, iteration, float(scores.min()), round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > 550:
                return


if __name__ == '__main__':
    main()
