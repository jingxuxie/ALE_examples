from optimize import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default=str(ROOT / 'baseline/design.json'))
    parser.add_argument('--output', default='search_best.json')
    parser.add_argument('--passes', type=int, default=12)
    parser.add_argument('--seed', type=int, default=17482)
    parser.add_argument('--weight', type=float, default=3.0)
    parser.add_argument('--samples', type=int, default=8)
    parser.add_argument('--coherence', type=float, default=1.0)
    parser.add_argument('--relative', type=float, default=0.0)
    parser.add_argument('--augment', action='store_true')
    parser.add_argument('--tail', type=float, default=0.0)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    training = np.load('training.npz')
    features = np.concatenate([DATA['features'], training['features']])
    families = np.concatenate([DATA['families'], training['families']])
    if args.augment:
        additional = np.load('validation.npz')
        features = np.concatenate([features, additional['features']])
        families = np.concatenate([families, additional['families']])
    base_intact, base_loss = profile(features, np.flatnonzero(BASELINE), BASELINE[BASELINE > 0])
    scale = np.array([base_intact[families == family].mean() for family in families])
    weights = 1 / scale
    weights *= (base_intact / base_loss) ** args.relative
    weights[families == 'long_coherence'] *= args.coherence
    weights /= weights.sum()
    def make_objective(selected_features, selected_weights, selected_base_loss):
        if args.tail:
            return TailObjective(selected_features, selected_weights, args.weight, 0.08, selected_base_loss, args.tail)
        return Objective(selected_features, selected_weights, args.weight, 0.15)

    objective = make_objective(features, weights, base_loss)
    initial = np.array(json.loads(Path(args.start).read_text())['batches'])
    support = np.flatnonzero(initial)
    batches, value = objective.allocate(support, initial[support])
    print('initial', value, flush=True)
    report(features, families, support, batches)
    started = time.time()
    for pass_index in range(args.passes):
        selected = np.concatenate([rng.choice(np.flatnonzero(families == family), args.samples, replace=False) for family in FAMILIES])
        sub_weights = weights[selected] / weights[selected].sum()
        screening = make_objective(features[selected], sub_weights, base_loss[selected])
        accepted = 0
        for position in rng.permutation(len(support)):
            remaining = BUDGET - COSTS[support] @ batches + COSTS[support[position]] * batches[position]
            best = screening.value(support, batches)
            options = []
            trial_support = support.copy()
            trial_batches = batches.copy()
            for candidate in rng.permutation(len(CANDIDATES)):
                if candidate in support:
                    continue
                trial_support[position] = candidate
                trial_batches[position] = min(48, remaining / COSTS[candidate])
                if trial_batches[position] < 0.5:
                    continue
                candidate_value = screening.value(trial_support, trial_batches)
                if candidate_value < best:
                    options.append((candidate_value, candidate, trial_batches[position]))
            options.sort()
            for candidate_value, candidate, candidate_batch in options[:3]:
                trial_support[position] = candidate
                trial_batches = batches.copy()
                trial_batches[position] = candidate_batch
                full_value = objective.value(trial_support, trial_batches)
                if full_value > value * 1.02:
                    continue
                new_batches, new_value = objective.allocate(trial_support, trial_batches, maxiter=60)
                if new_value < value - 1e-4:
                    print('swap', pass_index, position, support[position], candidate,
                          round(value, 5), round(new_value, 5), 'time', round(time.time()-started, 1), flush=True)
                    support = trial_support.copy()
                    batches = new_batches
                    value = new_value
                    accepted += 1
                    rounded = integerize(objective, support, batches)
                    save(support, rounded, args.output)
                    np.savez(args.output + '.npz', support=support, batches=batches, value=value)
                    break
        print('pass', pass_index, 'accepted', accepted, 'value', value, 'elapsed', time.time()-started, flush=True)
        report(features, families, support, batches)
    rounded = integerize(objective, support, batches)
    save(support, rounded, args.output)
    report(features, families, support, rounded)


if __name__ == '__main__':
    main()
