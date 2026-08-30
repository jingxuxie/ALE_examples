import array
import heapq
import itertools
import json
import math
import operator
import random
import sys
import time


ALL = (1 << 32) - 1
ANCHORS = [85 << (8 * site) for site in range(32)]


def exchange(request):
    print(json.dumps(request, separators=(",", ":")), flush=True)
    response = sys.stdin.readline()
    if not response:
        raise RuntimeError("oracle closed")
    return json.loads(response)


def structures():
    result = [[], []]
    for partners in itertools.combinations(range(1, 6), 2):
        group = (0,) + partners
        other = tuple(site for site in range(6) if site not in group)
        result[0].append(list(itertools.combinations(group, 2)) + list(itertools.combinations(other, 2)))
    for order in itertools.permutations(range(1, 6)):
        if order[0] < order[-1]:
            cycle = (0,) + order
            result[1].append([(cycle[index], cycle[(index + 1) % 6]) for index in range(6)])
    return result


STRUCTURES = structures()


class LocalModel:
    def __init__(self, root, counts, contamination=.20, subset_limit=220):
        self.root = root
        self.sites = sorted((site for site in range(32) if counts[site]), key=lambda site: (-counts[site], site))
        self.sources = self.sites[:min(4, len(self.sites))]
        self.pool = sum(1 << site for site in self.sites)
        self.contamination = contamination
        size = len(self.sites)
        high = (1 - contamination) / 6 + contamination / 31
        low = contamination / 31
        middle = (1 - contamination) / 50 + low
        outer = (1 - low - 6 * middle) / 24
        ratio = math.log(high / low)
        subsets = []
        for missing in range(min(2, 31 - size) + 1):
            for known in itertools.combinations(range(size), 6 - missing):
                score = ratio * sum(counts[self.sites[index]] for index in known)
                score += math.log(math.comb(31 - size, missing))
                subsets.append((score, known + tuple(range(size, size + missing))))
        subsets.sort(reverse=True)
        maximum = subsets[0][0]
        masses = [math.exp(score - maximum) for score, members in subsets]
        target_mass = sum(masses) * .9999
        retained_mass = 0.0
        retained_count = 0
        while retained_count < min(subset_limit, len(subsets)) and retained_mass < target_mass:
            retained_mass += masses[retained_count]
            retained_count += 1
        subsets = subsets[:retained_count]
        self.weights = [[], []]
        self.members = [[], []]
        self.full_members = [[], []]
        self.groups = [[], []]
        self.history = []
        self.likelihoods = [[[] for source in self.sources] for family in range(2)]
        for family in range(2):
            for source_index in range(len(self.sources)):
                self.likelihoods[family][source_index] = [array.array('d') for outcome in range(size + 1)]
            for score, members in subsets:
                member_set = set(members)
                for edges in STRUCTURES[family]:
                    neighbors = [set() for source in range(6)]
                    local_neighbors = [set() for source in range(6)]
                    for first, second in edges:
                        neighbors[first].add(members[second])
                        neighbors[second].add(members[first])
                        local_neighbors[first].add(second)
                        local_neighbors[second].add(first)
                    self.weights[family].append(math.exp(score - maximum) / len(STRUCTURES[family]))
                    self.members[family].append(tuple(index for index in members if index < size))
                    self.full_members[family].append(members)
                    if family == 0:
                        group = tuple(sorted({0} | local_neighbors[0]))
                    else:
                        group = tuple(sorted({0} | {target for neighbor in local_neighbors[0] for target in local_neighbors[neighbor]}))
                    self.groups[family].append((group, tuple(index for index in range(6) if index not in group)))
                    for source_index in range(len(self.sources)):
                        vectors = self.likelihoods[family][source_index]
                        if source_index in member_set:
                            adjacent = neighbors[members.index(source_index)]
                            probabilities = [0 if target == source_index else high if target in adjacent else low if target in member_set else middle for target in range(size)]
                        else:
                            probabilities = [0 if target == source_index else middle if target in member_set else outer for target in range(size)]
                        probabilities.append(1 - sum(probabilities))
                        for outcome, probability in enumerate(probabilities):
                            vectors[outcome].append(probability)
        self.normalize()
        self.profile = None

    def normalize(self):
        total = sum(self.weights[0]) + sum(self.weights[1])
        for family in range(2):
            self.weights[family] = [weight / total for weight in self.weights[family]]

    def probability(self):
        return sum(self.weights[0])

    def membership(self):
        result = [0.0] * 32
        for family in range(2):
            for weight, members in zip(self.weights[family], self.members[family]):
                for index in members:
                    result[self.sites[index]] += weight
        return result

    def prune(self):
        for family in range(2):
            weights = self.weights[family]
            threshold = max(weights) * 1e-8
            retained = [index for index, weight in enumerate(weights) if weight >= threshold]
            if len(retained) > .8 * len(weights):
                continue
            self.weights[family] = [weights[index] for index in retained]
            self.members[family] = [self.members[family][index] for index in retained]
            self.full_members[family] = [self.full_members[family][index] for index in retained]
            self.groups[family] = [self.groups[family][index] for index in retained]
            for source_index in range(len(self.sources)):
                self.likelihoods[family][source_index] = [array.array('d', (vector[index] for index in retained)) for vector in self.likelihoods[family][source_index]]
        self.normalize()

    def predict(self):
        priors = [sum(weights) for weights in self.weights]
        membership = self.membership()
        profiles = []
        for source_index in range(len(self.sources)):
            if source_index >= 3 and membership[self.sources[source_index]] < .50:
                continue
            marginal = []
            for family in range(2):
                marginal.append([sum(map(operator.mul, self.weights[family], vector)) for vector in self.likelihoods[family][source_index]])
            probabilities = [left + right for left, right in zip(*marginal)]
            information = 0
            for family in range(2):
                for outcome, value in enumerate(marginal[family]):
                    if value > 0 and priors[family] > 0:
                        information += value * math.log(value / (priors[family] * probabilities[outcome]))
            profiles.append((information, source_index, probabilities))
        self.profile = max(profiles)
        return self.profile

    def update(self, source_index, outcomes):
        self.history.append((source_index, list(outcomes)))
        for family in range(2):
            vectors = self.likelihoods[family][source_index]
            if len(outcomes) == 1:
                likelihood = vectors[outcomes[0]]
            else:
                likelihood = map(sum, zip(*(vectors[outcome] for outcome in outcomes)))
            self.weights[family] = list(map(operator.mul, self.weights[family], likelihood))
        self.normalize()

    def refine(self):
        outside = len(self.sites)
        increment = (1 - self.contamination) / 6
        low = self.contamination / 31
        corrected = []
        rng = random.Random(645251)
        for family in range(2):
            weights = self.weights[family]
            ranked = sorted(range(len(weights)), key=weights.__getitem__, reverse=True)
            selected = {index: weights[index] for index in ranked[:128]}
            remaining = ranked[128:]
            remainder_mass = sum(weights[index] for index in remaining)
            if remainder_mass > 1e-12:
                step = remainder_mass / 96
                threshold = rng.random() * step
                pointer = 0
                cumulative = weights[remaining[0]]
                for sample in range(96):
                    while cumulative < threshold and pointer + 1 < len(remaining):
                        pointer += 1
                        cumulative += weights[remaining[pointer]]
                    index = remaining[pointer]
                    selected[index] = selected.get(index, 0.0) + step
                    threshold += step
            evidence = 0.0
            for model_index, weight in selected.items():
                members = self.full_members[family][model_index]
                partition, other_partition = self.groups[family][model_index]
                positions = [members.index(source) if source in members else -1 for source in range(len(self.sources))]
                nuisance = {target: [1.0] * 6 for target in range(outside) if target not in members}
                initial = [[vector[model_index] for vector in self.likelihoods[family][source]] for source in range(len(self.sources))]
                probabilities = [list(row) for row in initial]
                log_ratio = 0.0
                for source, outcomes in self.history:
                    mass = sum(probabilities[source][outcome] for outcome in outcomes)
                    baseline = sum(initial[source][outcome] for outcome in outcomes)
                    log_ratio += math.log(max(1e-100, mass) / baseline)
                    position = positions[source]
                    if position < 0:
                        continue
                    exterior_included = outside in outcomes
                    for target, odds in nuisance.items():
                        sign = int(target in outcomes) - int(exterior_included)
                        if not sign:
                            continue
                        first_sum = sum(odds[index] for index in partition)
                        second_sum = sum(odds[index] for index in other_partition)
                        denominator = 16 + first_sum * second_sum
                        neighbor_probability = odds[position] * (second_sum if position in partition else first_sum) / denominator
                        positive = max(1e-100, mass + sign * increment * (1 - neighbor_probability))
                        negative = max(1e-100, mass - sign * increment * neighbor_probability)
                        odds[position] = min(1e30, max(1e-30, odds[position] * positive / negative))
                        first_sum = sum(odds[index] for index in partition)
                        second_sum = sum(odds[index] for index in other_partition)
                        denominator = 16 + first_sum * second_sum
                        for changed_source, changed_position in enumerate(positions):
                            if changed_position < 0:
                                continue
                            probability = odds[changed_position] * (second_sum if changed_position in partition else first_sum) / denominator
                            old_probability = probabilities[changed_source][target]
                            new_probability = low + increment * probability
                            maximum = old_probability + probabilities[changed_source][outside] - low * (32 - outside) - increment
                            new_probability = min(new_probability, max(low, maximum))
                            probabilities[changed_source][target] = new_probability
                            probabilities[changed_source][outside] += old_probability - new_probability
                evidence += weight * math.exp(max(-20, min(20, log_ratio)))
            corrected.append(evidence)
        return corrected[0] / sum(corrected)

    def sample_rows(self, source_index, rng, samples=32):
        result = []
        for family in range(2):
            weights = self.weights[family]
            total = sum(weights)
            if total < 1e-10:
                continue
            step = total / samples
            threshold = rng.random() * step
            cumulative = weights[0]
            index = 0
            vectors = self.likelihoods[family][source_index]
            for sample in range(samples):
                while cumulative < threshold and index + 1 < len(weights):
                    index += 1
                    cumulative += weights[index]
                result.append((family, total / samples, [vector[index] for vector in vectors]))
                threshold += step
        return result


class Policy:
    def __init__(self, communicate=exchange):
        self.exchange = communicate
        self.frames = 0
        self.queries = 0
        self.counts = [[0] * 32 for site in range(32)]
        self.seen = [0] * 32
        self.rng = random.Random(573191)
        self.models = []
        self.roots = set()
        self.started_cpu = time.process_time()
        self.started_wall = time.monotonic()

    def start(self, source):
        self.exchange({"op": "start", "source": source})
        self.frames += 1
        self.frame_queries = 0

    def query(self, source, sites):
        flipped = sites.bit_count() > 16
        if flipped:
            sites ^= ALL
        mask = 0
        remaining = sites
        while remaining:
            lowest = remaining & -remaining
            mask |= ANCHORS[lowest.bit_length() - 1]
            remaining -= lowest
        reply = self.exchange({"op": "parity", "mask": format(mask, "x")})
        self.queries += 1
        self.frame_queries += 1
        return reply["value"] ^ ((sites >> source) & 1) ^ flipped

    def decode(self, source, categories, probabilities, allowance=8):
        queue = []
        counter = 0
        for category, (sites, probability) in enumerate(zip(categories, probabilities)):
            if sites and probability > 0:
                heapq.heappush(queue, (probability, counter, sites, [category], None, None))
                counter += 1
        while len(queue) > 1:
            left = heapq.heappop(queue)
            right = heapq.heappop(queue)
            heapq.heappush(queue, (left[0] + right[0], counter, left[2] | right[2], left[3] + right[3], left, right))
            counter += 1
        node = queue[0]
        while node[4] is not None and self.frame_queries < allowance and self.queries < 480:
            value = self.query(source, node[4][2])
            node = node[4] if value else node[5]
        return node[2], node[3]

    def record(self, source, echo):
        self.counts[source][echo] += 1
        self.seen[echo] += 1

    def informative_decode(self, source, categories, rows, allowance):
        allowed = [index for index, sites in enumerate(categories) if sites]
        while len(allowed) > 1 and self.frame_queries < allowance and self.queries < 480:
            conditioned = []
            priors = [0.0, 0.0]
            marginal = [[0.0] * len(categories) for family in range(2)]
            for family, weight, probabilities in rows:
                mass = sum(probabilities[index] for index in allowed)
                adjusted = weight * mass
                priors[family] += adjusted
                conditioned.append((family, adjusted, [probabilities[index] / mass if index in allowed else 0 for index in range(len(categories))]))
                for index in allowed:
                    marginal[family][index] += weight * probabilities[index]
            total = sum(priors)
            ordered = sorted(allowed, key=lambda index: marginal[0][index] / max(1e-100, marginal[1][index]))
            candidates = {tuple(sorted(ordered[:cut])) for cut in range(1, len(ordered))}
            candidates.update((index,) for index in allowed)
            for repeat in range(16):
                selected = tuple(index for index in allowed if self.rng.random() < .5)
                if selected and len(selected) < len(allowed):
                    candidates.add(selected)
            best = -1
            chosen = None
            for selected in candidates:
                yes_family = [0.0, 0.0]
                conditional_entropy = 0.0
                for family, weight, probabilities in conditioned:
                    probability = sum(probabilities[index] for index in selected)
                    yes_family[family] += weight * probability
                    if 1e-12 < probability < 1 - 1e-12:
                        conditional_entropy -= weight * (probability * math.log(probability) + (1 - probability) * math.log1p(-probability))
                yes = sum(yes_family) / total
                if not 1e-12 < yes < 1 - 1e-12:
                    continue
                entropy = -yes * math.log(yes) - (1 - yes) * math.log1p(-yes)
                family_entropy = 0.0
                for family in range(2):
                    if priors[family] > 0:
                        probability = yes_family[family] / priors[family]
                        if 1e-12 < probability < 1 - 1e-12:
                            family_entropy -= priors[family] / total * (probability * math.log(probability) + (1 - probability) * math.log1p(-probability))
                information = entropy - family_entropy + .20 * (entropy - conditional_entropy / total)
                if information > best:
                    best = information
                    chosen = selected
            if chosen is None:
                chosen = allowed[:len(allowed) // 2]
            mask = 0
            for index in chosen:
                mask |= categories[index]
            value = self.query(source, mask)
            allowed = list(chosen) if value else [index for index in allowed if index not in chosen]
        mask = 0
        for index in allowed:
            mask |= categories[index]
        return mask, allowed

    def root_sample(self, source):
        self.roots.add(source)
        self.start(source)
        categories = [1 << target if target != source else 0 for target in range(32)]
        probabilities = [(self.counts[source][target] + .20) if target != source else 0 for target in range(32)]
        mask, outcomes = self.decode(source, categories, probabilities)
        if mask.bit_count() == 1:
            echo = mask.bit_length() - 1
            self.record(source, echo)
            return echo
        return -1

    def estimate_contamination(self):
        levels = (1 / 8, 1 / 6, 1 / 4)
        scores = []
        for contamination in levels:
            low = contamination / 31
            high = (1 - contamination) / 6 + low
            ratio = high / low
            score = 0.0
            for root in self.roots:
                coefficients = [1.0] + [0.0] * 6
                for site, count in enumerate(self.counts[root]):
                    if site == root:
                        continue
                    value = ratio ** count
                    for degree in range(6, 0, -1):
                        coefficients[degree] += value * coefficients[degree - 1]
                score += sum(self.counts[root]) * math.log(low) + math.log(coefficients[6])
            scores.append(score)
        maximum = max(scores)
        weights = [math.exp(score - maximum) for score in scores]
        return sum(weight * level for weight, level in zip(weights, levels)) / sum(weights)

    def same_probability(self, root, reference):
        counts = self.counts[root]
        inside = sum(counts[site] for site in reference)
        outside = sum(counts) - inside
        contamination = .20
        high = (1 - contamination) / 6 + contamination / 31
        low = contamination / 31
        terms = []
        for known in range(3):
            missing = 2 - known
            if missing > 6 - len(reference):
                continue
            multiplicity = math.comb(6 - len(reference), missing)
            for selected in itertools.combinations(reference, known):
                term = sum(counts[site] for site in selected) * math.log(high / low)
                term += outside * math.log((1 - known * high - (len(reference) - known) * low) / (1 - len(reference) * low))
                terms.append(term + math.log(multiplicity))
        maximum = max(terms)
        log_ratio = maximum + math.log(sum(math.exp(term - maximum) for term in terms) / 15)
        log_ratio += math.log(.22 / .78)
        return 1 / (1 + math.exp(-max(-700, min(700, log_ratio))))

    def run_local(self, root, maximum_frames, reveal_outside=0, model=None):
        if model is None:
            model = LocalModel(root, self.counts[root], self.estimate_contamination())
            self.models.append(model)
        for iteration in range(maximum_frames):
            if self.frames >= 160 or self.queries >= 480:
                break
            elapsed = time.process_time() - self.started_cpu
            if elapsed > (3.2 if len(self.models) == 1 else 6.2) or time.monotonic() - self.started_wall > 10.0:
                break
            probability = model.probability()
            if iteration >= 28 and (probability > .997 or probability < .003):
                break
            if iteration % 4 == 0:
                if iteration and iteration % 12 == 0:
                    model.prune()
                information, source_index, probabilities = model.predict()
            source = model.sources[source_index]
            categories = [1 << site if site != source else 0 for site in model.sites]
            categories.append(ALL ^ model.pool ^ (1 << root))
            categories[-1] |= 1 << root
            self.start(source)
            future_roots = 28 if len(self.models) == 1 else 0
            available = 480 - self.queries - 4 * future_roots
            future_local = max(1, 161 - self.frames - future_roots)
            allowance = min(3, max(1, available // future_local))
            rows = model.sample_rows(source_index, self.rng)
            mask, outcomes = self.informative_decode(source, categories, rows, allowance)
            model.update(source_index, outcomes)
            if mask.bit_count() == 1:
                self.record(source, mask.bit_length() - 1)
            elif reveal_outside and outcomes == [len(model.sites)] and self.frame_queries < 5:
                remaining = [1 << site if (mask >> site) & 1 else 0 for site in range(32)]
                identified, ignored = self.decode(source, remaining, [1] * 32, 8)
                if identified.bit_count() == 1:
                    self.record(source, identified.bit_length() - 1)
                reveal_outside -= 1
        return model.probability()

    def run(self):
        first_root = 0
        for iteration in range(30):
            self.root_sample(first_root)
            values = sorted(self.counts[first_root], reverse=True)
            if iteration >= 23 and values[5] >= 2:
                break
        first_probability = self.run_local(first_root, 52, 3)
        membership = self.models[0].membership()
        reference = sorted(range(32), key=lambda site: membership[site], reverse=True)[:6]
        reference = reference[:max(4, sum(membership[site] > .8 for site in reference))]
        rejected = {first_root, *reference}
        same_probability = 0
        while True:
            candidates = [site for site in range(32) if site not in rejected]
            preferred = [site for site in candidates if self.counts[first_root][site] == 1 and self.seen[site] == 1 and membership[site] < .04]
            if preferred:
                second_root = self.rng.choice(preferred)
            else:
                minimum = min(self.seen[site] for site in candidates)
                second_root = self.rng.choice([site for site in candidates if self.seen[site] == minimum])
            rejected.add(second_root)
            rejected_root = False
            for iteration in range(min(30, 160 - self.frames - 24)):
                self.root_sample(second_root)
                same_probability = self.same_probability(second_root, reference)
                if iteration >= 5 and same_probability > .96 and self.frames < 122:
                    rejected_root = True
                    break
                values = sorted(self.counts[second_root], reverse=True)
                if iteration >= 23 and values[5] >= 2:
                    break
            if not rejected_root:
                break
        second_probability = self.run_local(second_root, 160 - self.frames)
        if self.frames < 160 and self.queries < 480 and .003 < first_probability < .997:
            first_probability = self.run_local(first_root, 160 - self.frames, model=self.models[0])
        original = (first_probability, second_probability)
        if time.process_time() - self.started_cpu < 6.3 and time.monotonic() - self.started_wall < 10.0:
            first_probability = self.models[0].refine()
        if time.process_time() - self.started_cpu < 6.3 and time.monotonic() - self.started_wall < 10.0:
            second_probability = self.models[1].refine()
        print('refinement', original, (first_probability, second_probability), file=sys.stderr)
        probabilities = [first_probability * second_probability, first_probability * (1 - second_probability) + (1 - first_probability) * second_probability, (1 - first_probability) * (1 - second_probability)]
        family = ("RR", "RS", "SS")[max(range(3), key=lambda index: probabilities[index])]
        self.exchange({"op": "guess", "family": family})
        return family, (first_probability, second_probability, same_probability), (self.frames, self.queries)


def main():
    hello = json.loads(sys.stdin.readline())
    Policy().run()


if __name__ == "__main__":
    main()
