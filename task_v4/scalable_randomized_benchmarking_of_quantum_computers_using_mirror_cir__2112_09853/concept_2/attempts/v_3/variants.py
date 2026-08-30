import math
import numpy as np
from policy import Policy


class ExactPolicy(Policy):
    batch_size = 6
    depth_multipliers = (1.05, 1.8)

    def candidate_pool(self, posterior):
        return self.grid.pool(self.generator, 300, self.hello['max_matching_size'], varied=True)

    def posterior(self, samples=512, burn=450, thin=2):
        return super().posterior(samples=samples, burn=burn, thin=thin)

    def select_batch(self, posterior, batch_size):
        candidates = self.candidate_pool(posterior)
        design, features = self.grid.features(candidates)
        candidate_rates = posterior[:, :self.rate_dimension] @ features.T
        mean_rates = candidate_rates.mean(axis=0)
        multipliers = np.array(self.depth_multipliers)
        depths = np.clip(2*np.rint(multipliers[:, None]/mean_rates[None, :]/2), 2, 256).astype(int).ravel()
        candidate_rates = np.tile(candidate_rates, (1, len(multipliers)))
        design = np.tile(design, (len(multipliers), 1))
        probabilities = self.probabilities(posterior, design, candidate_rates, depths, (self.spent+16)/2000)
        centered = probabilities-probabilities.mean(axis=0)
        noise = np.mean(probabilities*(1-probabilities), axis=0)/32
        target_rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ self.proxy_features.T))
        precision = (0.003+0.1*target_rates)**-2
        optimal = np.sum(precision*target_rates, axis=0)/precision.sum(axis=0)
        residual = precision*(target_rates-optimal)
        target_centered = residual/np.sqrt(precision.mean(axis=0))
        covariance = centered.T @ centered / len(posterior)
        target_covariance = target_centered.T @ centered / len(posterior)
        outcomes = np.arange(33)
        coefficients = np.array([math.lgamma(33)-math.lgamma(success+1)-math.lgamma(33-success) for success in outcomes])
        likelihood = np.exp(np.log(probabilities)[:, :, None]*outcomes[None, None, :]
                            + np.log1p(-probabilities)[:, :, None]*(32-outcomes)[None, None, :]
                            + coefficients[None, None, :]).reshape(len(posterior), -1)
        numerator = residual.T @ likelihood
        denominator = precision.T @ likelihood
        exact_utility = ((numerator**2/np.maximum(1e-200, denominator)).reshape(len(optimal), len(depths), 33)
                         .sum(axis=(0, 2))/len(posterior))
        initial_utility = np.sum(target_covariance**2, axis=0)/(np.diag(covariance)+noise)
        chosen = []
        forbidden = np.zeros(len(depths), dtype=bool)
        for index in range(batch_size):
            denominator = np.maximum(1e-9, np.diag(covariance)+noise)
            utility = np.sum(target_covariance**2, axis=0)/denominator
            utility *= exact_utility/np.maximum(initial_utility, 1e-20)
            utility[forbidden] = -1
            selected = int(np.argmax(utility))
            chosen.append((candidates[selected % len(candidates)], int(depths[selected])))
            column = covariance[:, selected].copy()
            target_column = target_covariance[:, selected].copy()
            target_covariance -= np.outer(target_column, column)/denominator[selected]
            covariance -= np.outer(column, column)/denominator[selected]
            forbidden[selected % len(candidates)::len(candidates)] = True
        return chosen

    def run(self, exchange):
        while self.spent <= 2000-32:
            posterior = self.posterior()
            remaining = (2000-self.spent)//32
            batch_size = min(self.batch_size, remaining)
            for matching, depth in self.select_batch(posterior, batch_size):
                shots = 48 if self.spent == 1952 else 32
                observation = exchange({'type': 'experiment', 'matching': matching, 'depth': depth, 'shots': shots})
                self.observations.append(observation)
                self.spent += shots
        targets = exchange({'type': 'ready'})
        posterior = self.posterior(samples=2048, burn=1400, thin=4)
        unused, features = self.grid.features(targets['matchings'])
        rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ features.T))
        weights = (0.003+0.10*rates)**-2
        predictions = np.sum(weights*rates, axis=0)/weights.sum(axis=0)
        exchange({'type': 'final', 'predictions': predictions.tolist()})


class FocusedPolicy(ExactPolicy):
    def candidate_pool(self, posterior):
        candidates = self.grid.pool(self.generator, 240, self.hello['max_matching_size'], varied=True)
        pair_scores = posterior[:, 1+self.edge_count:self.rate_dimension].var(axis=0)
        pair_scores *= self.proxy_features[:, 1+self.edge_count:].mean(axis=0)
        selected = np.argsort(pair_scores)[-100:]
        candidates += [self.grid.pairs[index].tolist() for index in selected if pair_scores[index] > 1e-10]
        candidates += [[edge] for edge in range(self.edge_count)]
        for index in selected[-40:]:
            matching = self.grid.matching(self.generator, min(4, self.hello['max_matching_size']), self.grid.pairs[index])
            if matching is not None:
                candidates.append(matching)
        return candidates


class ImprovedPolicy(FocusedPolicy):
    sampler_name = '../sampler2.so'
