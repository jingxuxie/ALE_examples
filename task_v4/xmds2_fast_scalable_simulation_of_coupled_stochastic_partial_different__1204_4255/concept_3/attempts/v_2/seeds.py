from optimize import *
from scipy.special import betainc

times = np.linspace(0, 8, 801)
basis = BSpline(KNOTS, np.eye(25), 3)(times)
values = FIXED.copy()
fraction = np.clip((times - 3.1) / 4.9, 0, 1)
desired = betainc(5, 5, fraction)
acceleration = 2520 * fraction ** 3 * (1 - fraction) ** 3 * (1 - 2 * fraction) / 4.9 ** 2
for channel_index, distance in [(0, 1), (1, 2.2)]:
    values[channel_index, 3:-3] = np.linalg.lstsq(basis[:, 3:-3], distance * (desired + acceleration) - basis @ values[channel_index], rcond=None)[0]
values[5] = 1
values[2, 3:12] = [1.25, 2.5, 2.8, 2.8, 2.8, 2.8, 2.8, 2.5, 1.25]
values[2] *= (2.5 * np.pi) / (np.sum(values[2]) * 8 / 22)
vector = values[:, 3:-3].ravel()
bounds, conditions = constraints()
result = minimize(lambda current: (np.sum((current - vector) ** 2), 2 * (current - vector)), vector, jac=True, method='SLSQP', bounds=bounds, constraints=conditions, options={'maxiter': 200, 'ftol': 1e-12})
write('echo_seed.json', result.x)
fc.validate_artifact(artifact(result.x), PROTOCOL)
cases = cases_for('broad')
Path('compact_cases.json').write_text(json.dumps(cases[:5] + cases[9:13] + cases[17:21], indent=2))
values[2] = 0
values[2, 3:9] = [-1.2, -2.6, -2.8, -2.8, -2.6, -1.2]
values[2] *= (-1.5 * np.pi) / (np.sum(values[2]) * 8 / 22)
fraction = np.clip((times - 2.7) / 5.3, 0, 1)
desired = betainc(5, 5, fraction)
acceleration = 2520 * fraction ** 3 * (1 - fraction) ** 3 * (1 - 2 * fraction) / 5.3 ** 2
for channel_index, distance in [(0, 1), (1, 2.2)]:
    values[channel_index, 3:-3] = np.linalg.lstsq(basis[:, 3:-3], distance * (desired + acceleration) - basis @ values[channel_index], rcond=None)[0]
vector = values[:, 3:-3].ravel()
result = minimize(lambda current: (np.sum((current - vector) ** 2), 2 * (current - vector)), vector, jac=True, method='SLSQP', bounds=bounds, constraints=conditions, options={'maxiter': 200, 'ftol': 1e-12})
write('negative_seed.json', result.x)
fc.validate_artifact(artifact(result.x), PROTOCOL)
