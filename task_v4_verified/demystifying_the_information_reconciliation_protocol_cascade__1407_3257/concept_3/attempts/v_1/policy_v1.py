import heapq
import itertools
import json
import math
import sys


def topologies():
    result = []
    for triple in itertools.combinations(range(5), 3):
        pair = [site for site in range(5) if site not in triple]
        edges = list(itertools.combinations(triple, 2)) + [tuple(pair)]
        result.append((0, edges))
    for order in itertools.permutations(range(5)):
        if order[0] < order[-1]:
            result.append((1, list(zip(order, order[1:]))))
    return result


TOPOLOGIES = topologies()


class LocalModel:
    def __init__(self, core):
        self.core = core
        self.index = {site: index for index, site in enumerate(core)}
        self.models = []
        self.scores = []
        self.probs = []
        for family, edges in TOPOLOGIES:
            adjacency = [[False] * 5 for unused in range(5)]
            for first, second in edges:
                adjacency[first][second] = True
                adjacency[second][first] = True
            for epsilon in (0.00001, 1 / 32, 1 / 16):
                edge = (1 - epsilon) / 6 + epsilon / 31
                noise = epsilon / 31
                probabilities = []
                for source in range(5):
                    row = [0.0 if echo == source else edge if adjacency[source][echo] else noise for echo in range(5)]
                    row.append(1 - sum(row))
                    probabilities.append(row)
                self.models.append(family)
                self.probs.append(probabilities)
                self.scores.append(-math.log(30 if family == 0 else 180))
        self.observations = 0
        self.hits = 0

    def update(self, source, echo):
        source_index = self.index[source]
        echo_index = self.index.get(echo, 5)
        for model in range(len(self.scores)):
            self.scores[model] += math.log(max(1e-15, self.probs[model][source_index][echo_index]))
        self.observations += 1
        self.hits += echo_index != 5

    def posterior(self):
        maximum = max(self.scores)
        weights = [math.exp(score - maximum) for score in self.scores]
        total = sum(weights)
        return [weight / total for weight in weights]

    def probability(self):
        weights = self.posterior()
        return sum(weight for weight, family in zip(weights, self.models) if family == 1)

    def source(self):
        weights = self.posterior()
        selected = 0
        best = -1
        for source in range(5):
            mixture = [0.0] * 6
            conditional_entropy = 0.0
            family_mixtures = [[0.0] * 6 for unused in range(2)]
            family_weights = [0.0, 0.0]
            for model, weight in enumerate(weights):
                if weight < 1e-9:
                    continue
                family = self.models[model]
                family_weights[family] += weight
                for echo, probability in enumerate(self.probs[model][source]):
                    mixture[echo] += weight * probability
                    family_mixtures[family][echo] += weight * probability
                    if probability:
                        conditional_entropy -= weight * probability * math.log(probability)
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

    def query(self, sites):
        mask = sum(self.masks[site] for site in sites)
        reply = self.exchange({'op': 'parity', 'mask': format(mask, 'x')})
        self.queries += 1
        return reply['value'] ^ int(self.current in sites)

    def full_echo(self, source):
        known = [site for site in range(32) if site != source and self.counts[source][site] + self.counts[site][source]]
        unknown_weight = max(0.06, (6 - len(known)) / max(1, 31 - len(known)))
        heap = []
        serial = 0
        for site in range(32):
            if site == source:
                continue
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
        if deepest > 8:
            sites = [site for site in range(32) if site != source]
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

    def discover(self, center, forbidden=None, maximum=28):
        initial = self.frames
        hits = 0
        while self.frames - initial < maximum and self.frames < 153 and self.queries < 470:
            self.start(center)
            echo = self.full_echo(center)
            if forbidden and echo in forbidden:
                hits += 1
                if hits >= 2:
                    return None
            ordered = sorted(range(32), key=lambda site: self.counts[center][site], reverse=True)
            if self.counts[center][ordered[4]] >= 2 and self.frames - initial >= 16:
                break
        core = sorted(range(32), key=lambda site: self.counts[center][site], reverse=True)[:5]
        self.trace.append(('discover', center, self.frames - initial, [(site, self.counts[center][site]) for site in core], hits))
        return core

    def run_local(self, model, maximum, full, minimum=26, threshold=0.997):
        initial = self.frames
        while self.frames - initial < maximum and self.frames < 160 and self.queries < (472 if full else 477):
            probability = model.probability()
            if model.observations >= minimum and (probability > threshold or probability < 1 - threshold):
                break
            source = model.source()
            self.start(source)
            echo = self.full_echo(source) if full else self.restricted_echo(source, model.core)
            model.update(source, echo)
        self.trace.append(('local', model.probability(), model.observations, model.hits, self.frames, self.queries))

    def run(self):
        center = 0
        core = self.discover(center)
        first = LocalModel(core)
        self.run_local(first, 49, True)
        component = {center} | set(core)
        for source in [center] + core:
            component.update(site for site in range(32) if self.counts[source][site])
        second_core = None
        rejected = set()
        while second_core is None and self.frames < 110 and self.queries < 370:
            candidates = [site for site in range(32) if site not in component and site not in rejected]
            if not candidates:
                candidates = [site for site in range(32) if site not in core and site != center and site not in rejected]
            candidate = candidates[0]
            second_core = self.discover(candidate, set(core), maximum=min(28, 116 - self.frames))
            if second_core is None:
                rejected.add(candidate)
                component.add(candidate)
                component.update(site for site in range(32) if self.counts[candidate][site])
        if second_core is None:
            probability = first.probability()
            return 'SS' if probability > 0.5 else 'RR'
        second = LocalModel(second_core)
        self.run_local(second, max(0, 160 - self.frames), False, minimum=26, threshold=0.999)
        while self.frames < 160 and self.queries < 477:
            first_probability = first.probability()
            second_probability = second.probability()
            if max(min(first_probability, 1 - first_probability), min(second_probability, 1 - second_probability)) < 0.001:
                break
            model = first if min(first_probability, 1 - first_probability) > min(second_probability, 1 - second_probability) else second
            self.run_local(model, 1, False, minimum=1000)
        first_probability = first.probability()
        second_probability = second.probability()
        probabilities = [(1 - first_probability) * (1 - second_probability), first_probability * (1 - second_probability) + second_probability * (1 - first_probability), first_probability * second_probability]
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
