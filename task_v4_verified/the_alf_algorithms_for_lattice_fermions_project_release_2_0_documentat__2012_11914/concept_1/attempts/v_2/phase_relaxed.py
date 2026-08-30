from optimize import *
from scipy.linalg import eig
from scipy.optimize import minimize

DELTA = MODEL['beta'] / 16
COUPLING = np.arccosh(np.exp(2 * DELTA))
KINETIC = expm(-DELTA * KINETIC_MATRIX)
TARGETS = [np.exp(MODEL['beta']), np.exp(-MODEL['beta'])]
MAPPING = np.array([(horizontal % 2) * 2 + vertical % 2 for horizontal in range(4) for vertical in range(4)])


def objective(flat):
    fields = flat.reshape(16, 16)
    factors = KINETIC[None] * np.exp(COUPLING * fields)[:, None, :]
    prefixes = [np.eye(16)]
    for factor in factors:
        prefixes.append(factor @ prefixes[-1])
    eigenvalues, right = eig(prefixes[-1])
    radius = np.abs(eigenvalues)
    normalized = np.array([(eigenvalues + target) / (radius + target) for target in TARGETS])
    scores = normalized.prod(axis=1).real
    selected = scores.argmin()
    score = scores[selected]
    target = TARGETS[selected]
    factors_selected = normalized[selected]
    coefficient = np.array([np.prod(np.delete(factors_selected, position)) for position in range(16)]) / (target + radius)
    coefficient -= score * eigenvalues.conj() / (radius * (target + radius))
    sensitivity = (right * coefficient[None]) @ np.linalg.inv(right)
    gradient = np.empty((16, 16))
    backward = sensitivity
    for time_index in range(15, -1, -1):
        backward = backward @ factors[time_index]
        gradient[time_index] = COUPLING * np.einsum('ij,ji->i', prefixes[time_index], backward).real
    return float(score), gradient.reshape(-1)


def main():
    random = np.random.default_rng(912564)
    started = time.monotonic()
    initial = np.array(json.loads((ROOT / 'best_reduced.json').read_text())['fields'], dtype=float)
    value, gradient = objective(initial.reshape(-1))
    for position in random.choice(256, 3, replace=False):
        shifted = initial.copy().reshape(-1)
        shifted[position] += 1e-5
        print('Gradient', position, gradient[position], (objective(shifted)[0] - value) / 1e-5, flush=True)
    best = value
    relaxed_best = value
    best_field = initial.copy()
    current = initial.copy()
    for restart in range(20000):
        if restart % 20 == 0:
            for name in ['best_reduced.json', 'best_775544.json', 'best_basin.json', 'best_phase_relaxed.json']:
                if (ROOT / name).exists():
                    candidate = np.array(json.loads((ROOT / name).read_text())['fields'], dtype=float)
                    score = evaluate(candidate[None])[0][0]
                    if score < best:
                        best = score
                        best_field = candidate.copy()
            current = best_field.copy()
        trial = current.copy()
        if restart:
            mutation_type = random.random()
            if mutation_type < 0.4:
                reduced_mask = random.random((16, 4)) < random.uniform(0.02, 0.2)
                trial[reduced_mask[:, MAPPING]] *= -1
            elif mutation_type < 0.7:
                trial[random.random((16, 16)) < random.uniform(0.01, 0.2)] *= -1
            else:
                for site in random.choice(16, random.integers(1, 6), replace=False):
                    trial[:, site] = np.roll(trial[:, site], random.integers(-4, 5))
        result = minimize(objective, trial.reshape(-1), jac=True, method='L-BFGS-B', bounds=[(-1, 1)] * 256, options={'maxiter': 250, 'ftol': 1e-11, 'gtol': 1e-7, 'maxls': 30})
        relaxed = result.x.reshape(16, 16)
        if result.fun < relaxed_best - 1e-10:
            relaxed_best = result.fun
            (ROOT / 'phase_relaxed_best.json').write_text(json.dumps({'fields': relaxed.tolist()}) + '\n')
            print('Relaxed best', relaxed_best, restart, round(time.monotonic() - started, 1), flush=True)
        candidates = np.where(random.random((256, 16, 16)) < (relaxed[None] + 1) / 2, 1, -1).astype(np.int8)
        candidates[0] = np.where(relaxed >= 0, 1, -1)
        scores, signs = evaluate(candidates)
        for candidate in candidates[signs < 0]:
            if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                save(candidate, 'found_phase_relaxed.json')
                save(candidate, 'witness.json')
                print('FOUND', round(time.monotonic() - started, 1), flush=True)
                return
        position = scores.argmin()
        if scores[position] < best - 1e-10:
            best = scores[position]
            best_field = candidates[position].copy()
            save(best_field, 'best_phase_relaxed.json')
            print('Best', best, restart, round(time.monotonic() - started, 1), flush=True)
        current = relaxed if random.random() < 0.5 else candidates[position].astype(float)
        if restart % 50 == 0:
            print('Progress', restart, result.fun, best, round(time.monotonic() - started, 1), flush=True)
        if time.monotonic() - started > 1800:
            return


if __name__ == '__main__':
    main()
