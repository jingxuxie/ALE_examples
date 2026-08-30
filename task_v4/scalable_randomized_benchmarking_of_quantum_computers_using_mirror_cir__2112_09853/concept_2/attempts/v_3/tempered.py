import numpy as np
from balanced import BalancedPolicy
from variants import ExactPolicy


class TemperedPolicy(BalancedPolicy):
    sampler_name = '../sampler3.so'
    sampler_tempered = True

    def posterior(self, samples=512, burn=450, thin=2):
        if samples < 2048 or len(self.observations) < 60:
            return super().posterior(samples=samples, burn=burn, thin=thin)
        design, features = self.grid.features([record['matching'] for record in self.observations])
        depths = np.array([record['depth'] for record in self.observations])
        successes = np.array([record['successes'] for record in self.observations])
        shots = np.array([record['shots'] for record in self.observations])
        contexts = np.array([record['context'] for record in self.observations])
        sizes = design.sum(axis=1)

        def likelihood(state):
            rates = features @ state[:self.rate_dimension]
            spam = state[self.rate_dimension:]
            latent = spam[0]+spam[1]*sizes/(self.grid.qubits//2)+design @ spam[2:2+self.edge_count]/np.sqrt(sizes)
            if self.family==3:
                latent += spam[-4]*np.sin(2*np.pi*spam[-3]*contexts+spam[-2])+spam[-1]*(contexts-0.5)
            probability = (0.58+0.37/(1+np.exp(-latent)))*np.exp(-depths*rates)
            probability = 2.0**(-self.grid.qubits)+(1-2.0**(-self.grid.qubits))*probability
            return np.sum(successes*np.log(probability)+(shots-successes)*np.log1p(-probability))

        super().posterior(samples=1, burn=600, thin=1)
        cold = self.state.copy()
        self.temperature = 0.7
        super().posterior(samples=1, burn=400, thin=1)
        hot = self.state.copy()
        outputs = []
        for block in range(64):
            self.state = cold
            self.temperature = 1.0
            outputs.append(super().posterior(samples=32, burn=0, thin=3))
            cold = self.state.copy()
            self.state = hot
            self.temperature = 0.7
            super().posterior(samples=1, burn=0, thin=48)
            hot = self.state.copy()
            difference = 0.3*(likelihood(hot)-likelihood(cold))
            if np.log(self.generator.random()) < difference:
                cold, hot = hot, cold
        self.state = cold
        self.temperature = 1.0
        return np.concatenate(outputs)


class FinalCandidatePolicy(TemperedPolicy):
    def candidate_pool(self, posterior):
        return ExactPolicy.candidate_pool(self, posterior)
