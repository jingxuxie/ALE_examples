from phase_relaxed import *
import phase_relaxed as phase_objective

CURRENT_BETA = MODEL['beta']


def set_beta(beta, chemical=1):
    global COUPLING, KINETIC, TARGETS, CURRENT_BETA
    CURRENT_BETA = beta
    COUPLING = np.arccosh(np.exp(beta / 8))
    KINETIC = expm(-beta / 16 * KINETIC_MATRIX)
    TARGETS = [np.exp(beta * chemical), np.exp(-beta * chemical)]


def objective(flat):
    fields = flat.reshape(16, 16)
    factors = KINETIC[None] * np.exp(COUPLING * fields)[:, None, :]
    prefixes = [np.eye(16)]
    for factor in factors:
        prefixes.append(factor @ prefixes[-1])
    eigenvalues, right = eig(prefixes[-1])
    radius = np.maximum(np.abs(eigenvalues), 1e-30)
    normalized = np.array([(eigenvalues + target) / (radius + target) for target in TARGETS])
    margins = normalized.prod(axis=1).real
    coefficient = np.zeros(16, dtype=complex)
    for selected in range(2):
        target = TARGETS[selected]
        target_coefficient = np.array([np.prod(np.delete(normalized[selected], position)) for position in range(16)]) / (target + radius)
        target_coefficient -= margins[selected] * eigenvalues.conj() / (radius * (target + radius))
        coefficient += margins[1 - selected] * target_coefficient
    sensitivity = (right * coefficient[None]) @ np.linalg.inv(right)
    gradient = np.empty((16, 16))
    backward = sensitivity
    for time_index in range(15, -1, -1):
        backward = backward @ factors[time_index]
        gradient[time_index] = COUPLING * np.einsum('ij,ji->i', prefixes[time_index], backward).real
    return float(margins.prod()), gradient.reshape(-1)


def main():
    random = np.random.default_rng(990050)
    started = time.monotonic()
    best_field = np.array(json.loads((ROOT / 'best_775544.json').read_text())['fields'], dtype=float)
    best = float(evaluate(best_field[None])[0][0])
    for restart in range(10000):
        groups = random.choice([4, 6, 8, 16])
        labels = np.minimum(np.arange(16) * groups // 16, groups - 1)
        current = random.choice([-1.0, 1.0], size=(groups, 16))[labels]
        if restart % 3 == 0:
            current = best_field.copy()
            current[random.random((16, 16)) < random.uniform(0.05, 0.3)] *= -1
        schedule = [(0.75, chemical) for chemical in [0.3, 0.5, 0.7, 0.9, 1.0]] if restart % 3 == 0 else [(beta, 1.0) for beta in ([1.2, 1.0, 0.85, 0.75] if restart % 2 else [0.82, 0.78, 0.76, 0.75])]
        for beta, chemical in schedule:
            set_beta(beta, chemical)
            result = minimize(objective, current.reshape(-1), jac=True, method='L-BFGS-B', bounds=[(-1, 1)] * 256, options={'maxiter': 250, 'ftol': 1e-11, 'gtol': 1e-8, 'maxls': 25})
            current = result.x.reshape(16, 16)
        result = minimize(phase_objective.objective, current.reshape(-1), jac=True, method='L-BFGS-B', bounds=[(-1, 1)] * 256, options={'maxiter': 250, 'ftol': 1e-11, 'gtol': 1e-8, 'maxls': 25})
        current = result.x.reshape(16, 16)
        candidates = np.where(random.random((256, 16, 16)) < (current[None] + 1) / 2, 1, -1).astype(np.int8)
        candidates[0] = np.where(current >= 0, 1, -1)
        scores, signs = evaluate(candidates)
        for candidate in candidates[signs < 0]:
            if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                save(candidate, 'found_homotopy.json')
                save(candidate, 'witness.json')
                print('FOUND', restart, round(time.monotonic() - started, 1), flush=True)
                return
        minimum = float(scores.min())
        if minimum < best - 1e-10:
            best = minimum
            best_field = candidates[scores.argmin()].copy()
            save(best_field, 'best_homotopy.json')
            print('Best', best, 'relaxed', result.fun, restart, round(time.monotonic() - started, 1), flush=True)
        if restart % 20 == 0:
            print('Progress', restart, result.fun, best, round(time.monotonic() - started, 1), flush=True)
        if time.monotonic() - started > 500:
            return


if __name__ == '__main__':
    main()
