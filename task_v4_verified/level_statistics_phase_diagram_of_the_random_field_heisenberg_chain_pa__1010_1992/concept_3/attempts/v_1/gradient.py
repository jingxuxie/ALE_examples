from search import *
from exact import hamiltonian, sector
from scipy.linalg import eigh
from scipy.optimize import minimize
from scipy.special import logsumexp

def profile_gradient(fields):
    energies, vectors = eigh(hamiltonian(fields), eigvals_only=False,
                             overwrite_a=True, check_finite=False, driver='evr')
    statistics = proxy_statistics(energies)
    weights = np.zeros(922)
    weights[308:614] -= 1 / 306
    for window in statistics['windows']:
        start = window['start']
        weights[start:start+126] += 1 / (3 * 126)
    gaps = np.diff(energies)
    left = gaps[:-1]
    right = gaps[1:]
    left_smaller = left <= right
    left_derivative = np.where(left_smaller, 1 / right, -right / left ** 2)
    right_derivative = np.where(left_smaller, -left / right ** 2, 1 / left)
    gap_derivative = np.zeros(923)
    gap_derivative[:-1] += weights * left_derivative
    gap_derivative[1:] += weights * right_derivative
    energy_derivative = np.zeros(924)
    energy_derivative[:-1] -= gap_derivative
    energy_derivative[1:] += gap_derivative
    density = (vectors * vectors) @ energy_derivative
    gradient = sector()[1].T @ density
    return statistics['difference'], gradient

class EvaluationLimit(Exception):
    pass

class Optimize:
    def __init__(self, executor, orientation, best, temperature, limit):
        self.executor = executor
        self.orientation = orientation
        self.best = best
        self.temperature = temperature
        self.evaluations = 0
        self.started = time.monotonic()
        self.passed = False
        self.limit = limit

    def __call__(self, raw_fields):
        if self.evaluations >= self.limit:
            raise EvaluationLimit()
        fields = raw_fields - np.mean(raw_fields)
        profiles = [fields] + [SCALES[family] * fields + OFFSETS[family, member]
                              for family in range(4) for member in range(8)]
        results = list(self.executor.map(profile_gradient, profiles))
        differences = self.orientation * np.array([result[0] for result in results])
        gradients = self.orientation * np.array([result[1] for result in results])
        gradients[1:] *= np.repeat(SCALES, 8)[:, None]
        gradients -= gradients.mean(axis=1)[:, None]
        member_values = differences[1:].reshape(4, 8)
        member_gradients = gradients[1:].reshape(4, 8, 12)
        family_means = member_values.mean(axis=1)
        family_gradients = member_gradients.mean(axis=1)
        coverage_indices = np.argsort(member_values, axis=1)[:, 2]
        coverage_values = member_values[np.arange(4), coverage_indices]
        coverage_gradients = member_gradients[np.arange(4), coverage_indices]
        core = np.mean(family_means)
        core_gradient = np.mean(family_gradients, axis=0)
        margins = np.concatenate(([core-0.060, differences[0]-0.055], family_means-0.050, coverage_values-0.025))
        margin_gradients = np.vstack((core_gradient, gradients[0], family_gradients, coverage_gradients))
        temperature = self.temperature
        score = -temperature * logsumexp(-margins / temperature) + 0.15 * core
        soft_weights = np.exp(-margins / temperature - logsumexp(-margins / temperature))
        score_gradient = soft_weights @ margin_gradients + 0.15 * core_gradient
        true_score = float(np.min(margins) + 0.15 * core)
        self.evaluations += 1
        if (true_score > self.best or np.min(margins) >= 0) and valid(fields):
            candidate = dict(fields=fields.tolist(), orientation=self.orientation, kind=-2)
            try:
                for profile in profiles[1:]:
                    validate_fields(profile, derived=True)
                candidate.update(score=true_score, margin=float(np.min(margins)),
                                 coverage=float(np.min(coverage_values)), core=float(core),
                                 worst=float(np.min(family_means)), base=float(differences[0]),
                                 passed=bool(np.min(margins) >= 0))
                if candidate['score'] > self.best:
                    self.best = candidate['score']
                    witness = dict(schema_version=1, fields=candidate['fields'], orientation=self.orientation)
                    Path('witness.json').write_text(json.dumps(witness, indent=2) + '\n')
                    Path('gradient_best.json').write_text(json.dumps(candidate, indent=2))
                    print('BEST', json.dumps({key:value for key,value in candidate.items() if key!='fields'}), 'evaluation', self.evaluations, 'seconds', time.monotonic()-self.started, flush=True)
                if candidate['passed']:
                    result = full_measure(candidate)
                    if result is not None and result[1]['pass']:
                        save_result(result[0], result[1], Path('.'), 'passing')
                        self.passed = True
            except ValueError:
                pass
        if self.evaluations % 10 == 0:
            print('evaluation', self.evaluations, 'score', true_score, 'core', core, 'margin', float(np.min(margins)), 'gradient_norm', np.linalg.norm(score_gradient), 'seconds', time.monotonic()-self.started, flush=True)
        if self.passed:
            raise StopIteration('passing witness found')
        return -float(score), -score_gradient

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=Path('finalists.json'))
    parser.add_argument('--starts', type=int, default=8)
    parser.add_argument('--iterations', type=int, default=80)
    parser.add_argument('--temperature', type=float, default=0.002)
    parser.add_argument('--radius', type=float, default=0.35)
    parser.add_argument('--evaluations', type=int, default=100)
    parser.add_argument('--check-gradient', action='store_true')
    args = parser.parse_args()
    if args.check_gradient:
        fields = np.random.default_rng(1).uniform(-2, 2, 12)
        fields -= fields.mean()
        value, gradient = profile_gradient(fields)
        numerical = []
        for site in range(12):
            delta = np.zeros(12)
            delta[site] = 1e-6
            plus = proxy_statistics(spectrum(fields+delta))['difference']
            minus = proxy_statistics(spectrum(fields-delta))['difference']
            numerical.append((plus-minus) / 2e-6)
        error = float(np.max(np.abs(gradient-numerical)))
        print('analytic_gradient', gradient, 'finite_difference', numerical, 'max_error', error, flush=True)
        assert error < 1e-5
        return
    rows = json.loads(args.input.read_text())
    if isinstance(rows, dict):
        rows = [rows]
    rows.sort(key=lambda item:item['score'], reverse=True)
    best = rows[0]['score']
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        for index, candidate in enumerate(rows[:args.starts]):
            print('START', index, candidate, flush=True)
            objective_function = Optimize(executor, candidate['orientation'], best, args.temperature, args.evaluations)
            fields = np.array(candidate['fields'])
            try:
                result = minimize(objective_function, fields, jac=True, method='L-BFGS-B',
                                  bounds=[(value-args.radius, value+args.radius) for value in fields],
                                  options=dict(maxiter=args.iterations, maxls=15, ftol=1e-12, gtol=1e-6, maxcor=8))
                print('END', index, result.message, result.fun, result.nit, flush=True)
            except StopIteration:
                print('PASS', flush=True)
                return
            except EvaluationLimit:
                print('END', index, 'evaluation limit', flush=True)
            best = max(best, objective_function.best)

if __name__ == '__main__':
    main()
