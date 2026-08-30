import numpy as np
from variants import ExactPolicy


class DensePolicy(ExactPolicy):
    sampler_name = '../sampler2.so'

    def select_batch(self, posterior, batch_size):
        candidates = self.grid.pool(self.generator, 300 if self.grid.qubits==16 else 600, self.hello['max_matching_size'], varied=False)
        design, features = self.grid.features(candidates)
        candidate_rates = posterior[:, :self.rate_dimension] @ features.T
        mean_rates = candidate_rates.mean(axis=0)
        depths = np.clip(2*np.rint(1.6/mean_rates/2), 2, 256).astype(int)
        probabilities = self.probabilities(posterior, design, candidate_rates, depths, (self.spent+16)/2000)
        probability = probabilities.mean(axis=0)
        noise = (1-probability)/(32*depths**2*probability)
        centered = candidate_rates-candidate_rates.mean(axis=0)
        target_rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ self.proxy_features.T))
        target_centered = (target_rates-target_rates.mean(axis=0))/(0.003+0.1*target_rates.mean(axis=0))
        covariance = centered.T @ centered / len(posterior)
        target_covariance = target_centered.T @ centered / len(posterior)
        chosen = []
        forbidden = np.zeros(len(depths), dtype=bool)
        for index in range(batch_size):
            denominator = np.maximum(1e-12, np.diag(covariance)+noise)
            utility = np.sum(target_covariance**2, axis=0)/denominator
            utility[forbidden] = -1
            selected = int(np.argmax(utility))
            chosen.append((candidates[selected], int(depths[selected])))
            column = covariance[:, selected].copy()
            target_column = target_covariance[:, selected].copy()
            target_covariance -= np.outer(target_column, column)/denominator[selected]
            covariance -= np.outer(column, column)/denominator[selected]
            forbidden[selected] = True
        return chosen
