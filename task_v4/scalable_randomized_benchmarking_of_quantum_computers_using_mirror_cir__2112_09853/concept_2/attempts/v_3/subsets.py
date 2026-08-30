import numpy as np
from variants import ExactPolicy


class SubsetPolicy(ExactPolicy):
    sampler_name = '../sampler2.so'

    def candidate_pool(self, posterior):
        candidates = self.grid.pool(self.generator, 220, self.hello['max_matching_size'], varied=True)
        pair_variance = posterior[:, 1+self.edge_count:self.rate_dimension].var(axis=0)
        if self.observations:
            parents = [record['matching'] for record in self.observations if len(record['matching']) >= 4]
            if parents:
                unused, parent_features = self.grid.features(parents)
                uncertainty = parent_features[:, 1+self.edge_count:] @ pair_variance
                uncertainty = np.maximum(1e-12, uncertainty)**1.5
                uncertainty /= uncertainty.sum()
                for attempt in range(240):
                    parent = parents[self.generator.choice(len(parents), p=uncertainty)]
                    size = int(self.generator.integers(3, len(parent)))
                    chosen = sorted(int(edge) for edge in self.generator.choice(parent, size=size, replace=False))
                    candidates.append(chosen)
        pair_scores = pair_variance * self.proxy_features[:, 1+self.edge_count:].mean(axis=0)
        pair_scores = np.maximum(pair_scores, 1e-15)
        pair_scores /= pair_scores.sum()
        for attempt in range(100):
            chosen = set()
            vertices = set()
            wanted = int(self.generator.choice([4, 4, 6, self.hello['max_matching_size']]))
            for trial in range(16):
                pair = self.grid.pairs[self.generator.choice(self.pair_count, p=pair_scores)]
                additional = set(map(int, pair))-chosen
                new_vertices = {vertex for edge in additional for vertex in self.grid.edges[edge]}
                if not new_vertices.intersection(vertices) and len(chosen)+len(additional) <= wanted:
                    chosen.update(additional)
                    vertices.update(new_vertices)
                if len(chosen) == wanted:
                    break
            if len(chosen) >= 3:
                candidates.append(sorted(chosen))
        if self.spent >= 1280:
            probability = (posterior[:, 1+self.edge_count:self.rate_dimension] > 0).mean(axis=0)
            candidates += [self.grid.pairs[index].tolist() for index in np.flatnonzero((probability > 0.25)&(probability < 0.85))]
        candidates = [list(matching) for matching in dict.fromkeys(tuple(matching) for matching in candidates)]
        return candidates


class SequentialPolicy(SubsetPolicy):
    batch_size = 3

    def posterior(self, samples=384, burn=250, thin=2):
        return super().posterior(samples=samples, burn=burn, thin=thin)
