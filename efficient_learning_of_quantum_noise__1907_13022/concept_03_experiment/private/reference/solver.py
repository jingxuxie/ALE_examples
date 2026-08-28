import sys
import numpy as np


def walsh(values):
    result = np.array(values, dtype=float, copy=True)
    width = result.shape[-1]
    stride = 1
    while stride < width:
        pieces = result.reshape(*result.shape[:-1], -1, 2, stride)
        left = pieces[..., 0, :].copy()
        right = pieces[..., 1, :].copy()
        pieces[..., 0, :] = left + right
        pieces[..., 1, :] = left - right
        stride *= 2
    return result


def simplex(values):
    ordered = np.sort(values)[::-1]
    offsets = (np.cumsum(ordered) - 1.0) / np.arange(1, len(ordered) + 1)
    offset = offsets[np.flatnonzero(ordered > offsets)[-1]]
    return np.maximum(values - offset, 0.0)


def fit_modes(depths, modes):
    nonconstant = modes[:, 1:]
    crossed = nonconstant < nonconstant[0] * (17.0 / 64.0)
    first = np.argmax(crossed, axis=0)
    stops = np.where(crossed.any(axis=0), np.maximum(first + 1, 3), len(depths))
    selected = np.arange(len(depths))[:, None] < stops[None, :]
    selected_data = np.where(selected, nonconstant, 0.0)
    coordinate = np.asarray(depths)[:, None]

    def objective(rates):
        basis = np.where(selected, np.power(rates[None, :], coordinate), 0.0)
        denominator = np.maximum(np.sum(basis * basis, axis=0), 1e-300)
        amplitudes = np.clip(np.sum(basis * selected_data, axis=0) / denominator, .01, 1.)
        residual = selected_data - basis * amplitudes
        return np.sum(residual * residual, axis=0), amplitudes

    left = np.full(nonconstant.shape[1], .01)
    right = np.ones_like(left)
    ratio = (np.sqrt(5.) - 1.) / 2.
    inner_left = right - ratio * (right - left)
    inner_right = left + ratio * (right - left)
    loss_left, _ = objective(inner_left)
    loss_right, _ = objective(inner_right)
    for iteration in range(65):
        keep_left = loss_left < loss_right
        right = np.where(keep_left, inner_right, right)
        left = np.where(keep_left, left, inner_left)
        inner_left = right - ratio * (right - left)
        inner_right = left + ratio * (right - left)
        loss_left, _ = objective(inner_left)
        loss_right, _ = objective(inner_right)
    rates = (left + right) / 2.
    _, amplitudes = objective(rates)
    return np.r_[1., rates], np.r_[1., amplitudes], stops


def marginal(probabilities, qubits):
    labels = np.arange(len(probabilities), dtype=np.int64)
    index = np.zeros(len(probabilities), dtype=np.int64)
    for position, qubit in enumerate(qubits):
        index |= ((labels >> int(qubit)) & 1) << position
    return np.bincount(index, weights=probabilities, minlength=2 ** len(qubits))


def entropy(probabilities):
    positive = probabilities[probabilities > 0]
    return -np.sum(positive * np.log(positive))


def diagnostics(probabilities, data):
    labels = np.arange(len(probabilities), dtype=np.int64)
    events = []
    for block in data['blocks']:
        mask = int(np.sum(block.astype(np.int64) * (1 << np.arange(len(block)))))
        events.append((labels & mask) != 0)
    events = np.asarray(events, dtype=float)
    means = events @ probabilities
    covariance = (events * probabilities) @ events.T - means[:, None] * means
    scales = np.sqrt(np.maximum(means * (1 - means), 0.0))
    denominators = scales[:, None] * scales
    correlations = np.divide(covariance, denominators, out=np.zeros_like(covariance), where=denominators > 0)
    information = []
    for query in data['conditional_queries']:
        first, second, given = [np.flatnonzero(mask).tolist() for mask in query]
        information.append(entropy(marginal(probabilities, first + given))
                           + entropy(marginal(probabilities, second + given))
                           - entropy(marginal(probabilities, given))
                           - entropy(marginal(probabilities, first + second + given)))
    model = np.ones(len(probabilities))
    for qubit, parent_mask in enumerate(data['parents']):
        parents = np.flatnonzero(parent_mask).tolist()
        joint = marginal(probabilities, [qubit] + parents).reshape(-1, 2)
        denominator = joint.sum(axis=1, keepdims=True)
        conditional = np.divide(joint, denominator, out=np.full_like(joint, .5), where=denominator > 0)
        parent_index = np.zeros(len(probabilities), dtype=np.int64)
        for position, parent in enumerate(parents):
            parent_index |= ((labels >> parent) & 1) << position
        model *= conditional[parent_index, (labels >> qubit) & 1]
    model /= model.sum()
    mixture = .5 * (probabilities + model)
    divergence = 0.0
    for distribution in (probabilities, model):
        positive = distribution > 0
        divergence += .5 * np.sum(distribution[positive] * np.log2(distribution[positive] / mixture[positive]))
    return dict(probabilities=probabilities, correlations=correlations,
                conditional_information=np.maximum(information, 0.),
                spatial_jsd=np.array(np.sqrt(max(divergence, 0.))))


def solve(input_path, output_path):
    data = np.load(input_path, allow_pickle=False)
    probabilities = data['counts'].astype(float)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    modes = walsh(probabilities)
    rates, amplitudes, stops = fit_modes(data['depths'], modes)
    recovered = simplex(walsh(rates) / len(rates))
    np.savez(output_path, **diagnostics(recovered, data))


if __name__ == '__main__':
    solve(*sys.argv[1:])
