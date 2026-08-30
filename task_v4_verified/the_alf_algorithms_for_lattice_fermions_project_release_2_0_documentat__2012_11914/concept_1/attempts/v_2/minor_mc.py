from minor_search import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--seed', type=int, default=224466)
    parser.add_argument('--eigen', action='store_true')
    parser.add_argument('--iterations', type=int, default=6000)
    parser.add_argument('--seconds', type=int, default=1200)
    args = parser.parse_args()
    random = np.random.default_rng(args.seed)
    started = time.monotonic()
    base = np.array(json.loads((ROOT / 'best_991122.json').read_text())['fields'], dtype=np.int8)
    allowed = np.arange(256) if args.all else np.flatnonzero(base.reshape(-1) == 1)
    updates = update_matrices(base)[:, allowed[:, None], allowed[None]]
    updates /= np.abs(np.diagonal(updates, axis1=-2, axis2=-1))[:, :, None]
    walkers = 256 if args.eigen else 1024
    best_field = np.array(json.loads((ROOT / 'best_775544.json').read_text())['fields'], dtype=np.int8)
    best_phase = float(evaluate(best_field[None])[0][0])
    temperatures = np.geomspace(0.00001, 0.04, walkers) if args.eigen else np.geomspace(0.002, 2.0, walkers)

    def objective(selected):
        minors = updates[:, selected[:, :, None], selected[:, None, :]]
        signs, logs = np.linalg.slogdet(minors)
        score = logs.min(axis=0)
        negative = signs.prod(axis=0) < 0
        score[negative] = -1000 - logs[:, negative].sum(axis=0)
        if args.eigen:
            eigenvalues = np.linalg.eigvals(minors)
            score = np.abs(eigenvalues).min(axis=(0, 2))
            score[negative] *= -1
        invalid = np.any(np.diff(np.sort(selected, axis=1), axis=1) == 0, axis=1)
        score[invalid] = np.inf
        negative[invalid] = False
        return score, negative

    for restart in range(100):
        counts = [8, 12, 16, 24, 32, 48, 64, 6, 10, 20] if args.all else [6, 7, 8, 9, 10, 12, 16, 20, 24, 32]
        count = counts[restart % len(counts)]
        positions = np.array([random.choice(len(allowed), count, replace=False) for walker in range(walkers)])
        seed_indices = np.flatnonzero(best_field.reshape(-1)[allowed] != base.reshape(-1)[allowed])
        for walker in range(walkers // 2):
            seed_selected = random.choice(seed_indices, min(count, len(seed_indices)), replace=False)
            extras = random.choice(np.setdiff1d(np.arange(len(allowed)), seed_selected), count - len(seed_selected), replace=False)
            positions[walker] = np.concatenate([seed_selected, extras])
        scores, negative = objective(positions)
        best = float(scores.min())
        for iteration in range(args.iterations):
            candidates = positions.copy()
            mutation_count = random.choice([1, 2, 3, 4, 8], p=[0.65, 0.20, 0.08, 0.05, 0.02])
            for mutation_index in range(mutation_count):
                selected_index = random.integers(count, size=walkers)
                candidates[np.arange(walkers), selected_index] = random.integers(len(allowed), size=walkers)
            proposed, negative = objective(candidates)
            for selected in candidates[negative]:
                candidate = base.copy()
                candidate.reshape(-1)[allowed[selected]] *= -1
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, f'found_minor_mc_{args.seed}.json')
                    save(candidate, 'witness.json')
                    print('FOUND', count, restart, iteration, round(time.monotonic() - started, 1), flush=True)
                    return
            minimum = float(proposed.min())
            if minimum < best - 1e-8:
                best = minimum
                candidate = base.copy()
                candidate.reshape(-1)[allowed[candidates[proposed.argmin()]]] *= -1
                phase_score = evaluate(candidate[None])[0][0]
                if phase_score < best_phase:
                    best_phase = phase_score
                    best_field = candidate.copy()
                    save(candidate, f'best_minor_mc_{args.seed}.json')
                    print('Best phase', best_phase, 'minor', best, 'count', count, restart, iteration, round(time.monotonic() - started, 1), flush=True)
            accepted = (proposed < scores) | (random.random(walkers) < np.exp(np.minimum(0, (scores - proposed) / temperatures)))
            positions[accepted] = candidates[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 200 == 199:
                elite = np.argsort(scores)[:16]
                destinations = random.choice(walkers, 16, replace=False)
                positions[destinations] = positions[elite]
                scores[destinations] = scores[elite]
            if iteration % 1000 == 0:
                print('Progress', restart, count, iteration, float(scores.min()), best_phase, round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > args.seconds:
                return


if __name__ == '__main__':
    main()
