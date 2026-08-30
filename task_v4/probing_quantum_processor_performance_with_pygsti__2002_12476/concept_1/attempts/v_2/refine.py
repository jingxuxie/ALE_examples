from optimize import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='robust_best.json')
    parser.add_argument('--output', default='refined')
    args = parser.parse_args()
    data = [DATA, np.load('training.npz'), np.load('validation.npz')]
    features = np.concatenate([item['features'] for item in data])
    families = np.concatenate([item['families'] for item in data])
    baseline_intact, baseline_loss = profile(features, np.flatnonzero(BASELINE), BASELINE[BASELINE > 0])
    initial = np.array(json.loads(Path(args.start).read_text())['batches'])
    support = np.flatnonzero(initial)
    rows = features[:, support]
    objective = Objective(features, intact_weight=0, temperature=.06)
    costs = COSTS[support]

    def intact_value_gradient(batches):
        information = rows.transpose(0, 2, 1) @ (rows * (64 * batches)[None, :, None]) + np.eye(14) * 1e-10
        covariance = np.linalg.inv(information)
        intact = np.trace(covariance[:, :12, :12], axis1=1, axis2=2).mean()
        gradient = -64 * np.sum((rows @ covariance[:, :, :12]) ** 2, axis=-1).mean(axis=0)
        return intact, gradient

    for ratio in [1.06, 1.10, 1.14]:
        limit = ratio * baseline_intact.mean()
        result = minimize(lambda batches: objective.fun(batches, support), initial[support].astype(float), jac=True,
                          method='SLSQP', bounds=[(1, 48)] * len(support),
                          constraints=[{'type': 'ineq', 'fun': lambda batches: (BUDGET-costs@batches)/10000,
                                        'jac': lambda batches: -costs/10000},
                                       {'type': 'ineq', 'fun': lambda batches: limit-intact_value_gradient(batches)[0],
                                        'jac': lambda batches: -intact_value_gradient(batches)[1]}],
                          options={'maxiter': 200, 'ftol': 1e-7})
        rounded = integerize(objective, support, result.x)
        filename = f'{args.output}_{ratio:.2f}.json'
        save(support, rounded, filename)
        print(filename, result.success, result.message, flush=True)
        report(features, families, support, rounded)


if __name__ == '__main__':
    main()
