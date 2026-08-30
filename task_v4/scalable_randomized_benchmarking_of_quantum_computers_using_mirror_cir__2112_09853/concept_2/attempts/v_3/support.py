import numpy as np
from subsets import SubsetPolicy


class SupportPolicy(SubsetPolicy):
    def select_batch(self, posterior, batch_size):
        if self.spent >= 1536:
            return super().select_batch(posterior, batch_size)
        candidates = self.candidate_pool(posterior)
        design, features = self.grid.features(candidates)
        rates = posterior[:, :self.rate_dimension] @ features.T
        multipliers = np.array([1.05, 1.8])
        depths = np.clip(2*np.rint(multipliers[:, None]/rates.mean(axis=0)[None, :]/2), 2, 256).astype(int).ravel()
        rates = np.tile(rates, (1, 2))
        design = np.tile(design, (2, 1))
        mask = np.tile(features[:, 1+self.edge_count:].T, (1, 2))
        probabilities = self.probabilities(posterior, design, rates, depths, (self.spent+16)/2000)
        centered = probabilities-probabilities.mean(axis=0)
        noise = np.mean(probabilities*(1-probabilities), axis=0)/32
        covariance = centered.T @ centered/len(posterior)
        support = (posterior[:, 1+self.edge_count:self.rate_dimension]>0).astype(float)
        support_mean = support.mean(axis=0)
        support_centered = support-support_mean
        support_covariance = support_centered.T @ centered/len(posterior)
        support_variance = support_mean*(1-support_mean)
        importance = self.proxy_features[:, 1+self.edge_count:].mean(axis=0)/(support_variance+0.01)
        chosen = []
        forbidden = np.zeros(len(depths), dtype=bool)
        for index in range(batch_size):
            denominator = np.maximum(1e-9, np.diag(covariance)+noise)
            reduction = support_covariance**2-support_variance[:, None]*np.diag(covariance)[None, :]/(len(posterior)/2)
            utility = np.sum(reduction*importance[:, None]*mask, axis=0)/denominator
            utility[forbidden] = -1e100
            selected = int(np.argmax(utility))
            chosen.append((candidates[selected % len(candidates)], int(depths[selected])))
            column = covariance[:, selected].copy()
            support_column = support_covariance[:, selected].copy()
            support_covariance -= np.outer(support_column, column)/denominator[selected]
            covariance -= np.outer(column, column)/denominator[selected]
            forbidden[selected % len(candidates)::len(candidates)] = True
        return chosen
