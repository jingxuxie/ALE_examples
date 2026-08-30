from optimize import *


def main():
    random = np.random.default_rng(774532)
    started = time.monotonic()
    best = 2.0
    best_field = None
    current = None
    current_score = 2.0
    masks = []
    for length in [1, 2, 3, 4, 6, 8]:
        for time_index in range(16):
            for site in range(16):
                mask = np.ones((16, 16), dtype=np.int8)
                for offset in range(length):
                    mask[(time_index + offset) % 16, site] = -1
                masks.append(mask)
        for time_index in range(16):
            for horizontal in range(2):
                for vertical in range(2):
                    mask = np.ones((16, 16), dtype=np.int8)
                    for offset in range(length):
                        for horizontal_offset in [0, 2]:
                            for vertical_offset in [0, 2]:
                                site = 4 * (horizontal + horizontal_offset) + vertical + vertical_offset
                                mask[(time_index + offset) % 16, site] = -1
                    masks.append(mask)
    masks = np.array(masks)
    for basin in range(20000):
        if basin % 20 == 0:
            for name in ['best_reduced.json', 'best_775544.json', 'best_phase_relaxed.json', 'best_basin.json']:
                if (ROOT / name).exists():
                    candidate = np.array(json.loads((ROOT / name).read_text())['fields'], dtype=np.int8)
                    candidate_score = evaluate(candidate[None])[0][0]
                    if candidate_score < best:
                        best = candidate_score
                        best_field = candidate.copy()
            current = best_field.copy()
            current_score = best
        trial = current.copy()
        if basin:
            if random.random() < 0.5:
                for mutation_index in range(random.integers(1, 6)):
                    trial *= masks[random.integers(len(masks))]
            else:
                trial.reshape(-1)[random.choice(256, random.integers(4, 32), replace=False)] *= -1
        trial_score = evaluate(trial[None])[0][0]
        for descent in range(100):
            candidates = trial[None] * masks
            shifted = np.broadcast_to(trial, (16 * 6, 16, 16)).copy()
            for site in range(16):
                for offset_index, offset in enumerate([-3, -2, -1, 1, 2, 3]):
                    shifted[site * 6 + offset_index, :, site] = np.roll(trial[:, site], offset)
            candidates = np.concatenate([candidates, shifted])
            scores, signs = evaluate(candidates)
            for candidate in candidates[signs < 0]:
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, 'found_basin.json')
                    save(candidate, 'witness.json')
                    print('FOUND', round(time.monotonic() - started, 1), flush=True)
                    return
            position = scores.argmin()
            if scores[position] >= trial_score - 1e-10:
                break
            trial = candidates[position].copy()
            trial_score = scores[position]
            if trial_score < best:
                best = trial_score
                best_field = trial.copy()
                save(best_field, 'best_basin.json')
                print('Best', best, 'basin', basin, 'descent', descent, 'seconds', round(time.monotonic() - started, 1), flush=True)
        temperature = [0.001, 0.003, 0.01, 0.03][basin // 20 % 4]
        if trial_score < current_score or random.random() < np.exp(min(0, (current_score - trial_score) / temperature)):
            current = trial.copy()
            current_score = trial_score
        if basin % 10 == 0:
            print('Progress', basin, float(current_score), float(best), round(time.monotonic() - started, 1), flush=True)
        if time.monotonic() - started > 2600:
            return


if __name__ == '__main__':
    main()
