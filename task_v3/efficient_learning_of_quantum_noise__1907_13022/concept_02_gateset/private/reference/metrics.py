import numpy as np


WEIGHTS = {'identification': 0.35, 'invariant_estimation': 0.25, 'heldout_prediction': 0.40}


def balanced_brier(prediction, target):
    losses = [np.mean((prediction[target == value] - value) ** 2) for value in (0, 1)
              if np.any(target == value)]
    return float(np.mean(losses))


def losses(output, oracle):
    identification = 0.5 * (balanced_brier(output['structural_identifiable'],
                                          oracle['structural_identifiable']) +
                            balanced_brier(output['calibration_identifiable'],
                                           oracle['calibration_identifiable']))
    mask = oracle['calibration_identifiable'].astype(bool)
    invariant = np.mean(((output['query_log_estimate'][mask] - oracle['query_log'][mask]) /
                         oracle['query_scale'][mask]) ** 2)
    prediction = np.mean((output['holdout_mean'] - oracle['holdout_mean']) ** 2)
    return dict(identification=float(identification), invariant_estimation=float(invariant),
                heldout_prediction=float(prediction))


def score_components(actual, baseline, reference):
    components = {}
    for component in WEIGHTS:
        scale = baseline[component] / 4 + 12 * reference[component]
        if scale <= 0 or reference[component] >= baseline[component]:
            raise ValueError('Invalid baseline/reference calibration: ' + component)
        components[component] = float(scale / (scale + actual[component]))
    return components, float(sum(WEIGHTS[key] * value for key, value in components.items()))
