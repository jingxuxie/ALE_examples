import numpy as np
from scipy.special import expit


def hadamard(size):
    result = np.ones((1, 1))
    while len(result) < size:
        result = np.block([[result, result], [result, -result]])
    return result


def reduce_internal(matrix, right):
    matrix = matrix.copy()
    right = right.copy()
    pivots = []
    for column in range(matrix.shape[1]):
        candidates = np.flatnonzero(matrix[len(pivots):, column])
        if not len(candidates):
            continue
        pivot = len(pivots) + int(candidates[0])
        target = len(pivots)
        matrix[[target, pivot]] = matrix[[pivot, target]]
        right[[target, pivot]] = right[[pivot, target]]
        rows = np.flatnonzero(matrix[:, column])
        rows = rows[rows != target]
        matrix[rows] ^= matrix[target]
        right[rows] ^= right[target]
        pivots.append(column)
    return matrix, right, pivots


def xor_span(basis):
    result = np.zeros(1 << len(basis), dtype=np.uint32)
    filled = 1
    for vector in basis:
        result[filled:2 * filled] = result[:filled] ^ np.uint32(vector)
        filled *= 2
    return result


def enumeration_table(matrix, right, pivots, boundary_bits, probabilities, labels, query_membership, transform):
    internal_count = matrix.shape[1]
    rank = len(pivots)
    free = [column for column in range(internal_count) if column not in pivots]
    basis = []
    for column in free:
        vector = 1 << column
        for row, pivot in enumerate(pivots):
            if matrix[row, column]:
                vector |= 1 << pivot
        basis.append(vector)
    targets = (boundary_bits @ right[:, :-1].T + right[:, -1]) % 2
    valid = np.all(targets[:, rank:] == 0, axis=1)
    particular = np.zeros(len(boundary_bits), dtype=np.uint32)
    for row, pivot in enumerate(pivots):
        particular |= targets[:, row].astype(np.uint32) << pivot
    patterns = (particular[:, None] ^ xor_span(basis)[None, :]).ravel()
    modes = probabilities.shape[0]
    label_count = len(transform)
    channels = label_count + query_membership.shape[0]
    table = np.empty((len(boundary_bits), modes, channels))
    log_weights = np.log1p(-probabilities).sum(axis=1)[:, None] + np.zeros((modes, len(patterns)))
    logical = np.zeros(len(patterns), dtype=np.int64)
    logits = np.log(probabilities) - np.log1p(-probabilities)
    for index in range(internal_count):
        active = (patterns >> index) & 1
        log_weights += logits[:, index, None] * active
        logical ^= active.astype(np.int64) * labels[index]
    boundary_index = np.repeat(np.arange(len(boundary_bits)), 1 << len(free))
    label_index = boundary_index * label_count + logical
    parities = []
    for membership in query_membership:
        parity = np.zeros(len(patterns), dtype=np.uint8)
        for index in np.flatnonzero(membership):
            parity ^= ((patterns >> index) & 1).astype(np.uint8)
        parities.append(1.0 - 2.0 * parity)
    for mode in range(modes):
        weights = np.exp(log_weights[mode])
        distribution = np.bincount(label_index, weights=weights, minlength=len(boundary_bits) * label_count)
        table[:, mode, :label_count] = distribution.reshape(-1, label_count) @ transform
        for query_index, parity_sign in enumerate(parities):
            table[:, mode, label_count + query_index] = (weights * parity_sign).reshape(len(boundary_bits), -1).sum(axis=1)
    table[~valid] = 0
    return table


def dynamic_table(matrix, right, pivots, boundary_bits, probabilities, labels, query_membership, transform):
    rank = len(pivots)
    modes, internal_count = probabilities.shape
    label_count = len(transform)
    channels = label_count + query_membership.shape[0]
    states = np.arange(1 << rank)
    distribution = np.zeros((1 << rank, modes, channels))
    distribution[0] = 1.0
    for index in range(internal_count):
        support = sum(int(matrix[row, index]) << row for row in range(rank))
        signs = np.concatenate([transform[:, labels[index]], 1.0 - 2.0 * query_membership[:, index]])
        probability = probabilities[:, index]
        distribution = distribution * (1.0 - probability)[None, :, None] + distribution[states ^ support] * probability[None, :, None] * signs
    targets = (boundary_bits @ right[:, :-1].T + right[:, -1]) % 2
    indices = np.zeros(len(boundary_bits), dtype=np.int64)
    for row in range(rank):
        indices |= targets[:, row].astype(np.int64) << row
    table = distribution[indices].copy()
    table[np.any(targets[:, rank:] != 0, axis=1)] = 0.0
    return table


def elimination_order(scopes):
    remaining = [set(scope) for scope in scopes]
    variables = set().union(*remaining)
    order = []
    maximum = 0
    while variables:
        options = []
        for variable in variables:
            gathered = [scope for scope in remaining if variable in scope]
            union = set().union(*gathered)
            options.append((len(union), sum(len(scope) for scope in gathered), variable, union))
        _, _, variable, union = min(options, key=lambda item: item[:3])
        maximum = max(maximum, len(union))
        order.append(variable)
        remaining = [scope for scope in remaining if variable not in scope]
        remaining.append(union - {variable})
        variables.remove(variable)
    return order, maximum


def contract_factors(factors, order):
    factors = list(factors)
    for variable in order:
        selected = [(scope, values) for scope, values in factors if variable in scope]
        factors = [(scope, values) for scope, values in factors if variable not in scope]
        union = sorted(set().union(*(set(scope) for scope, _ in selected)))
        output_scope = tuple(item for item in union if item != variable)
        index = {item: position for position, item in enumerate(union)}
        mode_index, channel_index = len(union), len(union) + 1
        arguments = []
        for scope, values in selected:
            arguments.extend([values, [index[item] for item in scope] + [mode_index, channel_index]])
        arguments.append([index[item] for item in output_scope] + [mode_index, channel_index])
        result = np.einsum(*arguments, optimize=False)
        factors.append((output_scope, result))
    result = factors[0][1].copy()
    for _, values in factors[1:]:
        result *= values
    return result


class Network:
    def __init__(self, case):
        self.case = case
        self.faults = case['faults']
        regions = list(dict.fromkeys(case['detector_regions']))
        region_index = {region: index for index, region in enumerate(regions)}
        self.detector_region = [region_index[region] for region in case['detector_regions']]
        self.internal = [[] for _ in regions]
        self.boundary = [[] for _ in regions]
        self.owner = {}
        self.silent = []
        self.cross = []
        for index, fault in enumerate(self.faults):
            touched = {self.detector_region[detector] for detector in fault['detectors']}
            if not touched:
                self.silent.append(index)
            elif len(touched) == 1:
                self.internal[next(iter(touched))].append(index)
            else:
                variable = len(self.cross)
                self.cross.append(index)
                self.owner[variable] = min(touched)
                for region in touched:
                    self.boundary[region].append(variable)
        self.groups = np.array([fault['rate_group'] for fault in self.faults], dtype=int)
        self.biases = np.array([fault['bias'] for fault in self.faults])
        self.labels = np.array([fault['logical_mask'] for fault in self.faults], dtype=np.int64)
        self.transform = hadamard(1 << case['num_observables'])
        self.order, self.width = elimination_order(self.boundary)

    def emission(self, shot, model):
        offsets = np.asarray(model['offsets'])
        slopes = np.asarray(model['slopes'])
        probabilities = expit(offsets[:, self.groups] + slopes[self.groups] * shot['dose'] + self.biases)
        probabilities = np.clip(probabilities, 1e-14, 1.0 - 1e-14)
        modes = len(offsets)
        label_count = len(self.transform)
        channels = label_count + len(shot['queries'])
        membership = np.zeros((len(shot['queries']), len(self.faults)), dtype=np.uint8)
        for query_index, query in enumerate(shot['queries']):
            membership[query_index, query['faults']] = 1
        factors = []
        log_scale = np.zeros(modes)
        for region, internal in enumerate(self.internal):
            scope = self.boundary[region]
            boundary_faults = [self.cross[variable] for variable in scope]
            observed = [detector for detector, owner in enumerate(self.detector_region)
                        if owner == region and shot['syndrome'][detector] is not None]
            matrix = np.zeros((len(observed), len(internal)), dtype=np.uint8)
            right = np.zeros((len(observed), len(scope) + 1), dtype=np.uint8)
            for row, detector in enumerate(observed):
                matrix[row] = [int(detector in self.faults[index]['detectors']) for index in internal]
                right[row, :-1] = [int(detector in self.faults[index]['detectors']) for index in boundary_faults]
                right[row, -1] = shot['syndrome'][detector]
            matrix, right, pivots = reduce_internal(matrix, right)
            boundary_bits = ((np.arange(1 << len(scope))[:, None] >> np.arange(len(scope) - 1, -1, -1)) & 1).astype(np.uint8)
            argument = (matrix, right, pivots, boundary_bits, probabilities[:, internal], self.labels[internal],
                        membership[:, internal], self.transform)
            if len(internal) - len(pivots) + len(scope) <= 20:
                table = enumeration_table(*argument)
            else:
                table = dynamic_table(*argument)
            maximum = table[:, :, 0].max(axis=0)
            if np.any(maximum <= 0):
                raise ValueError('Observed syndrome is incompatible with the detector model')
            table /= maximum[None, :, None]
            log_scale += np.log(maximum)
            for boundary_index, variable in enumerate(scope):
                if self.owner[variable] != region:
                    continue
                fault_index = self.cross[variable]
                active = boundary_bits[:, boundary_index]
                probability = probabilities[:, fault_index]
                table *= np.where(active[:, None], probability, 1.0 - probability)[:, :, None]
                signs = np.concatenate([self.transform[:, self.labels[fault_index]], 1.0 - 2.0 * membership[:, fault_index]])
                table *= np.where(active[:, None], signs, 1.0)[:, None, :]
            factors.append((tuple(scope), table.reshape((2,) * len(scope) + (modes, channels))))
        silent = np.ones((modes, channels))
        for fault_index in self.silent:
            signs = np.concatenate([self.transform[:, self.labels[fault_index]], 1.0 - 2.0 * membership[:, fault_index]])
            silent *= 1.0 - probabilities[:, fault_index, None] * (1.0 - signs)
        factors.append(((), silent))
        batch_size = max(1, min(channels, (64 * 1024 * 1024) // (8 * modes * (1 << self.width))))
        moments = np.empty((modes, channels))
        for start in range(0, channels, batch_size):
            stop = min(start + batch_size, channels)
            sliced = [(scope, values[..., start:stop]) for scope, values in factors]
            moments[:, start:stop] = contract_factors(sliced, self.order)
        emission = moments[:, 0]
        if np.any(emission <= 0):
            raise ValueError('The complete observed syndrome has zero probability')
        log_emission = np.log(emission) + log_scale
        conditional = moments / emission[:, None]
        logical = (conditional[:, :label_count] @ self.transform) / label_count
        logical = np.maximum(logical, 0.0)
        logical /= logical.sum(axis=1, keepdims=True)
        queries = np.clip((1.0 - conditional[:, label_count:]) / 2.0, 0.0, 1.0)
        return log_emission, logical, queries


def smooth(log_emission, initial, transition):
    shifts = log_emission.max(axis=1)
    emission = np.exp(log_emission - shifts[:, None])
    forward = np.empty_like(emission)
    scales = np.empty(len(emission))
    forward[0] = initial * emission[0]
    scales[0] = forward[0].sum()
    forward[0] /= scales[0]
    for shot in range(1, len(emission)):
        forward[shot] = (forward[shot - 1] @ transition) * emission[shot]
        scales[shot] = forward[shot].sum()
        forward[shot] /= scales[shot]
    backward = np.ones_like(emission)
    switches = np.empty(len(emission) - 1)
    for shot in range(len(emission) - 2, -1, -1):
        suffix = emission[shot + 1] * backward[shot + 1] / scales[shot + 1]
        backward[shot] = transition @ suffix
        pair = forward[shot, :, None] * transition * suffix[None, :]
        switches[shot] = (pair.sum() - np.trace(pair)) / pair.sum()
    posterior = forward * backward
    posterior /= posterior.sum(axis=1, keepdims=True)
    return float(np.sum(shifts + np.log(scales))), posterior, np.clip(switches, 0.0, 1.0)


def decode_case(case, model):
    network = Network(case)
    emissions, logical, queries = zip(*(network.emission(shot, model) for shot in case['shots']))
    log_evidence, regimes, switches = smooth(np.asarray(emissions), np.asarray(model['initial']), np.asarray(model['transition']))
    output = []
    for index, shot in enumerate(case['shots']):
        posterior = regimes[index] @ logical[index]
        posterior = np.maximum(posterior, 0.0)
        posterior /= posterior.sum()
        query_probability = regimes[index] @ queries[index]
        output.append({'id': shot['id'], 'logical_posterior': posterior.tolist(),
                       'logical_decision': int(np.argmax(posterior)),
                       'query_probability': {query['id']: float(query_probability[query_index])
                                             for query_index, query in enumerate(shot['queries'])}})
    return {'id': case['id'], 'log_evidence': log_evidence, 'switch_probability': switches.tolist(), 'shots': output}
