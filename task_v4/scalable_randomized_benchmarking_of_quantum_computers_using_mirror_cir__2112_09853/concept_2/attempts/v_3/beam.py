import numpy as np
from balanced import BalancedPolicy


class BeamPolicy(BalancedPolicy):
    def candidate_pool(self, posterior):
        maximum = self.hello['max_matching_size']
        minimum = max(3, maximum//2)
        candidates = self.grid.pool(self.generator, 180, maximum, varied=True)
        target_rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ self.proxy_features.T))
        precision = (0.003+0.1*target_rates)**-2
        optimal = np.sum(precision*target_rates, axis=0)/precision.sum(axis=0)
        target_centered = precision*(target_rates-optimal)/np.sqrt(precision.mean(axis=0))
        beams = [()]
        for size in range(1, maximum+1):
            available = set()
            for parent in beams:
                occupied = {vertex for edge in parent for vertex in self.grid.edges[edge]}
                for edge, endpoints in enumerate(self.grid.edges):
                    if not occupied.intersection(endpoints):
                        available.add(tuple(sorted(parent+(edge,))))
            available = sorted(available)
            if not available:
                break
            design, features = self.grid.features(available)
            rates = posterior[:, :self.rate_dimension] @ features.T
            depths = np.clip(2*np.rint(1.5/rates.mean(axis=0)/2), 2, 256).astype(int)
            probabilities = self.probabilities(posterior, design, rates, depths, (self.spent+16)/2000)
            centered = probabilities-probabilities.mean(axis=0)
            covariance = target_centered.T @ centered/len(posterior)
            variance = np.mean(centered**2, axis=0)+np.mean(probabilities*(1-probabilities), axis=0)/32
            utility = np.sum(covariance**2, axis=0)/variance
            order = np.argsort(utility)[::-1]
            beams = [available[index] for index in order[:5]]
            possible = order[5:min(60, len(order))]
            if len(possible):
                selected = self.generator.choice(possible, size=min(7, len(possible)), replace=False)
                beams += [available[index] for index in selected]
            if size >= minimum:
                candidates += [list(available[index]) for index in order[:24]]
        return [list(matching) for matching in dict.fromkeys(tuple(matching) for matching in candidates)]
