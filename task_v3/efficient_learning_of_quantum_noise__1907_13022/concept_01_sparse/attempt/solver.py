import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys
import time
import itertools
import numpy as np
from scipy.linalg import cho_factor, cho_solve


def walsh(values):
    result = np.array(values, dtype=np.float64, copy=True)
    width = result.shape[-1]
    stride = 1
    while stride < width:
        blocks = result.reshape(*result.shape[:-1], -1, 2 * stride)
        first = blocks[..., :stride].copy()
        second = blocks[..., stride:].copy()
        blocks[..., :stride] = first + second
        blocks[..., stride:] = first - second
        stride *= 2
    return result / width


def packed_integer(bits):
    return int.from_bytes(np.packbits(bits, bitorder='little').tobytes(), 'little')


def span_coordinates(rows, offsets):
    basis = {}
    for index, row in enumerate(rows):
        value = packed_integer(row)
        combination = 1 << index
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (value, combination)
                break
            value ^= basis[pivot][0]
            combination ^= basis[pivot][1]
    coordinates = []
    for row in offsets:
        value = packed_integer(row)
        combination = 0
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                break
            value ^= basis[pivot][0]
            combination ^= basis[pivot][1]
        coordinates.append(combination if value == 0 else -1)
    return coordinates


class SoftDecoder:
    def __init__(self, offsets, hash_rows):
        self.dimension = offsets.shape[1]
        self.extra = offsets[self.dimension + 1:]
        self.checks = np.concatenate((self.extra, hash_rows), axis=0)
        self.redundancy = self.checks.shape[0]
        self.columns = [packed_integer(self.checks[:, index])
                        for index in range(self.dimension)]
        self.columns.extend(1 << index for index in range(len(self.extra)))
        self.length = len(self.columns)

    def decode(self, values, hash_bits, order=1, breadth=24, number=2):
        hard = (values[1:] < 0).astype(np.uint8)
        reliability = np.abs(values[1:])
        syndrome_bits = (self.checks @ hard[:self.dimension]) & 1
        syndrome_bits[:len(self.extra)] ^= hard[self.dimension:]
        syndrome_bits[len(self.extra):] ^= hash_bits
        syndrome = packed_integer(syndrome_bits)
        if syndrome == 0:
            return [hard[:self.dimension].copy()]
        basis = [0] * self.redundancy
        transforms = [0] * self.redundancy
        selected = []
        selected_set = set()
        for index in np.argsort(reliability):
            index = int(index)
            value = self.columns[index]
            combination = 1 << len(selected)
            while value:
                pivot = value.bit_length() - 1
                if basis[pivot] == 0:
                    basis[pivot] = value
                    transforms[pivot] = combination
                    selected.append(index)
                    selected_set.add(index)
                    break
                value ^= basis[pivot]
                combination ^= transforms[pivot]
            if len(selected) == self.redundancy:
                break
        def resolve(value):
            combination = 0
            while value:
                pivot = value.bit_length() - 1
                if basis[pivot] == 0:
                    return None
                value ^= basis[pivot]
                combination ^= transforms[pivot]
            return combination

        initial = resolve(syndrome)
        if initial is None:
            return []
        outside = [int(index) for index in np.argsort(reliability)
                   if int(index) not in selected_set][:breadth]
        changes = [resolve(self.columns[index]) for index in outside]
        masks = [initial]
        flipped = [()]
        costs = [0.0]
        if order >= 1:
            for index, change in enumerate(changes):
                masks.append(initial ^ change)
                flipped.append((outside[index],))
                costs.append(reliability[outside[index]])
        if order >= 2:
            for first in range(len(outside)):
                for second in range(first):
                    masks.append(initial ^ changes[first] ^ changes[second])
                    flipped.append((outside[first], outside[second]))
                    costs.append(reliability[outside[first]] + reliability[outside[second]])
        if order >= 3:
            for first, second, third in itertools.combinations(range(min(len(outside), 28)), 3):
                masks.append(initial ^ changes[first] ^ changes[second] ^ changes[third])
                flipped.append((outside[first], outside[second], outside[third]))
                costs.append(reliability[outside[first]] + reliability[outside[second]] + reliability[outside[third]])
        mask_integers = masks
        mask_parts = [np.array([(mask >> shift) & ((1 << 64) - 1) for mask in mask_integers], dtype=np.uint64)
                      for shift in range(0, len(selected), 64)]
        costs = np.array(costs)
        selected = np.array(selected, dtype=np.int64)
        byte_bits = ((np.arange(256)[:, None] >> np.arange(8)) & 1)
        for start in range(0, len(selected), 8):
            weights = reliability[selected[start:start + 8]]
            table = byte_bits[:, :len(weights)] @ weights
            part = mask_parts[start // 64]
            costs += table[((part >> np.uint64(start % 64)) & np.uint64(255)).astype(np.int64)]
        results = []
        for index in np.argsort(costs)[:number]:
            corrected = hard.copy()
            change = mask_integers[index]
            while change:
                lowest = change & -change
                corrected[selected[lowest.bit_length() - 1]] ^= 1
                change ^= lowest
            for position in flipped[index]:
                corrected[position] ^= 1
            results.append(corrected[:self.dimension])
        return results


class Reconstruction:
    def __init__(self, data):
        self.started = time.monotonic()
        self.qubit_count = int(data['n_qubits'])
        self.dimension = 2 * self.qubit_count
        self.hashes = np.array(data['hashes'], dtype=np.uint8)
        self.offsets = np.array(data['offsets'], dtype=np.uint8)
        self.groups, self.hash_width, _ = self.hashes.shape
        self.buckets = 1 << self.hash_width
        self.rows = self.offsets.shape[0]
        self.extra_start = self.dimension + 1
        self.floor = float(data['recovery_floor'])
        self.maximum = int(data['max_terms'])
        self.capacity = min(2048, max(640, 2 * self.maximum + 64))
        self.values = np.ascontiguousarray(walsh(data['eigenvalues']).transpose(0, 2, 1))
        self.sigma = np.maximum(np.array(data['noise_std']) / np.sqrt(self.buckets), 1e-15)
        self.weights = (np.median(self.sigma) / self.sigma) ** 2
        self.fit_weights = None
        self.bit_weights = (1 << np.arange(self.hash_width, dtype=np.int64))
        self.uniform = np.zeros_like(self.values)
        bucket_bits = (np.arange(self.buckets)[:, None] >> np.arange(self.hash_width)) & 1
        for group in range(self.groups):
            coordinates = span_coordinates(self.hashes[group], self.offsets)
            for row, coordinate in enumerate(coordinates):
                if coordinate >= 0:
                    binary = (coordinate >> np.arange(self.hash_width)) & 1
                    self.uniform[group, :, row] = (1.0 - 2.0 * ((bucket_bits @ binary) & 1)) / self.buckets
        self.uniform_norm = np.sum(self.uniform ** 2 * self.weights[:, None, :])
        self.uniform_data = np.sum(self.uniform * self.values * self.weights[:, None, :])
        self.bits = np.zeros((1, self.dimension), dtype=np.uint8)
        self.probabilities = np.zeros(1)
        self.known = {bytes(self.bits[0])}
        self.trusted = set(self.known)
        self.blocked = set()
        self.archive = {}
        self.decoders = [SoftDecoder(self.offsets, self.hashes[group]) for group in range(self.groups)]
        self.pair_decoders = {}
        self.xor_decoders = {}
        self.triple_decoders = {}
        self.residual = self.values.copy()
        self.fit()

    def signatures(self, bits):
        return 1.0 - 2.0 * ((bits @ self.offsets.T) & 1)

    def locations(self, bits):
        return np.stack([((bits @ matrix.T) & 1) @ self.bit_weights for matrix in self.hashes])

    def fit(self):
        count = len(self.bits)
        signs = self.signatures(self.bits)
        locations = self.locations(self.bits)
        gram = np.full((count, count), self.uniform_norm)
        rhs = np.full(count, self.uniform_norm - self.uniform_data)
        uniform_cross = np.zeros(count)
        for group in range(self.groups):
            weights = self.weights[group] if self.fit_weights is None else self.fit_weights[group, locations[group]]
            weighted = signs * weights
            rhs += np.einsum('ij,ij->i', weighted, self.values[group, locations[group]])
            uniform_cross += np.einsum('ij,ij->i', weighted, self.uniform[group, locations[group]])
            ordering = np.argsort(locations[group])
            borders = np.flatnonzero(np.diff(locations[group, ordering])) + 1
            for indices in np.split(ordering, borders):
                gram[np.ix_(indices, indices)] += weighted[indices] @ signs[indices].T
        gram -= uniform_cross[:, None] + uniform_cross[None, :]
        rhs -= uniform_cross
        diagonal = np.diag(gram).copy()
        gram.flat[::count + 1] += np.maximum(diagonal, 1e-30) * 1e-12
        active = np.arange(count)
        solution = np.zeros(count)
        last_active = active
        for iteration in range(40):
            if not len(active):
                break
            last_active = active
            submatrix = gram[np.ix_(active, active)]
            try:
                factor = cho_factor(submatrix, lower=True, check_finite=False)
                estimate = cho_solve(factor, rhs[active], check_finite=False)
                if estimate.sum() > 1.0:
                    direction = cho_solve(factor, np.ones(len(active)), check_finite=False)
                    estimate -= direction * ((estimate.sum() - 1.0) / direction.sum())
            except np.linalg.LinAlgError:
                estimate = np.linalg.lstsq(submatrix, rhs[active], rcond=1e-10)[0]
            if np.all(estimate >= 0):
                solution[active] = estimate
                break
            active = active[estimate > 0]
        else:
            solution[last_active] = np.maximum(estimate, 0.0)
        if solution.sum() > 1.0:
            solution /= solution.sum()
        self.probabilities = solution
        self.residual = self.values - (1.0 - solution.sum()) * self.uniform
        for group in range(self.groups):
            np.add.at(self.residual[group], locations[group], -solution[:, None] * signs)
        self.fit_std = np.median(self.sigma) / np.sqrt(np.diag(gram))

    def consider(self, proposals, mode='direct'):
        candidates = []
        sources = []
        seen = set()
        for bits, source in proposals:
            key = bytes(bits)
            if key in self.known or key in seen or (mode != 'direct' and key in self.blocked):
                continue
            seen.add(key)
            candidates.append(bits)
            sources.append(source)
        if not candidates:
            return 0
        candidates = np.array(candidates, dtype=np.uint8)
        signs = self.signatures(candidates)
        locations = self.locations(candidates)
        count = len(candidates)
        check_num = np.zeros(count)
        check_den = np.zeros(count)
        external_num = np.zeros(count)
        external_den = np.zeros(count)
        external_check_num = np.zeros(count)
        external_check_den = np.zeros(count)
        amplitude_num = np.zeros(count)
        amplitude_den = np.zeros(count)
        source_mask = np.zeros((self.groups, count), dtype=bool)
        for index, source in enumerate(sources):
            source_mask[list(source), index] = True
        for group in range(self.groups):
            observed = self.residual[group, locations[group]]
            for start, numerator, denominator, external in [
                    (self.extra_start, check_num, check_den, False),
                    (1, external_num, external_den, True)]:
                weights = self.weights[group, start:]
                total_weight = weights.sum()
                matched = observed[:, start:] * signs[:, start:]
                means = (matched @ weights) / total_weight
                scatter = np.sum((matched - means[:, None]) ** 2 * weights, axis=1) / total_weight
                noise = np.mean(self.sigma[group, start:] ** 2)
                variance = np.maximum(scatter, noise) * np.sum(weights ** 2) / total_weight ** 2
                precision = 1.0 / np.maximum(variance, 1e-30)
                if external:
                    precision *= ~source_mask[group]
                else:
                    external_check_num += means * precision * (~source_mask[group])
                    external_check_den += precision * (~source_mask[group])
                numerator += means * precision
                denominator += precision
            weights = self.weights[group, 1:]
            means = ((observed[:, 1:] * signs[:, 1:]) @ weights) / weights.sum()
            amplitude_num += means
            amplitude_den += 1.0
        check_z = check_num / np.sqrt(np.maximum(check_den, 1e-30))
        external_z = external_num / np.sqrt(np.maximum(external_den, 1e-30))
        external_check_z = external_check_num / np.sqrt(np.maximum(external_check_den, 1e-30))
        estimates = amplitude_num / amplitude_den
        detection_floor = max(np.median(self.sigma) / np.sqrt(self.groups * (self.rows - 1)) * 3.0,
                              self.floor * 0.015)
        if mode == 'direct':
            accept = (check_z > 5.5) & (external_z > 2.5)
        elif mode == 'soft':
            accept = (check_z > 7.5) & (external_z > 5.5) & (external_check_z > 4.5)
        else:
            accept = (check_z > 7.5) & (external_z > 5.0) & (external_check_z > 3.5)
        accept &= estimates > detection_floor
        selected = np.flatnonzero(accept)
        if not len(selected):
            return 0
        room = max(0, self.capacity - len(self.bits))
        if len(selected) > room:
            selected = selected[np.argsort(estimates[selected])[-room:]] if room else selected[:0]
        if not len(selected):
            return 0
        self.bits = np.concatenate((self.bits, candidates[selected]))
        self.known.update(bytes(bits) for bits in candidates[selected])
        if mode == 'direct':
            self.trusted.update(bytes(bits) for bits in candidates[selected])
            self.blocked.difference_update(bytes(bits) for bits in candidates[selected])
        self.fit()
        return len(selected)

    def direct(self):
        proposals = []
        for group in range(self.groups):
            bits = (self.residual[group, :, 1:self.dimension + 1] < 0).astype(np.uint8)
            bins = ((bits @ self.hashes[group].T) & 1) @ self.bit_weights
            for bucket in np.flatnonzero(bins == np.arange(self.buckets)):
                proposals.append((bits[bucket], (group,)))
        return self.consider(proposals)

    def refine(self, deep=False):
        if len(self.bits) <= 1:
            return 0
        signs = self.signatures(self.bits)
        locations = self.locations(self.bits)
        combined = np.zeros_like(signs)
        precisions = np.zeros(len(self.bits))
        restored_groups = []
        for group in range(self.groups):
            restored = self.residual[group, locations[group]] + self.probabilities[:, None] * signs
            restored_groups.append(restored)
            power = np.maximum(np.mean(restored[:, 1:] ** 2, axis=1), np.mean(self.sigma[group, 1:] ** 2))
            combined += restored / power[:, None]
            precisions += 1.0 / power
        combined /= precisions[:, None]
        decoded = (combined[:, 1:self.dimension + 1] < 0).astype(np.uint8)
        decoded_locations = self.locations(decoded)
        possible = np.all(decoded_locations == locations, axis=0) & np.any(decoded != self.bits, axis=1)
        possible[0] = False
        indices = np.flatnonzero(possible)
        total_weight = np.sum(self.weights)
        replacements = {}
        strength = np.mean(np.abs(combined[:, 1:]), axis=1)

        def assess(index, bits):
            signature = self.signatures(bits[None])[0]
            check_values = combined[index, self.extra_start:]
            reliable = np.abs(check_values) > 0.35 * strength[index]
            if np.count_nonzero(reliable) < 10 or np.any(check_values[reliable] * signature[self.extra_start:][reliable] < 0):
                return -np.inf
            improvement = 0.0
            for group in range(self.groups):
                improvement += np.sum((signature - signs[index]) * restored_groups[group][index] * self.weights[group]) / total_weight
            return improvement

        for index in indices:
            improvement = assess(index, decoded[index])
            if improvement > max(4 * self.fit_std[index], 0.025 * self.probabilities[index]):
                replacements[int(index)] = decoded[index]
        if deep:
            groups = tuple(range(self.groups))
            if groups not in self.triple_decoders:
                self.triple_decoders[groups] = SoftDecoder(self.offsets, np.concatenate(list(self.hashes)))
            decoder = self.triple_decoders[groups]
            held_out = min(16, (self.rows - self.extra_start) // 2)
            differences = np.sum(decoded != self.bits, axis=1)
            selected = np.flatnonzero((differences > 0) & (self.probabilities > 1.1 * np.median(self.sigma)))
            selected = selected[np.argsort(differences[selected])[::-1]][:512]
            for index in selected:
                if index == 0 or int(index) in replacements:
                    continue
                values = combined[index].copy()
                values[-held_out:] = 0.0
                hash_bits = np.concatenate([((int(location) >> np.arange(self.hash_width)) & 1)
                                           for location in locations[:, index]]).astype(np.uint8)
                proposals = decoder.decode(values, hash_bits, order=3, breadth=36, number=3)
                best_improvement = max(4 * self.fit_std[index], 0.025 * self.probabilities[index])
                for bits in proposals:
                    if np.array_equal(bits, self.bits[index]):
                        continue
                    signature = self.signatures(bits[None])[0]
                    check_values = combined[index, -held_out:]
                    reliable = np.abs(check_values) > 0.35 * strength[index]
                    if np.count_nonzero(reliable) < 10 or np.any(check_values[reliable] * signature[-held_out:][reliable] < 0):
                        continue
                    improvement = assess(index, bits)
                    if improvement > best_improvement:
                        best_improvement = improvement
                        replacements[int(index)] = bits
                if time.monotonic() - self.started > 95:
                    break
        if not replacements:
            return 0
        for index, bits in replacements.items():
            self.bits[index] = bits
        unique = []
        self.known = set()
        for bits in self.bits:
            key = bytes(bits)
            if key not in self.known:
                unique.append(bits)
                self.known.add(key)
        self.bits = np.array(unique, dtype=np.uint8)
        self.fit()
        return len(replacements)

    def soft(self, order=1):
        proposals = []
        for group in range(self.groups):
            powers = np.mean(self.residual[group, :, 1:] ** 2, axis=1)
            noise = np.mean(self.sigma[group, 1:] ** 2)
            selected = np.flatnonzero(powers > max(1.5 * noise, (self.floor * 0.025) ** 2))
            for bucket in selected[np.argsort(powers[selected])[::-1]]:
                hash_bits = ((int(bucket) >> np.arange(self.hash_width)) & 1).astype(np.uint8)
                values = self.residual[group, bucket] * self.weights[group]
                decoded = self.decoders[group].decode(values, hash_bits, order=order, breadth=28, number=2)
                proposals.extend((bits, (group,)) for bits in decoded)
                if time.monotonic() - self.started > 100:
                    break
        return self.consider(proposals, 'soft')

    def pairs(self, order=1):
        proposals = []
        options = []
        for first in range(self.groups):
            for second in range(first):
                left = self.residual[first, :, 1:]
                right = self.residual[second, :, 1:]
                left_norm = np.sqrt(np.sum(left ** 2, axis=1))
                right_norm = np.sqrt(np.sum(right ** 2, axis=1))
                correlation = (left @ right.T) / np.maximum(left_norm[:, None] * right_norm[None, :], 1e-30)
                left_good = left_norm > np.sqrt(self.rows - 1) * np.median(self.sigma[first]) * 1.4
                right_good = right_norm > np.sqrt(self.rows - 1) * np.median(self.sigma[second]) * 1.4
                correlation[~left_good] = -1
                correlation[:, ~right_good] = -1
                best = np.argpartition(correlation, -min(3, self.buckets), axis=1)[:, -min(3, self.buckets):]
                for bucket in range(self.buckets):
                    for other in best[bucket]:
                        score = correlation[bucket, other]
                        if score > 0.3:
                            options.append((score, first, second, bucket, int(other)))
        options.sort(reverse=True)
        for score, first, second, bucket, other in options[:600]:
            key = (first, second)
            if key not in self.pair_decoders:
                self.pair_decoders[key] = SoftDecoder(self.offsets, np.concatenate((self.hashes[first], self.hashes[second])))
            hash_bits = np.concatenate((((bucket >> np.arange(self.hash_width)) & 1),
                                        ((other >> np.arange(self.hash_width)) & 1))).astype(np.uint8)
            values = self.residual[first, bucket] + self.residual[second, other]
            decoded = self.pair_decoders[key].decode(values, hash_bits, order=order, breadth=24, number=2)
            proposals.extend((bits, key) for bits in decoded)
            if time.monotonic() - self.started > 100:
                break
        return self.consider(proposals, 'pair')

    def doubletons(self):
        doubletons = []
        physical = self.residual + (1.0 - self.probabilities.sum()) * self.uniform
        for group in range(self.groups):
            for bucket in range(self.buckets):
                observed = physical[group, bucket]
                absolute = np.abs(observed[1:])
                low, high = np.quantile(absolute, [0.25, 0.75])
                for iteration in range(5):
                    above = absolute > (low + high) * 0.5
                    if above.all() or not above.any():
                        break
                    low = np.mean(absolute[~above])
                    high = np.mean(absolute[above])
                if high - low < max(6 * np.median(self.sigma[group]), self.floor * 0.05):
                    continue
                center = (high + low) * 0.5
                magnitude_values = np.abs(observed) - center
                difference = (magnitude_values[1:self.dimension + 1] < 0).astype(np.uint8)
                if not np.any(difference) or np.any((self.hashes[group] @ difference) & 1):
                    continue
                xor_signs = self.signatures(difference[None])[0]
                if np.count_nonzero(xor_signs[1:] * magnitude_values[1:] < 0) > 0:
                    continue
                levels = np.where(xor_signs[1:] > 0, high, low)
                scatter = np.sqrt(np.mean((absolute - levels) ** 2))
                if scatter > (high - low) * 0.18:
                    continue
                doubletons.append((high, group, bucket, difference, xor_signs, (high - low) * 0.5))
        doubletons.sort(key=lambda item: -item[0])
        proposals = []
        seen = set()
        for mass, source, bucket, difference, xor_signs, minimum_amplitude in doubletons:
            source_values = physical[source, bucket]
            known = xor_signs > 0
            known[0] = False
            unknown = (xor_signs < 0)
            if np.count_nonzero(unknown) < 8:
                continue
            orientation = np.sign(source_values)
            options = []
            for group in range(self.groups):
                if group == source:
                    continue
                delta = int(self.locations(difference[None])[group, 0])
                if delta == 0:
                    continue
                choices = np.arange(self.buckets)
                partners = choices ^ delta
                choices = choices[choices < partners]
                partners = choices ^ delta
                combined = physical[group, choices] + physical[group, partners] * xor_signs
                selected_values = combined[:, known]
                score = (selected_values @ orientation[known]) / np.maximum(
                    np.sqrt(np.sum(selected_values ** 2, axis=1) * np.count_nonzero(known)), 1e-30)
                ordering = np.argsort(score)[-3:][::-1]
                if score[ordering[0]] > 0.3:
                    options.append((float(score[ordering[0]]), group, delta, choices[ordering]))
            options.sort(reverse=True, key=lambda item: item[0])
            if len(options) < 2:
                continue
            first_option, second_option = options[:2]
            first, first_delta, first_choices = first_option[1:]
            second, second_delta, second_choices = second_option[1:]
            groups = (source, first, second)
            key = groups
            if key not in self.xor_decoders:
                self.xor_decoders[key] = SoftDecoder(self.offsets, np.concatenate([self.hashes[group] for group in groups]))
            decoder = self.xor_decoders[key]
            constraint_rows = np.concatenate([self.hashes[group] for group in groups] + [self.offsets[known]])
            basis = {}
            for row in constraint_rows:
                value = packed_integer(row)
                while value:
                    pivot = value.bit_length() - 1
                    if pivot not in basis:
                        basis[pivot] = value
                        break
                    value ^= basis[pivot]
            freedom = max(0, self.dimension - len(basis))
            threshold = 2.0 * freedom * np.log(2.0) + 22.0
            amplitude = mass * 0.5
            best_pair = None
            best_likelihood = threshold
            pair_likelihoods = {}
            for first_bucket, second_base, flip in itertools.product(first_choices, second_choices, range(2)):
                second_bucket = int(second_base) ^ (second_delta if flip else 0)
                locations = (bucket, int(first_bucket), second_bucket)
                unknown_values = np.zeros(self.rows)
                contributions = []
                forced = known.copy()
                forced_signs = orientation.copy()
                compatible = True
                for group, location, delta in [(first, int(first_bucket), first_delta),
                                                (second, second_bucket, second_delta)]:
                    for paired, multiplier in [(location, np.ones(self.rows)), (location ^ delta, xor_signs)]:
                        raw = physical[group, paired]
                        observed = raw * multiplier
                        bound = raw[0] - 2 * minimum_amplitude + max(0.45 * amplitude, 6 * np.max(self.sigma[group]))
                        certain = np.abs(raw) > max(bound, 0.55 * amplitude)
                        certain[0] = False
                        observed_signs = np.sign(observed)
                        if np.any(certain & forced & (observed_signs != forced_signs)):
                            compatible = False
                            break
                        forced_signs[certain] = observed_signs[certain]
                        forced |= certain
                        power = np.mean(observed[unknown] ** 2)
                        variance = max(power - amplitude ** 2, 0.3 * power,
                                       np.mean(self.sigma[group, unknown] ** 2))
                        unknown_values += observed / variance
                        contributions.append((observed, variance))
                    if not compatible:
                        break
                if not compatible:
                    continue
                values = unknown_values.copy()
                values[forced] = forced_signs[forced] * max(np.max(np.abs(values)), 1.0) * 1000.0
                hash_bits = np.concatenate([((location >> np.arange(self.hash_width)) & 1)
                                             for location in locations]).astype(np.uint8)
                decoded = decoder.decode(values, hash_bits, order=2, breadth=40, number=3)
                for bits in decoded:
                    signature = self.signatures(bits[None])[0]
                    if np.any(signature[forced] * forced_signs[forced] < 0):
                        continue
                    likelihood = 0.0
                    for observed, variance in contributions:
                        likelihood += np.sum(2 * amplitude * signature[unknown] * observed[unknown] - amplitude ** 2) / variance
                    if likelihood < threshold:
                        continue
                    counterpart = bits ^ difference
                    pair_key = tuple(sorted((bytes(bits), bytes(counterpart))))
                    pair_likelihoods[pair_key] = max(likelihood, pair_likelihoods.get(pair_key, -np.inf))
                    accepted = True
                    if self.groups > 3:
                        check_locations = self.locations(np.stack((bits, counterpart)))
                        for group in range(self.groups):
                            if group in groups:
                                continue
                            total = 0.0
                            variance_sum = 0.0
                            for row, check_bits in enumerate((bits, counterpart)):
                                check_signs = signature if row == 0 else signature * xor_signs
                                matched = self.residual[group, check_locations[group, row], 1:] * check_signs[1:]
                                total += np.mean(matched)
                                variance_sum += max(np.var(matched), np.mean(self.sigma[group, 1:] ** 2)) / (self.rows - 1)
                            if total < 3.0 * np.sqrt(variance_sum):
                                accepted = False
                                break
                    if accepted and likelihood > best_likelihood:
                        best_likelihood = likelihood
                        best_pair = (bits, counterpart)
                if time.monotonic() - self.started > 95:
                    break
            ranked_likelihoods = sorted(pair_likelihoods.values(), reverse=True)
            separated = len(ranked_likelihoods) < 2 or ranked_likelihoods[0] - ranked_likelihoods[1] > 10.0
            if best_pair is not None and separated:
                for item in best_pair:
                    entry = bytes(item)
                    if entry not in self.known and entry not in seen and entry not in self.blocked:
                        seen.add(entry)
                        proposals.append(item)
            if time.monotonic() - self.started > 95:
                break
        proposals = proposals[:max(0, self.capacity - len(self.bits))]
        if not proposals:
            return 0
        self.bits = np.concatenate((self.bits, np.array(proposals, dtype=np.uint8)))
        self.known.update(bytes(bits) for bits in proposals)
        self.fit()
        return len(proposals)

    def triples(self):
        held_out = min(16, (self.rows - self.extra_start) // 2)
        training_end = self.rows - held_out
        normalized = []
        powers = []
        for group in range(self.groups):
            values = self.residual[group, :, 1:training_end]
            power = np.mean(values ** 2, axis=1)
            norm = np.sqrt(np.sum(values ** 2, axis=1))
            normalized.append(values / np.maximum(norm[:, None], 1e-30))
            powers.append(np.maximum(power, np.mean(self.sigma[group, 1:training_end] ** 2)))
        correlations = {}
        for first in range(self.groups):
            for second in range(first + 1, self.groups):
                correlations[first, second] = normalized[first] @ normalized[second].T
        options = []
        for groups in itertools.combinations(range(self.groups), 3):
            first, second, third = groups
            first_second = correlations[first, second]
            first_third = correlations[first, third]
            second_third = correlations[second, third]
            choices = min(3, self.buckets)
            best = np.argpartition(first_second, -choices, axis=1)[:, -choices:]
            for first_bucket in range(self.buckets):
                for second_bucket in best[first_bucket]:
                    pair_score = first_second[first_bucket, second_bucket]
                    if pair_score < 0.25:
                        continue
                    combined_score = first_third[first_bucket] + second_third[second_bucket]
                    third_choices = min(2, self.buckets)
                    thirds = np.argpartition(combined_score, -third_choices)[-third_choices:]
                    for third_bucket in thirds:
                        score = (pair_score + combined_score[third_bucket]) / 3
                        if score > 0.32 and min(first_third[first_bucket, third_bucket], second_third[second_bucket, third_bucket]) > 0.16:
                            options.append((score, groups, (first_bucket, int(second_bucket), int(third_bucket))))
        if self.groups > 3:
            extended = {}
            for score, groups, locations in sorted(options, reverse=True)[:600]:
                mapping = dict(zip(groups, locations))
                compatible = True
                for other in range(self.groups):
                    if other in mapping:
                        continue
                    similarity = np.zeros(self.buckets)
                    for group, location in mapping.items():
                        if group < other:
                            similarity += correlations[group, other][location]
                        else:
                            similarity += correlations[other, group][:, location]
                    similarity /= len(mapping)
                    location = int(np.argmax(similarity))
                    if similarity[location] < 0.22:
                        compatible = False
                        break
                    mapping[other] = location
                if compatible:
                    full_locations = tuple(mapping[group] for group in range(self.groups))
                    total = 0.0
                    for first, second in itertools.combinations(range(self.groups), 2):
                        total += correlations[first, second][mapping[first], mapping[second]]
                    average = total / (self.groups * (self.groups - 1) / 2) + 0.025
                    extended[full_locations] = max(average, extended.get(full_locations, 0.0))
            options.extend((score, tuple(range(self.groups)), locations) for locations, score in extended.items())
        options.sort(reverse=True)
        proposals = []
        seen = set()
        for score, groups, locations in options[:600]:
            if groups not in self.triple_decoders:
                self.triple_decoders[groups] = SoftDecoder(self.offsets, np.concatenate([self.hashes[group] for group in groups]))
            combined = np.zeros(self.rows)
            total_precision = 0.0
            for group, location in zip(groups, locations):
                precision = 1 / powers[group][location]
                combined += self.residual[group, location] * precision
                total_precision += precision
            combined /= total_precision
            values = combined.copy()
            values[training_end:] = 0.0
            hash_bits = np.concatenate([((location >> np.arange(self.hash_width)) & 1)
                                         for location in locations]).astype(np.uint8)
            decoded = self.triple_decoders[groups].decode(values, hash_bits, order=3, breadth=36, number=2)
            for bits in decoded:
                key = bytes(bits)
                if key in self.known or key in seen or key in self.blocked:
                    continue
                signature = self.signatures(bits[None])[0]
                matched = combined * signature
                if np.any(matched[training_end:] <= 0):
                    continue
                estimate = np.mean(matched[1:training_end])
                check_estimate = np.mean(matched[training_end:])
                if estimate <= max(self.floor * 0.02, 4 * np.median(self.sigma) / np.sqrt(self.groups * self.rows)):
                    continue
                if not 0.5 * estimate < check_estimate < 1.6 * estimate:
                    continue
                if self.groups > 3:
                    check_locations = self.locations(bits[None])[:, 0]
                    numerator = 0.0
                    precision_sum = 0.0
                    for group in range(self.groups):
                        if group in groups:
                            continue
                        observed = self.residual[group, check_locations[group], 1:] * signature[1:]
                        variance = max(np.var(observed), np.mean(self.sigma[group, 1:] ** 2)) / (self.rows - 1)
                        numerator += np.mean(observed) / variance
                        precision_sum += 1 / variance
                    if numerator < 5 * np.sqrt(precision_sum):
                        continue
                seen.add(key)
                proposals.append(bits)
            if time.monotonic() - self.started > 98:
                break
        proposals = proposals[:max(0, self.capacity - len(self.bits))]
        if not proposals:
            return 0
        self.bits = np.concatenate((self.bits, np.array(proposals, dtype=np.uint8)))
        self.known.update(bytes(bits) for bits in proposals)
        self.fit()
        return len(proposals)

    def restart(self):
        signs = self.signatures(self.bits)
        locations = self.locations(self.bits)
        confidence = np.zeros(len(self.bits))
        for group in range(self.groups):
            matched = self.residual[group, locations[group], 1:] * signs[:, 1:] + self.probabilities[:, None]
            average = np.mean(matched, axis=1)
            scatter = np.maximum(np.var(matched, axis=1), np.mean(self.sigma[group, 1:] ** 2))
            confidence = np.maximum(confidence, average / np.sqrt(scatter))
        eligible = np.array([bytes(bits) not in self.trusted for bits in self.bits])
        eligible &= (self.probabilities > max(1.1 * np.median(self.sigma), self.floor * 0.1)) & (confidence < 1.3)
        discarded = np.flatnonzero(eligible)
        if not len(discarded):
            return 0
        discarded = discarded[np.argsort(confidence[discarded])[:min(160, max(16, len(self.bits) // 2))]]
        keep = np.ones(len(self.bits), dtype=bool)
        keep[discarded] = False
        for index in discarded:
            key = bytes(self.bits[index])
            self.archive[key] = max(float(self.probabilities[index]), self.archive.get(key, 0.0))
            self.blocked.add(key)
        self.bits = self.bits[keep]
        self.known = {bytes(bits) for bits in self.bits}
        self.fit()
        return len(discarded)

    def adapt_weights(self):
        power = np.mean(self.residual[:, :, 1:] ** 2, axis=2)
        noise_power = np.mean(self.sigma[:, 1:] ** 2, axis=1)
        extra = np.maximum(power - noise_power[:, None] * (1 + 2 * np.sqrt(2 / (self.rows - 1))), 0.0)
        typical = np.median(extra, axis=1)
        if not np.any(typical > 0.1 * noise_power) and not np.any(extra > noise_power[:, None]):
            return
        extra = 0.75 * extra + 0.25 * typical[:, None]
        self.fit_weights = np.median(self.sigma) ** 2 / (self.sigma[:, None, :] ** 2 + extra[:, :, None])
        self.uniform_norm = np.sum(self.uniform ** 2 * self.fit_weights)
        self.uniform_data = np.sum(self.uniform * self.values * self.fit_weights)
        self.fit()

    def solve(self):
        stagnant = 0
        restarts = 0
        for iteration in range(512):
            if time.monotonic() - self.started > 102:
                break
            added = self.direct()
            if added:
                stagnant = 0
                continue
            added = self.soft(order=1 if stagnant == 0 else 2)
            if added:
                stagnant = 0
                continue
            added = self.refine()
            if added:
                stagnant = 0
                continue
            if stagnant >= 1:
                added = self.refine(deep=True)
                if added:
                    stagnant = 0
                    continue
                added = self.doubletons()
                if added:
                    stagnant = 0
                    continue
                if stagnant >= 2:
                    added = self.triples()
                    if added:
                        stagnant = 0
                        continue
                added = self.pairs(order=1 if stagnant == 1 else 2)
                if added:
                    stagnant = 0
                    continue
            stagnant += 1
            if stagnant >= 3:
                if restarts < 2 and time.monotonic() - self.started < 80 and self.restart():
                    restarts += 1
                    stagnant = 0
                    continue
                break
        if self.archive:
            additional = [np.frombuffer(key, dtype=np.uint8) for key, probability in
                          sorted(self.archive.items(), key=lambda item: -item[1]) if key not in self.known]
            additional = additional[:max(0, self.capacity - len(self.bits))]
            if additional:
                self.bits = np.concatenate((self.bits, np.array(additional, dtype=np.uint8)))
                self.fit()
        self.adapt_weights()
        keep = np.flatnonzero((self.probabilities[1:] > np.maximum(3.5 * self.fit_std[1:], self.floor * 0.01))) + 1
        self.bits = self.bits[np.concatenate(([0], keep))]
        self.fit()
        ordering = (np.argsort(self.probabilities[1:])[::-1] + 1)[:self.maximum]
        ordering = ordering[self.probabilities[ordering] > 0]
        selected = self.bits[ordering]
        paulis = np.array([0, 3, 1, 2], dtype=np.uint8)[2 * selected[:, 0::2] + selected[:, 1::2]]
        return paulis, self.probabilities[ordering], self.probabilities[0]


def main():
    with np.load(sys.argv[1], allow_pickle=False) as data:
        reconstruction = Reconstruction(data)
    paulis, probabilities, identity = reconstruction.solve()
    np.savez(sys.argv[2], paulis=paulis.astype(np.uint8),
             probabilities=probabilities.astype(np.float64), p_identity=np.float64(identity))


if __name__ == '__main__':
    main()
