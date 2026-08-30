import math
import numpy as np
from variants import ExactPolicy


class AllocationPolicy(ExactPolicy):
    sampler_name = '../sampler2.so'

    def select_actions(self, posterior):
        candidates = self.candidate_pool(posterior)
        candidates += [record['matching'] for record in self.observations]
        candidates = [list(matching) for matching in dict.fromkeys(tuple(matching) for matching in candidates)]
        design, features = self.grid.features(candidates)
        rates = posterior[:, :self.rate_dimension] @ features.T
        multipliers = np.array([1.05, 1.8])
        depths = np.clip(2*np.rint(multipliers[:, None]/rates.mean(axis=0)[None, :]/2), 2, 256).astype(int).ravel()
        rates = np.tile(rates, (1, 2))
        design = np.tile(design, (2, 1))
        probabilities = self.probabilities(posterior, design, rates, depths, (self.spent+16)/2000)
        centered = probabilities-probabilities.mean(axis=0)
        variance_per_shot = np.mean(probabilities*(1-probabilities), axis=0)
        covariance = centered.T @ centered / len(posterior)
        target_rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ self.proxy_features.T))
        precision = (0.003+0.1*target_rates)**-2
        optimal = np.sum(precision*target_rates, axis=0)/precision.sum(axis=0)
        residual = precision*(target_rates-optimal)
        target_centered = residual/np.sqrt(precision.mean(axis=0))
        target_covariance = target_centered.T @ centered/len(posterior)
        allocations = [32,64]
        exact = []
        for shots in allocations:
            outcomes = np.arange(shots+1)
            coefficients = np.array([math.lgamma(shots+1)-math.lgamma(success+1)-math.lgamma(shots+1-success) for success in outcomes])
            likelihood = np.exp(np.log(probabilities)[:, :, None]*outcomes[None, None, :]
                                +np.log1p(-probabilities)[:, :, None]*(shots-outcomes)[None, None, :]
                                +coefficients[None, None, :]).reshape(len(posterior), -1)
            numerator = residual.T @ likelihood
            denominator = precision.T @ likelihood
            utility = ((numerator**2/np.maximum(denominator, 1e-200)).reshape(len(optimal), len(depths), shots+1)
                       .sum(axis=(0, 2))/len(posterior))
            exact.append(utility)
            del likelihood, numerator, denominator
        exact = np.asarray(exact)
        initial = np.sum(target_covariance**2, axis=0)[None, :]/(np.diag(covariance)[None, :]+variance_per_shot[None, :]/np.asarray(allocations)[:, None])
        chosen = []
        forbidden = np.zeros(len(depths), dtype=bool)
        spent = self.spent
        while spent-self.spent < 192 and 2000-spent>=32:
            denominator = np.maximum(1e-9, np.diag(covariance)[None, :]+variance_per_shot[None, :]/np.asarray(allocations)[:, None])
            utility = np.sum(target_covariance**2, axis=0)[None, :]/denominator * exact/np.maximum(initial,1e-20)
            utility /= np.asarray(allocations)[:, None]
            utility[:, forbidden] = -1
            for allocation, shots in enumerate(allocations):
                if shots > 2000-spent:
                    utility[allocation] = -1
            allocation, selected = np.unravel_index(np.argmax(utility), utility.shape)
            shots = allocations[allocation]
            if 2000-spent-shots < 32:
                shots = 2000-spent
            chosen.append((candidates[selected % len(candidates)], int(depths[selected]), int(shots)))
            column = covariance[:, selected].copy()
            target_column = target_covariance[:, selected].copy()
            target_covariance -= np.outer(target_column, column)/denominator[allocation, selected]
            covariance -= np.outer(column, column)/denominator[allocation, selected]
            forbidden[selected % len(candidates)::len(candidates)] = True
            spent += shots
        return chosen

    def run(self, exchange):
        while self.spent <= 1968:
            posterior = self.posterior()
            for matching, depth, shots in self.select_actions(posterior):
                observation = exchange({'type':'experiment','matching':matching,'depth':depth,'shots':shots})
                self.observations.append(observation)
                self.spent += shots
        targets = exchange({'type':'ready'})
        posterior = self.posterior(samples=2048, burn=1400, thin=4)
        unused, features = self.grid.features(targets['matchings'])
        rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ features.T))
        weights = (0.003+0.10*rates)**-2
        predictions = np.sum(weights*rates,axis=0)/weights.sum(axis=0)
        exchange({'type':'final','predictions':predictions.tolist()})
