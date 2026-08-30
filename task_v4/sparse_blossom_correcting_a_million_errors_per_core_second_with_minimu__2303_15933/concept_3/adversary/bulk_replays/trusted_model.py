import numpy as np
from scipy.optimize import minimize


def walsh(values):
    output = np.array(values, dtype=float, copy=True)
    state_count = output.shape[-1]
    width = 1
    while width < state_count:
        blocks = output.reshape(output.shape[:-1] + (-1, 2 * width))
        left = blocks[..., :width].copy()
        right = blocks[..., width:].copy()
        blocks[..., :width] = left + right
        blocks[..., width:] = left - right
        width *= 2
    return output


class Model:
    def __init__(self, spec):
        self.spec = spec
        self.bounds = np.log(np.array([channel["rate_bounds"] for channel in spec["channels"]]))
        self.exposures = np.array([action["exposures"] for action in spec["actions"]])
        self.weights = np.array([action["mode_weights"] for action in spec["actions"]])
        masks = np.array([channel["masks"] for channel in spec["channels"]])
        state_count = 1 << spec["detector_count"]
        parity = np.array([int(index).bit_count() % 2 for index in range(state_count)])
        first = parity[masks[:, 0, None] & np.arange(state_count)]
        second = parity[masks[:, 1, None] & np.arange(state_count)]
        alternate = np.array([action["alternate_probability"] for action in spec["actions"]])
        self.odd = (1.0 - alternate[:, :, None]) * first + alternate[:, :, None] * second
        self.state_count = state_count

    def distribution(self, log_rates, gradient=False):
        attenuation = np.exp(-2.0 * self.exposures * np.exp(log_rates)[None, None, :])
        factors = 1.0 - (1.0 - attenuation[..., None]) * self.odd[:, None, :, :]
        factors = np.maximum(factors, 1e-100)
        products = np.prod(factors, axis=2)
        spectrum = np.sum(self.weights[:, :, None] * products, axis=1)
        probability = walsh(spectrum) / self.state_count
        probability = np.maximum(probability, 1e-15)
        if not gradient:
            return probability
        factor_derivative = (-2.0 * self.exposures * np.exp(log_rates)[None, None, :] * attenuation)[..., None]
        derivative = np.sum(self.weights[:, :, None, None] * products[:, :, None, :]
                            * factor_derivative * self.odd[:, None, :, :] / factors, axis=1)
        jacobian = walsh(derivative) / self.state_count
        return probability, jacobian

    def fit(self, counts, initial=None, iterations=140):
        counts = np.asarray(counts)
        start = self.bounds.mean(axis=1) if initial is None else np.asarray(initial)
        total = max(float(counts.sum()), 1.0)

        def objective(log_rates):
            probability, derivative = self.distribution(log_rates, gradient=True)
            value = -np.sum(counts * np.log(probability)) / total
            gradient = -np.einsum("as,aks->k", counts / probability, derivative) / total
            return value, gradient

        result = minimize(objective, start, method="L-BFGS-B", jac=True,
                          bounds=self.bounds.tolist(),
                          options={"maxiter": iterations, "ftol": 1e-12, "gtol": 1e-8, "maxls": 30})
        return result.x

    def fisher(self, log_rates):
        probability, derivative = self.distribution(log_rates, gradient=True)
        return np.einsum("aks,als,as->akl", derivative, derivative, 1.0 / probability, optimize=True)


def sample_histogram(spec, rates, action_id, shots, rng):
    probability = Model(spec).distribution(np.log(rates))[action_id]
    probability /= probability.sum()
    return rng.multinomial(shots, probability)
