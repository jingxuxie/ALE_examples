import numpy as np
from scipy.linalg import solve_triangular

KB = 0.08617333262
FAMILIES = ('acoustic_dominated', 'soft_optical', 'split_optical', 'broad_multiband')
WEIGHTS = np.array([0.55, 0.10, 0.10, 0.10, 0.15])
SCALES = np.array([0.10, 3.0, 0.035, 0.06, 0.08])


def properties(alpha2f, omega, width, mu):
    mass = 2.0 * alpha2f * width / omega
    coupling = mass.sum(axis=-1)
    probability = mass / coupling[..., None]
    log_frequency = np.exp(probability @ np.log(omega))
    rms_frequency = np.sqrt(probability @ (omega ** 2))
    denominator = coupling - mu * (1.0 + 0.62 * coupling)
    exponent = -1.04 * (1.0 + coupling) / np.maximum(denominator, 1e-300)
    critical_temperature = np.where(denominator > 0, log_frequency / (1.2 * KB) * np.exp(exponent), 0.0)
    return coupling, probability, log_frequency, rms_frequency, critical_temperature


def case_metrics(prediction, truth, inputs):
    omega, width, mu = inputs['omega_mev'], inputs['domega_mev'], inputs['mu_star']
    pred = properties(prediction, omega, width, mu)
    actual = properties(truth, omega, width, mu)
    cumulative = np.abs(np.cumsum(pred[1] - actual[1], axis=1)[:, :-1])
    errors = np.column_stack((
        cumulative @ np.diff(np.log(omega)),
        cumulative @ np.diff(omega),
        np.abs(np.log(pred[0] / actual[0])),
        np.abs(np.log(pred[2] / actual[2])),
        np.abs(np.log((pred[4] + 2.0) / (actual[4] + 2.0))),
    ))
    return errors @ (WEIGHTS / SCALES), errors


def covariance(inputs, row, slots):
    std = inputs['noise_std'][row, slots]
    rho = inputs['noise_rho'][row]
    length = inputs['noise_length'][row]
    correlation = (1.0 - rho) * np.eye(len(slots)) + rho * np.exp(-np.abs(slots[:, None] - slots) / length)
    return std[:, None] * correlation * std[None, :]


def forward(alpha2f, inputs):
    omega = inputs['omega_mev']
    mass = 2.0 * alpha2f * inputs['domega_mev'] / omega
    kernel = omega ** 2 / (omega ** 2 + inputs['nu_mev'][..., None] ** 2)
    return np.einsum('brj,bj->br', kernel, mass)


def summarize(prediction, truth, family, inputs, target):
    if prediction.shape != truth.shape or prediction.dtype.kind not in 'fiu':
        raise ValueError('alpha2f has incorrect shape or dtype')
    if not np.all(np.isfinite(prediction)) or np.any(prediction < 0):
        raise ValueError('alpha2f must be finite and nonnegative')
    if np.any(prediction.sum(axis=1) <= 0) or np.max(prediction) > 1e6:
        raise ValueError('alpha2f has zero mass or exceeds the numerical safety bound 1e6')
    losses, errors = case_metrics(prediction, truth, inputs)
    if not np.all(np.isfinite(losses)):
        raise ValueError('nonfinite derived metric')
    scores = {name: float(100 * np.exp(-losses[family == code].mean())) for code, name in enumerate(FAMILIES)}
    core = float(100 * np.exp(-losses.mean()))
    worst = min(scores.values())
    clean = forward(prediction, inputs)
    residuals = []
    for row in range(len(prediction)):
        slots = np.flatnonzero(inputs['mask'][row])
        chol = np.linalg.cholesky(covariance(inputs, row, slots))
        whitened = solve_triangular(chol, clean[row, slots] - inputs['interaction'][row, slots], lower=True)
        residuals.append(float(np.mean(whitened ** 2)))
    names = ('wasserstein_log_mev', 'wasserstein_mev', 'lambda_abs_log_error', 'omega_log_abs_log_error', 'tc_plus_2k_abs_log_error')
    return {
        'valid': True,
        'passed': bool(core >= target['core_score_min'] and worst >= target['worst_family_score_min']),
        'core_score': core,
        'worst_family_score': worst,
        'family_scores': scores,
        'mean_case_loss': float(losses.mean()),
        'mean_errors': dict(zip(names, errors.mean(axis=0).tolist())),
        'family_mean_errors': {name: dict(zip(names, errors[family == code].mean(axis=0).tolist())) for code, name in enumerate(FAMILIES)},
        'mean_whitened_residual_squared': float(np.mean(residuals)),
        'p90_case_loss': float(np.quantile(losses, 0.9)),
        'case_count': int(len(prediction)),
        'reason': 'fixed quality targets met' if core >= target['core_score_min'] and worst >= target['worst_family_score_min'] else 'below fixed core or worst-family target',
    }
