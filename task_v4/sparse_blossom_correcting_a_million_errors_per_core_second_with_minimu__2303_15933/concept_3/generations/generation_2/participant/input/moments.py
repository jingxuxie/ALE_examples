import numpy as np


def parity(values):
    values = np.asarray(values, dtype=np.uint64).copy()
    for shift in (32, 16, 8, 4, 2, 1):
        values ^= values >> np.uint64(shift)
    return (values & np.uint64(1)).astype(float)


class MomentModel:
    def __init__(self, spec, masks):
        self.bounds = np.log([channel["rate_bounds"] for channel in spec["channels"]])
        self.masks = np.asarray(masks, dtype=np.int64)
        footprints = np.array([channel["masks"] for channel in spec["channels"]])
        alternate = np.array([action["alternate_probability"] for action in spec["actions"]])
        first = parity(footprints[:, 0, None] & self.masks[None, :])
        second = parity(footprints[:, 1, None] & self.masks[None, :])
        self.odd = (1.0 - alternate[..., None]) * first + alternate[..., None] * second
        self.exposures = np.array([action["exposures"] for action in spec["actions"]])
        self.weights = np.array([action["mode_weights"] for action in spec["actions"]])

    def predict(self, log_rates, gradient=False):
        intensity = self.exposures * np.exp(log_rates)[None, None, :]
        attenuation = np.exp(-2.0 * intensity)
        factors = np.maximum(1.0 - (1.0 - attenuation[..., None]) * self.odd[:, None, :, :], 1e-100)
        products = np.prod(factors, axis=2)
        mean = np.sum(self.weights[..., None] * products, axis=1)
        if not gradient:
            return mean
        derivative = np.sum(self.weights[:, :, None, None] * products[:, :, None, :]
                            * (-2.0 * intensity * attenuation)[..., None]
                            * self.odd[:, None, :, :] / factors, axis=1)
        return mean, derivative
