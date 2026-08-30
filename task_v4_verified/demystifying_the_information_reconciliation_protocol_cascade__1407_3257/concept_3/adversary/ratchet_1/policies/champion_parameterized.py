import heapq
import itertools
import json
import math
import sys


CORE_SIZE = 6
CONTRACT = json.loads(open('/task/contract.json').read())
FRAME_LIMIT = CONTRACT['frames']
QUERY_LIMIT = CONTRACT['parity_queries']
FRAME_QUERY_LIMIT = CONTRACT['queries_per_frame']
NOISE_GRID = tuple(1 / denominator if denominator else 0.00001 for denominator in CONTRACT['contamination_denominators'])
NOISE_COUNT = len(NOISE_GRID)


def topologies(size=CORE_SIZE):
    result = []
    for triple in itertools.combinations(range(size), 3):
        if size == 6 and 0 not in triple:
            continue
        pair = [site for site in range(size) if site not in triple]
        edges = list(itertools.combinations(triple, 2)) + list(itertools.combinations(pair, 2))
        result.append((0, edges))
    for order in itertools.permutations(range(size)):
        if size == 6:
            if order[0] == 0 and order[1] < order[-1]:
                result.append((1, list(zip(order, order[1:] + order[:1]))))
        elif order[0] < order[-1]:
            result.append((1, list(zip(order, order[1:]))))
    return result


TOPOLOGIES = {size: topologies(size) for size in (5, 6)}


class LocalModel:
    def __init__(self, core):
        self.core = core
        self.size = len(core)
        self.index = {site: index for index, site in enumerate(core)}
        self.models = []
        self.scores = []
        self.probs = []
        self.entropies = []
        self.log_probs = []
        for family, edges in TOPOLOGIES[self.size]:
            adjacency = [[False] * self.size for unused in range(self.size)]
            for first, second in edges:
                adjacency[first][second] = True
                adjacency[second][first] = True
            for epsilon in NOISE_GRID:
                edge = (1 - epsilon) / 6 + epsilon / 31
                noise = epsilon / 31
                probabilities = []
                for source in range(self.size):
                    row = [0.0 if echo == source else edge if adjacency[source][echo] else noise for echo in range(self.size)]
                    row.append(1 - sum(row))
                    probabilities.append(row)
                self.models.append(family)
                self.probs.append(probabilities)
                self.entropies.append([-sum(probability * math.log(probability) for probability in row if probability) for row in probabilities])
                self.log_probs.append([[math.log(max(1e-15, probability)) for probability in row] for row in probabilities])
                self.scores.append(-math.log((10 if family == 0 else 60) * NOISE_COUNT))
        self.observations = 0
        self.hits = 0
        self.events = []
        self.cached_weights = None

    def update(self, source, echo):
        source_index = self.index[source]
        echo_index = self.index.get(echo, self.size)
        for model in range(len(self.scores)):
            self.scores[model] += self.log_probs[model][source_index][echo_index]
        self.cached_weights = None
        self.observations += 1
        self.hits += echo_index != self.size
        self.events.append((source, echo))

    def posterior(self):
        if self.cached_weights is not None:
            return self.cached_weights
        maximum = max(self.scores)
        weights = [math.exp(score - maximum) for score in self.scores]
        total = sum(weights)
        self.cached_weights = [weight / total for weight in weights]
        return self.cached_weights

    def probability(self):
        weights = self.posterior()
        return sum(weight for weight, family in zip(weights, self.models) if family == 1)

    def source(self, weights=None):
        if weights is None:
            weights = self.posterior()
        selected = 0
        best = -1
        for source in range(self.size):
            mixture = [0.0] * (self.size + 1)
            conditional_entropy = 0.0
            family_mixtures = [[0.0] * (self.size + 1) for unused in range(2)]
            family_weights = [0.0, 0.0]
            for model, weight in enumerate(weights):
                if weight < 1e-9:
                    continue
                family = self.models[model]
                family_weights[family] += weight
                conditional_entropy += weight * self.entropies[model][source]
                for echo, probability in enumerate(self.probs[model][source]):
                    mixture[echo] += weight * probability
                    family_mixtures[family][echo] += weight * probability
            entropy = -sum(probability * math.log(probability) for probability in mixture if probability)
            family_entropy = 0.0
            for family in range(2):
                if family_weights[family]:
                    family_entropy -= sum(probability * math.log(probability / family_weights[family]) for probability in family_mixtures[family] if probability)
            information = entropy - family_entropy + 0.15 * (entropy - conditional_entropy)
            if information > best:
                selected, best = source, information
        return self.core[selected]


class Policy:
    def __init__(self, exchange):
        self.exchange = exchange
        self.frames = 0
        self.queries = 0
        self.counts = [[0] * 32 for unused in range(32)]
        self.masks = [0x55 << (8 * site) for site in range(32)]
        self.trace = []

    def start(self, source):
        self.exchange({'op': 'start', 'source': source})
        self.frames += 1
        self.current = source
        self.frame_queries = 0

    def query(self, sites):
        mask = sum(self.masks[site] for site in sites)
        reply = self.exchange({'op': 'parity', 'mask': format(mask, 'x')})
        self.queries += 1
        self.frame_queries += 1
        return reply['value'] ^ int(self.current in sites)

    def full_echo(self, source, excluded=()):
        possible = [site for site in range(32) if site != source and site not in excluded]
        known = [site for site in possible if self.counts[source][site] + self.counts[site][source]]
        unknown_weight = max(0.06, (6 - len(excluded) - len(known)) / max(1, len(possible) - len(known)))
        heap = []
        serial = 0
        for site in possible:
            count = self.counts[source][site] + self.counts[site][source]
            weight = 1.0 + 0.08 * min(count, 6) if count else unknown_weight
            heapq.heappush(heap, (weight, serial, site, (site,)))
            serial += 1
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            heapq.heappush(heap, (left[0] + right[0], serial, (left[2], right[2], left[3]), left[3] + right[3]))
            serial += 1
        tree = heap[0][2]
        pending = [(tree, 0)]
        deepest = 0
        while pending:
            node, depth = pending.pop()
            if isinstance(node, tuple):
                pending.append((node[0], depth + 1))
                pending.append((node[1], depth + 1))
            else:
                deepest = max(deepest, depth)
        if deepest > FRAME_QUERY_LIMIT - self.frame_queries:
            sites = possible
            while len(sites) > 1:
                half = len(sites) // 2
                sites = sites[:half] if self.query(sites[:half]) else sites[half:]
            self.counts[source][sites[0]] += 1
            return sites[0]
        while isinstance(tree, tuple):
            left, right, sites = tree
            if len(sites) <= 16:
                choice = self.query(sites)
                tree = left if choice else right
            else:
                complement = [site for site in range(32) if site != source and site not in sites]
                choice = self.query(complement)
                tree = right if choice else left
        self.counts[source][tree] += 1
        return tree

    def restricted_echo(self, source, core):
        sites = [site for site in core if site != source]
        if not self.query(sites):
            return -1
        while len(sites) > 1:
            half = len(sites) // 2
            if self.query(sites[:half]):
                sites = sites[:half]
            else:
                sites = sites[half:]
        self.counts[source][sites[0]] += 1
        return sites[0]

    def discover(self, center, forbidden=None, maximum=45):
        initial = self.frames
        hits = 0
        while self.frames - initial < maximum and self.frames < FRAME_LIMIT - 7 and self.queries < QUERY_LIMIT - 10:
            self.start(center)
            confirmed = [site for site in range(32) if self.counts[center][site] >= 3]
            if len(confirmed) >= 2:
                if self.query(confirmed):
                    continue
                echo = self.full_echo(center, confirmed)
            else:
                echo = self.full_echo(center)
            if forbidden and echo in forbidden:
                hits += 1
                if hits >= 4 or self.counts[center][echo] >= 3:
                    return None
            ordered = sorted(range(32), key=lambda site: self.counts[center][site], reverse=True)
            if self.counts[center][ordered[CORE_SIZE - 1]] >= 3 and self.frames - initial >= 16:
                break
        core = sorted(range(32), key=lambda site: self.counts[center][site], reverse=True)[:CORE_SIZE]
        if len(core) == 6 and self.counts[center][core[-1]] < 3:
            core = core[:5]
        self.trace.append(('discover', center, self.frames - initial, [(site, self.counts[center][site]) for site in core], hits))
        return core

    def run_local(self, model, maximum, full, minimum=26, threshold=0.997, weights=None):
        initial = self.frames
        while self.frames - initial < maximum and self.frames < FRAME_LIMIT and self.queries < (QUERY_LIMIT - 8 if full else QUERY_LIMIT - 3):
            probability = model.probability()
            if model.observations >= minimum and (probability > threshold or probability < 1 - threshold):
                break
            source = model.source(weights)
            self.start(source)
            echo = self.full_echo(source) if full and model.observations < 20 else self.restricted_echo(source, model.core)
            model.update(source, echo)
        self.trace.append(('local', model.probability(), model.observations, model.hits, self.frames, self.queries))

    def joint(self, first, second):
        weights = [first.posterior(), second.posterior()]
        summaries = []
        for model, posterior in zip((first, second), weights):
            summary = [[0.0] * NOISE_COUNT for unused in range(2)]
            for index, weight in enumerate(posterior):
                summary[model.models[index]][index % NOISE_COUNT] += weight
            summaries.append(summary)
        combinations = [[0.0] * 2 for unused in range(2)]
        for first_family in range(2):
            for second_family in range(2):
                prior = 2 if first_family == second_family else 1
                combinations[first_family][second_family] = prior * sum(summaries[0][first_family][noise] * summaries[1][second_family][noise] for noise in range(NOISE_COUNT))
        total = sum(map(sum, combinations))
        probabilities = [combinations[0][0] / total, (combinations[0][1] + combinations[1][0]) / total, combinations[1][1] / total]
        marginals = [(combinations[1][0] + combinations[1][1]) / total, (combinations[0][1] + combinations[1][1]) / total]
        adjusted = []
        for component, model in enumerate((first, second)):
            other = summaries[1 - component]
            posterior = [weight * (2 * other[model.models[index]][index % NOISE_COUNT] + other[1 - model.models[index]][index % NOISE_COUNT]) for index, weight in enumerate(weights[component])]
            normalization = sum(posterior)
            adjusted.append([weight / normalization for weight in posterior])
        return probabilities, marginals, adjusted

    def run(self):
        center = 0
        core = self.discover(center)
        first = LocalModel(core)
        self.first = first
        self.run_local(first, 20, True)
        component = {center} | set(core)
        for source in [center] + core:
            component.update(site for site in range(32) if self.counts[source][site])
        second_core = None
        rejected = set()
        while second_core is None and self.frames < FRAME_LIMIT - 50 and self.queries < QUERY_LIMIT - 110:
            candidates = [site for site in range(32) if site not in component and site not in rejected]
            if not candidates:
                candidates = [site for site in range(32) if site not in core and site != center and site not in rejected]
            candidate = candidates[0]
            forbidden = {center} | set(core)
            forbidden.update(site for site in range(32) if sum(self.counts[source][site] for source in [center] + core) >= 3)
            second_core = self.discover(candidate, forbidden, maximum=min(45, FRAME_LIMIT - 40 - self.frames))
            if second_core is None:
                rejected.add(candidate)
                component.add(candidate)
        if second_core is None:
            probability = first.probability()
            return 'SS' if probability > 0.5 else 'RR'
        second = LocalModel(second_core)
        self.second = second
        while self.frames < FRAME_LIMIT and self.queries < QUERY_LIMIT - 3:
            probabilities, marginals, adjusted = self.joint(first, second)
            first_probability, second_probability = marginals
            if max(min(first_probability, 1 - first_probability), min(second_probability, 1 - second_probability)) < 0.0005:
                break
            component = 0 if min(first_probability, 1 - first_probability) > min(second_probability, 1 - second_probability) else 1
            model = (first, second)[component]
            self.run_local(model, 1, False, minimum=1000, weights=adjusted[component])
        probabilities, marginals, adjusted = self.joint(first, second)
        return ('RR', 'RS', 'SS')[max(range(3), key=lambda index: probabilities[index])]


def exchange(request):
    print(json.dumps(request, separators=(',', ':')), flush=True)
    return json.loads(sys.stdin.readline())


def main():
    json.loads(sys.stdin.readline())
    policy = Policy(exchange)
    family = policy.run()
    exchange({'op': 'guess', 'family': family})


if __name__ == '__main__':
    main()
