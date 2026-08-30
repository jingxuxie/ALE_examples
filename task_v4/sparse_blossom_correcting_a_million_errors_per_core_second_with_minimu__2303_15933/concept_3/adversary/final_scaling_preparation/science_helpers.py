import numpy as np

from cases import sample
from validation_model import LocalModel, characters, feature_masks, parity, walsh


def independent_marginal(case, patch, action_id):
    action = case["spec"]["actions"][action_id]
    states = np.arange(1 << len(patch))
    result = np.zeros(len(states))
    for mode, weight in enumerate(action["mode_weights"]):
        distribution = np.zeros(len(states))
        distribution[0] = 1.0
        for index, channel in enumerate(case["spec"]["channels"]):
            footprints = [sum(((mask >> detector) & 1) << offset for offset, detector in enumerate(patch)) for mask in channel["masks"]]
            probability = -0.5 * np.expm1(-2.0 * action["exposures"][mode][index] * case["rates"][index])
            alternate = action["alternate_probability"][index]
            distribution = ((1.0 - probability) * distribution + probability * (1.0 - alternate) * distribution[states ^ footprints[0]]
                            + probability * alternate * distribution[states ^ footprints[1]])
        result += weight * distribution
    return result


def moment_information(spec, rates, masks):
    log_rates = np.log(rates)
    xor_masks, inverse = np.unique((masks[:, None] ^ masks[None, :]).ravel(), return_inverse=True)
    information = []
    min_covariance = []
    for action in range(len(spec["actions"])):
        mean, derivative = characters(spec, log_rates, action, masks, gradient=True)
        xor_means = np.concatenate([characters(spec, log_rates, action, xor_masks[start:start + 512])
                                    for start in range(0, len(xor_masks), 512)])
        covariance = xor_means[inverse].reshape(len(masks), len(masks)) - np.outer(mean, mean)
        values, vectors = np.linalg.eigh(covariance)
        min_covariance.append(float(values[0]))
        assert values[0] > -1e-10
        transformed = vectors.T @ derivative
        information.append(transformed.T @ (transformed / np.maximum(values[:, None], 1e-10)))
    matrix = np.sum(information, axis=0) * spec["shot_budget"] / len(information)
    diagonal = np.diag(np.linalg.inv(matrix))
    assert np.min(diagonal) > 0
    families = np.array([channel["family"] for channel in spec["channels"]])
    return {"moment_information_rank": int(np.linalg.matrix_rank(matrix)),
            "minimum_information_eigenvalue": float(np.linalg.eigvalsh(matrix)[0]),
            "condition_number": float(np.linalg.cond(matrix)),
            "minimum_feature_covariance_eigenvalue": min(min_covariance),
            "covariance_eigenvalue_floor": 1e-10,
            "uniform_budget_optimal_moment_asymptotic_log_sd": {
                family: float(np.sqrt(np.mean(diagonal[families == family]))) for family in sorted(set(families))}}


def validate_case(case, information=False):
    spec = case["spec"]
    detector_count = spec["detector_count"]
    channel_count = len(spec["channels"])
    adjacency = [set() for detector in range(detector_count)]
    for first, second in spec["detector_edges"]:
        adjacency[first].add(second)
        adjacency[second].add(first)
    distances = np.full((detector_count, detector_count), detector_count + 1, dtype=int)
    for origin in range(detector_count):
        distances[origin, origin] = 0
        frontier = [origin]
        for node in frontier:
            for neighbor in adjacency[node]:
                if distances[origin, neighbor] > distances[origin, node] + 1:
                    distances[origin, neighbor] = distances[origin, node] + 1
                    frontier.append(neighbor)
    assert np.max(distances) <= detector_count - 1
    incidence = np.zeros(detector_count, dtype=int)
    largest_diameter = 0
    for channel in spec["channels"]:
        support = channel["masks"][0] | channel["masks"][1]
        nodes = [detector for detector in range(detector_count) if support & (1 << detector)]
        incidence[nodes] += 1
        largest_diameter = max(largest_diameter, int(distances[np.ix_(nodes, nodes)].max()))
    assert largest_diameter <= 2
    assert np.min(incidence) >= 2
    model = LocalModel(spec)
    assert max(map(len, model.patches)) <= 4
    masks = feature_masks(spec)
    log_rates = np.log(case["rates"])
    jacobian = np.concatenate([characters(spec, log_rates, action, masks, True)[1] for action in range(len(spec["actions"]))])
    rank = int(np.linalg.matrix_rank(jacobian, tol=1e-9))
    reference_rank = int(np.linalg.matrix_rank(characters(spec, log_rates, 0, masks, True)[1], tol=1e-9))
    assert rank == channel_count and reference_rank < channel_count
    direction = np.random.default_rng(8911).normal(size=channel_count)
    finite_difference = (characters(spec, log_rates + 1e-5 * direction, 3, masks)
                         - characters(spec, log_rates - 1e-5 * direction, 3, masks)) / 2e-5
    gradient_error = float(np.max(np.abs(finite_difference - characters(spec, log_rates, 3, masks, True)[1] @ direction)))
    assert gradient_error < 1e-8
    discrepancy = 0.0
    for block, patch in zip(model.blocks, model.patches):
        probability = model.block_distribution(log_rates, block)
        for action in (0, 3, 11, len(spec["actions"]) - 1):
            independent = independent_marginal(case, patch, action)
            discrepancy = max(discrepancy, float(np.max(np.abs(probability[action] - independent))))
    assert discrepancy < 2e-12
    empirical_z = 0.0
    for poisson in (False, True):
        shots = 100000
        action = 3 if not poisson else len(spec["actions"]) - 1
        syndromes, multiplicities = sample(case, action, shots, np.random.default_rng(19011 + int(poisson)), poisson=poisson)
        empirical = np.concatenate([np.sum((1.0 - 2.0 * parity(syndromes[:, None] & masks[None, start:start + 32]))
                                          * multiplicities[:, None], axis=0) / shots
                                    for start in range(0, len(masks), 32)])
        expected = characters(spec, log_rates, action, masks)
        deviation = np.sqrt(np.maximum(1.0 - expected**2, 1e-14) / shots)
        empirical_z = max(empirical_z, float(np.max(np.abs(empirical - expected) / deviation)))
    assert empirical_z < 7.0
    expected_detector_clicks = np.zeros(detector_count)
    for action in range(len(spec["actions"])):
        expected_detector_clicks += spec["shot_budget"] / len(spec["actions"]) * (1.0 - characters(spec, log_rates, action, 1 << np.arange(detector_count))) / 2.0
    assert np.min(expected_detector_clicks) > 100
    result = {"case": case["id"], "detectors": detector_count, "channels": channel_count, "actions": len(spec["actions"]),
              "connected": True, "minimum_channel_incidence": int(incidence.min()),
              "maximum_graph_degree": max(map(len, adjacency)), "maximum_channel_support_diameter": largest_diameter,
              "patches": len(model.patches), "max_patch_detectors": max(map(len, model.patches)),
              "observable_parity_features": len(masks), "jacobian_rank": rank, "reference_rank": reference_rank,
              "independent_marginal_max_error": discrepancy, "gradient_max_error": gradient_error,
              "independent_sampler_max_z": empirical_z,
              "minimum_expected_detector_clicks_uniform_budget": float(expected_detector_clicks.min()),
              "dense_single_mode_factor_array_GiB": 8 * len(spec["actions"]) * 2 * channel_count * 2**detector_count / 1024**3}
    if information:
        result["information"] = moment_information(spec, case["rates"], masks)
    return result


