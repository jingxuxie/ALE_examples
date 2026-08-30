import math
import numpy as np
from variants import ExactPolicy


class EntropyPolicy(ExactPolicy):
    sampler_name = '../sampler2.so'

    def select_batch(self, posterior, batch_size):
        candidates = self.grid.pool(self.generator, 320, self.hello['max_matching_size'], varied=True)
        design, features = self.grid.features(candidates)
        candidate_rates = posterior[:, :self.rate_dimension] @ features.T
        mean_rates = candidate_rates.mean(axis=0)
        multipliers = np.array([1.05, 1.8])
        depths = np.clip(2*np.rint(multipliers[:, None]/mean_rates[None, :]/2), 2, 256).astype(int).ravel()
        candidate_rates = np.tile(candidate_rates, (1, len(multipliers)))
        design = np.tile(design, (len(multipliers), 1))
        probabilities = self.probabilities(posterior, design, candidate_rates, depths, (self.spent+16)/2000)
        centered = probabilities-probabilities.mean(axis=0)
        noise = np.mean(probabilities*(1-probabilities), axis=0)/32
        covariance = centered.T @ centered / len(posterior)
        outcomes = np.arange(33)
        coefficients = np.array([math.lgamma(33)-math.lgamma(success+1)-math.lgamma(33-success) for success in outcomes])
        log_likelihood = (np.log(probabilities)[:, :, None]*outcomes[None, None, :]
                          + np.log1p(-probabilities)[:, :, None]*(32-outcomes)[None, None, :]
                          + coefficients[None, None, :])
        likelihood = np.exp(log_likelihood)
        predictive = likelihood.mean(axis=0)
        information = np.sum((likelihood*log_likelihood).mean(axis=0)-predictive*np.log(np.maximum(1e-200, predictive)), axis=1)
        initial_utility = np.log1p(np.diag(covariance)/noise)
        chosen = []
        forbidden = np.zeros(len(depths), dtype=bool)
        for index in range(batch_size):
            denominator = np.maximum(1e-9, np.diag(covariance)+noise)
            utility = np.log1p(np.maximum(0,np.diag(covariance))/noise) * information/initial_utility
            utility[forbidden] = -1
            selected = int(np.argmax(utility))
            chosen.append((candidates[selected % len(candidates)], int(depths[selected])))
            column = covariance[:, selected].copy()
            covariance -= np.outer(column, column)/denominator[selected]
            forbidden[selected % len(candidates)::len(candidates)] = True
        return chosen
