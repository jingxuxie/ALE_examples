import numpy as np
from scipy.special import logsumexp
from regional import configurations


class Distribution:
    def __init__(self, instance):
        self.spins = configurations(instance['n'])
        couplings = np.asarray(instance['couplings'])
        fields = np.asarray(instance['fields'])
        log_target = .5 * np.sum((self.spins @ couplings) * self.spins, axis=1) + self.spins @ fields
        self.log_target = log_target - logsumexp(log_target)
        self.target = np.exp(self.log_target)

    def concentrated(self, samples=32768):
        return np.partition(self.target, -samples)[-samples:].sum() >= .995
