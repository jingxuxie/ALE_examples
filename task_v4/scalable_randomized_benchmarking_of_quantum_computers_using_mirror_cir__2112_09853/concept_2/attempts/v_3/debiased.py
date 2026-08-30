import math
import numpy as np
from variants import ImprovedPolicy, FocusedPolicy


class DebiasedPolicy(ImprovedPolicy):
    def posterior(self, samples=512, burn=250, thin=4):
        if not hasattr(self, 'chain_states'):
            self.chain_states = [self.state.copy(), self.state.copy()]
        outputs = []
        for chain in range(2):
            self.state = self.chain_states[chain]
            outputs.append(super().posterior(samples=samples//2, burn=burn, thin=thin))
            self.chain_states[chain] = self.state
        return np.concatenate(outputs)

    def candidate_pool(self, posterior):
        if self.spent < 768:
            return self.grid.pool(self.generator, 360, self.hello['max_matching_size'], varied=False)
        return super().candidate_pool(posterior)

    def select_batch(self, posterior, batch_size):
        candidates = self.candidate_pool(posterior)
        design, features = self.grid.features(candidates)
        candidate_rates = posterior[:, :self.rate_dimension] @ features.T
        mean_rates = candidate_rates.mean(axis=0)
        multipliers = np.array([1.1, 1.8])
        depths = np.clip(2*np.rint(multipliers[:, None]/mean_rates[None, :]/2), 2, 256).astype(int).ravel()
        candidate_rates = np.tile(candidate_rates, (1, len(multipliers)))
        design = np.tile(design, (len(multipliers), 1))
        probabilities = self.probabilities(posterior, design, candidate_rates, depths, (self.spent+16)/2000)
        centered = probabilities-probabilities.mean(axis=0)
        noise = np.mean(probabilities*(1-probabilities), axis=0)/32
        target_rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ self.proxy_features.T))
        covariance = centered.T @ centered / len(posterior)
        half = len(posterior)//2
        covariances = []
        numerators = []
        denominators = []
        outcomes = np.arange(33)
        coefficients = np.array([math.lgamma(33)-math.lgamma(success+1)-math.lgamma(33-success) for success in outcomes])
        for section in [slice(None, half), slice(half, None)]:
            rates = target_rates[section]
            precision = (0.003+0.1*rates)**-2
            optimal = np.sum(precision*rates, axis=0)/precision.sum(axis=0)
            residual = precision*(rates-optimal)
            target_centered = residual/np.sqrt(precision.mean(axis=0))
            candidate_probability = probabilities[section]
            candidate_centered = candidate_probability-candidate_probability.mean(axis=0)
            covariances.append(target_centered.T @ candidate_centered/half)
            likelihood = np.exp(np.log(candidate_probability)[:, :, None]*outcomes[None, None, :]
                                + np.log1p(-candidate_probability)[:, :, None]*(32-outcomes)[None, None, :]
                                + coefficients[None, None, :]).reshape(half, -1)
            numerators.append(residual.T @ likelihood/half)
            denominators.append(precision.T @ likelihood/half)
        exact_utility = ((numerators[0]*numerators[1]/np.maximum(1e-100, (denominators[0]+denominators[1])/2))
                         .reshape(len(optimal), len(depths), 33).sum(axis=(0, 2)))
        initial_utility = np.sum(covariances[0]*covariances[1], axis=0)/(np.diag(covariance)+noise)
        chosen = []
        forbidden = np.zeros(len(depths), dtype=bool)
        for index in range(batch_size):
            denominator = np.maximum(1e-9, np.diag(covariance)+noise)
            utility = np.sum(covariances[0]*covariances[1], axis=0)/denominator
            utility *= np.clip(exact_utility/np.maximum(initial_utility, 1e-20), 0.1, 10)
            utility[forbidden] = -1e100
            selected = int(np.argmax(utility))
            chosen.append((candidates[selected % len(candidates)], int(depths[selected])))
            column = covariance[:, selected].copy()
            for target_covariance in covariances:
                target_column = target_covariance[:, selected].copy()
                target_covariance -= np.outer(target_column, column)/denominator[selected]
            covariance -= np.outer(column, column)/denominator[selected]
            forbidden[selected % len(candidates)::len(candidates)] = True
        return chosen
