import numpy as np
from scipy.optimize import minimize


def parity(values):
    values = np.asarray(values, dtype=np.uint64).copy()
    for shift in (32, 16, 8, 4, 2, 1):
        values ^= values >> np.uint64(shift)
    return (values & np.uint64(1)).astype(float)


def walsh(values):
    output = np.array(values, dtype=float, copy=True)
    width = 1
    while width < output.shape[-1]:
        blocks = output.reshape(output.shape[:-1] + (-1, 2 * width))
        left = blocks[..., :width].copy()
        right = blocks[..., width:].copy()
        blocks[..., :width] = left + right
        blocks[..., width:] = left - right
        width *= 2
    return output


def patches(spec):
    supports = sorted({int(channel["masks"][0] | channel["masks"][1]) for channel in spec["channels"]},
                      key=lambda mask: (-mask.bit_count(), mask))
    maximal = []
    for support in supports:
        if not any(support & containing == support for containing in maximal):
            maximal.append(support)
    return [[detector for detector in range(spec["detector_count"]) if mask & (1 << detector)] for mask in maximal]


def feature_masks(spec):
    features = set()
    for patch in patches(spec):
        for state in range(1, 1 << len(patch)):
            features.add(sum(1 << detector for index, detector in enumerate(patch) if state & (1 << index)))
    return np.array(sorted(features), dtype=np.int64)


def characters(spec, log_rates, action_id, masks, gradient=False):
    action = spec["actions"][action_id]
    footprints = np.array([channel["masks"] for channel in spec["channels"]], dtype=np.int64)
    masks = np.asarray(masks, dtype=np.int64)
    alternate = np.array(action["alternate_probability"])
    odd = ((1.0 - alternate[:, None]) * parity(footprints[:, 0, None] & masks[None, :])
           + alternate[:, None] * parity(footprints[:, 1, None] & masks[None, :]))
    intensity = np.array(action["exposures"]) * np.exp(log_rates)[None, :]
    attenuation = np.exp(-2.0 * intensity)
    factors = np.maximum(1.0 - (1.0 - attenuation[..., None]) * odd[None, :, :], 1e-100)
    products = np.prod(factors, axis=1)
    weights = np.array(action["mode_weights"])
    mean = np.einsum("m,mf->f", weights, products)
    if not gradient:
        return mean
    derivative = np.sum(weights[:, None, None] * products[:, None, :] * (-2.0 * intensity * attenuation)[..., None]
                        * odd[None, :, :] / factors, axis=0).T
    return mean, derivative


class LocalModel:
    def __init__(self, spec):
        self.spec = spec
        self.bounds = np.log(np.array([channel["rate_bounds"] for channel in spec["channels"]]))
        self.patches = patches(spec)
        self.blocks = []
        self.counts = []
        exposure = np.array([action["exposures"] for action in spec["actions"]])
        weights = np.array([action["mode_weights"] for action in spec["actions"]])
        alternate = np.array([action["alternate_probability"] for action in spec["actions"]])
        for patch in self.patches:
            support = sum(1 << detector for detector in patch)
            indices = np.array([index for index, channel in enumerate(spec["channels"])
                                if support & (channel["masks"][0] | channel["masks"][1])])
            projected = np.array([[sum(((mask >> detector) & 1) << offset for offset, detector in enumerate(patch))
                                   for mask in spec["channels"][index]["masks"]] for index in indices])
            state_count = 1 << len(patch)
            first = parity(projected[:, 0, None] & np.arange(state_count))
            second = parity(projected[:, 1, None] & np.arange(state_count))
            odd = ((1.0 - alternate[:, indices, None]) * first + alternate[:, indices, None] * second)
            self.blocks.append((indices, exposure[:, :, indices], weights, odd, state_count))
            self.counts.append(np.zeros((len(spec["actions"]), state_count)))

    def block_distribution(self, log_rates, block, gradient=False):
        indices, exposure, weights, odd, state_count = block
        intensity = exposure * np.exp(log_rates[indices])[None, None, :]
        attenuation = np.exp(-2.0 * intensity)
        factors = np.maximum(1.0 - (1.0 - attenuation[..., None]) * odd[:, None, :, :], 1e-100)
        products = np.prod(factors, axis=2)
        mean = np.sum(weights[:, :, None] * products, axis=1)
        probability = np.maximum(walsh(mean) / state_count, 1e-15)
        if not gradient:
            return probability
        derivative = np.sum(weights[:, :, None, None] * products[:, :, None, :]
                            * (-2.0 * intensity * attenuation)[..., None] * odd[:, None, :, :] / factors, axis=1)
        return probability, walsh(derivative) / state_count

    def observe(self, action, syndromes, multiplicities):
        syndromes = np.asarray(syndromes, dtype=np.int64)
        for patch, counts in zip(self.patches, self.counts):
            projected = np.zeros(len(syndromes), dtype=np.int64)
            for offset, detector in enumerate(patch):
                projected |= ((syndromes >> detector) & 1) << offset
            counts[action] += np.bincount(projected, weights=multiplicities, minlength=counts.shape[1])

    def fit(self, initial=None, iterations=150):
        start = self.bounds.mean(axis=1) if initial is None else np.asarray(initial)
        total = max(sum(counts.sum() for counts in self.counts), 1.0)

        def objective(log_rates):
            value = 0.0
            gradient = np.zeros(len(log_rates))
            for block, counts in zip(self.blocks, self.counts):
                probability, derivative = self.block_distribution(log_rates, block, gradient=True)
                value -= np.sum(counts * np.log(probability))
                gradient[block[0]] -= np.einsum("as,aks->k", counts / probability, derivative)
            return value / total, gradient / total

        result = minimize(objective, start, jac=True, method="L-BFGS-B", bounds=self.bounds.tolist(),
                          options={"maxiter": iterations, "ftol": 1e-12, "gtol": 1e-8, "maxls": 30})
        return result.x
