import math

import numpy as np

from posterior import LocalModel, contraction_plan, contract


def decode_case(case):
    faults = case['faults']
    region_labels = list(dict.fromkeys(case['detector_regions']))
    region_lookup = {label: index for index, label in enumerate(region_labels)}
    detector_regions = [region_lookup[label] for label in case['detector_regions']]
    region_count = len(region_labels)
    internal = [[] for _ in region_labels]
    boundary = [[] for _ in region_labels]
    boundary_faults = []
    boundary_owners = []
    silent = []
    for index, fault in enumerate(faults):
        owners = sorted({detector_regions[detector] for detector in fault['detectors']})
        if not owners:
            silent.append(index)
        elif len(owners) == 1:
            internal[owners[0]].append(index)
        else:
            variable = len(boundary_faults)
            boundary_faults.append(index)
            boundary_owners.append(owners[0])
            for owner in owners:
                boundary[owner].append(variable)
    logical_count = 1 << case['num_observables']
    query_keys = list(dict.fromkeys(tuple(sorted(query['faults']))
                                  for shot in case['shots'] for query in shot['queries']))
    query_indices = {key: logical_count + index for index, key in enumerate(query_keys)}
    channel_count = logical_count + len(query_keys)
    signs = np.ones((channel_count, len(faults)), dtype=np.float64)
    for character in range(logical_count):
        for index, fault in enumerate(faults):
            if (character & fault['logical_mask']).bit_count() & 1:
                signs[character, index] = -1.0
    for key, channel in query_indices.items():
        signs[channel, list(key)] = -1.0
    probabilities = np.array([fault['probabilities'] for fault in faults], dtype=float)
    modes = len(case['mode_prior'])
    probabilities = probabilities.reshape(len(faults), modes)
    plan, width = contraction_plan(boundary)
    models = {}
    shot_logs = np.full((len(case['shots']), modes), -np.inf)
    shot_moments = np.zeros((len(case['shots']), modes, channel_count))
    for shot_index, shot in enumerate(case['shots']):
        selected_channels = list(range(logical_count)) + sorted({query_indices[tuple(sorted(query['faults']))]
                                                                for query in shot['queries']})
        active_channels = len(selected_channels)
        local_models = []
        local_syndromes = []
        for region in range(region_count):
            observed = tuple(detector for detector, owner in enumerate(detector_regions)
                             if owner == region and shot['syndrome'][detector] is not None)
            key = (region, observed)
            if key not in models:
                models[key] = LocalModel(faults, internal[region], boundary[region],
                                         boundary_faults, observed, signs)
            local_models.append(models[key])
            local_syndromes.append(sum(int(shot['syndrome'][detector]) << index
                                       for index, detector in enumerate(observed)))
        for mode in range(modes):
            if case['mode_prior'][mode] == 0:
                continue
            factors = []
            impossible = False
            for region, model in enumerate(local_models):
                table, log_scale = model.evaluate(local_syndromes[region], probabilities[:, mode])
                table = table[selected_channels]
                for position, variable in enumerate(boundary[region]):
                    if boundary_owners[variable] != region:
                        continue
                    fault_index = boundary_faults[variable]
                    rate = probabilities[fault_index, mode]
                    assignments = (np.arange(table.shape[1]) >> position) & 1
                    table *= np.where(assignments[None, :],
                                      rate * signs[selected_channels, fault_index, None], 1.0 - rate)
                maximum = float(np.max(table[0]))
                if maximum == 0.0:
                    impossible = True
                    break
                table /= maximum
                log_scale += math.log(maximum)
                scope = tuple(reversed(boundary[region]))
                factors.append((scope, table.reshape((active_channels,) + (2,) * len(scope)), log_scale))
            if impossible:
                continue
            independent = np.ones(channel_count)
            for fault_index in silent:
                rate = probabilities[fault_index, mode]
                independent *= 1.0 - rate + rate * signs[:, fault_index]
            if factors:
                log_evidence, moments = contract(factors, plan, width, active_channels)
            else:
                log_evidence, moments = 0.0, np.ones(active_channels)
            if not math.isfinite(log_evidence):
                continue
            shot_logs[shot_index, mode] = log_evidence
            shot_moments[shot_index, mode, selected_channels] = moments * independent[selected_channels]
    log_weights = np.full(modes, -np.inf)
    for mode, prior in enumerate(case['mode_prior']):
        if prior > 0:
            log_weights[mode] = math.log(prior) + float(shot_logs[:, mode].sum())
    largest = float(log_weights.max())
    if not math.isfinite(largest):
        raise ValueError('All modes have zero evidence for case ' + str(case['id']))
    mode_posterior = np.exp(log_weights - largest)
    normalizer = float(mode_posterior.sum())
    mode_posterior /= normalizer
    log_evidence = largest + math.log(normalizer)
    inverse = np.array([[(-1.0 if (label & character).bit_count() & 1 else 1.0)
                         for character in range(logical_count)] for label in range(logical_count)])
    output_shots = []
    for shot_index, shot in enumerate(case['shots']):
        moments = mode_posterior @ shot_moments[shot_index]
        logical = inverse @ moments[:logical_count] / logical_count
        logical = np.clip(logical, 0.0, 1.0)
        logical /= logical.sum()
        queries = {query['id']: float(np.clip((1.0 - moments[query_indices[tuple(sorted(query['faults']))]]) / 2,
                                             0.0, 1.0)) for query in shot['queries']}
        output_shots.append({'id': shot['id'], 'logical_posterior': logical.tolist(),
                             'logical_decision': int(np.argmax(logical)), 'query_probability': queries})
    return {'id': case['id'], 'log_evidence': log_evidence,
            'mode_posterior': mode_posterior.tolist(), 'shots': output_shots}
