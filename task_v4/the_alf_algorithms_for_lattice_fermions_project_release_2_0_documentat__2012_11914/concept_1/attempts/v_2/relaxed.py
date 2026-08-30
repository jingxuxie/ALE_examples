from optimize import *
from scipy.linalg import eig
from scipy.optimize import minimize

DELTA = MODEL['beta'] / 16
COUPLING = np.arccosh(np.exp(2 * DELTA))
KINETIC = expm(-DELTA * KINETIC_MATRIX)


def objective(flat):
    fields = flat.reshape(16, 16)
    factors = KINETIC[None] * np.exp(COUPLING * fields)[:, None, :]
    product = np.eye(16)
    for factor in factors:
        product = factor @ product
    eigenvalues, left, right = eig(product, left=True, right=True)
    targets = np.array([np.exp(MODEL['beta']), np.exp(-MODEL['beta'])])
    all_distances = np.abs(eigenvalues[:, None] + targets) / (targets + np.abs(eigenvalues[:, None]))
    choices = all_distances.argmin(axis=1)
    distances = all_distances[np.arange(16), choices]
    position = distances.argmin()
    value = eigenvalues[position]
    target = targets[choices[position]]
    radius = abs(value)
    numerator = abs(value + target)
    coefficient = np.conj(value + target) / (max(1e-12, numerator) * (target + radius)) - numerator * np.conj(value) / (radius * (target + radius) ** 2)
    left_vector = left[:, position].conj()
    right_vector = right[:, position]
    left_vector /= left_vector @ right_vector
    forward = [right_vector]
    for factor in factors:
        forward.append(factor @ forward[-1])
    gradient = np.empty((16, 16))
    backward = left_vector
    for time_index in range(15, -1, -1):
        backward = backward @ factors[time_index]
        derivative = COUPLING * backward * forward[time_index]
        gradient[time_index] = np.real(coefficient * derivative)
    return float(distances[position]), gradient.reshape(-1)


def main():
    random = np.random.default_rng(387123)
    started = time.monotonic()
    best = 2.0
    relaxed_best = 2.0
    initial = np.array(json.loads((ROOT / 'best_991122.json').read_text())['fields'], dtype=float)
    value, gradient = objective(initial.reshape(-1))
    for position in random.choice(256, 3, replace=False):
        shifted = initial.copy().reshape(-1)
        shifted[position] += 1e-5
        print('Gradient', position, gradient[position], (objective(shifted)[0] - value) / 1e-5, flush=True)
    current = initial.copy()
    best_field = initial.copy()
    for restart in range(20000):
        if restart % 10 == 0:
            for name in ['best_blocks.json', 'best_basin.json', 'best_991122.json', 'best_relaxed.json']:
                if (ROOT / name).exists():
                    candidate = np.array(json.loads((ROOT / name).read_text())['fields'], dtype=float)
                    score = evaluate(candidate[None])[0][0]
                    if score < best:
                        best = score
                        best_field = candidate.copy()
            current = best_field.copy()
        trial = current.copy()
        if restart:
            if random.random() < 0.5:
                trial[random.random((16, 16)) < random.uniform(0.01, 0.15)] *= -1
            else:
                for site in random.choice(16, random.integers(1, 6), replace=False):
                    trial[:, site] = np.roll(trial[:, site], random.integers(-4, 5))
        result = minimize(objective, trial.reshape(-1), jac=True, method='L-BFGS-B', bounds=[(-1, 1)] * 256, options={'maxiter': 250, 'ftol': 1e-10, 'gtol': 1e-7, 'maxls': 30})
        relaxed = result.x.reshape(16, 16)
        if result.fun < relaxed_best:
            relaxed_best = result.fun
            (ROOT / 'relaxed_best.json').write_text(json.dumps({'fields': relaxed.tolist()}) + '\n')
            print('Relaxed best', relaxed_best, restart, round(time.monotonic() - started, 1), flush=True)
        candidates = np.where(random.random((256, 16, 16)) < (relaxed[None] + 1) / 2, 1, -1).astype(np.int8)
        candidates[0] = np.where(relaxed >= 0, 1, -1)
        scores, signs = evaluate(candidates)
        for candidate in candidates[signs < 0]:
            if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                save(candidate, 'found_relaxed.json')
                save(candidate, 'witness.json')
                print('FOUND', round(time.monotonic() - started, 1), flush=True)
                return
        position = scores.argmin()
        if scores[position] < best:
            best = scores[position]
            best_field = candidates[position].copy()
            save(best_field, 'best_relaxed.json')
            print('Best', best, restart, round(time.monotonic() - started, 1), flush=True)
        current = relaxed if random.random() < 0.5 else candidates[position].astype(float)
        if restart % 50 == 0:
            print('Progress', restart, result.fun, best, round(time.monotonic() - started, 1), flush=True)
        if time.monotonic() - started > 2400:
            return


if __name__ == '__main__':
    main()
