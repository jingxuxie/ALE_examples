import math
import time
import ctypes
from pathlib import Path
import numpy as np
from engine import Policy


class ActivePolicy(Policy):
    sampler_name = 'core.so'
    sampler_tempered = True

    def __init__(self, hello):
        self.started_cpu = time.process_time()
        self.started_wall = time.monotonic()
        self.sweep_cost = 0.001
        super().__init__(hello)
        self.final_library = self.library
        self.library = ctypes.CDLL(str(Path(__file__).with_name('sampler.so')))
        self.library.sample_posterior.argtypes = self.final_library.sample_posterior.argtypes[:-1]
        self.library.sample_posterior.restype = None
        self.sampler_tempered = False

    def elapsed(self):
        return max(time.process_time()-self.started_cpu, 0.7*(time.monotonic()-self.started_wall))

    def posterior(self, samples=512, burn=450, thin=2):
        started = time.process_time()
        result = super().posterior(samples=samples, burn=burn, thin=thin)
        self.sweep_cost = max(0.00002, (time.process_time()-started)/max(1, burn+samples*thin))
        return result

    def select_batch(self, posterior, batch_size):
        count = 300 if self.elapsed()<40 else 180
        candidates = self.grid.pool(self.generator, count, self.hello['max_matching_size'], varied=True)
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

    def final_posterior(self):
        self.library = self.final_library
        self.sampler_tempered = True
        self.sweep_cost *= 1.4
        if self.elapsed()>48:
            return self.posterior(samples=512, burn=150, thin=1)
        design, features = self.grid.features([record['matching'] for record in self.observations])
        depths = np.array([record['depth'] for record in self.observations])
        successes = np.array([record['successes'] for record in self.observations])
        shots = np.array([record['shots'] for record in self.observations])
        contexts = np.array([record['context'] for record in self.observations])
        sizes = design.sum(axis=1)

        def likelihood(state):
            rates = features @ state[:self.rate_dimension]
            spam = state[self.rate_dimension:]
            latent = spam[0]+spam[1]*sizes/(self.grid.qubits//2)+design @ spam[2:2+self.edge_count]/np.sqrt(np.maximum(1,sizes))
            if self.family==3:
                latent += spam[-4]*np.sin(2*np.pi*spam[-3]*contexts+spam[-2])+spam[-1]*(contexts-0.5)
            probability = (0.58+0.37/(1+np.exp(-latent)))*np.exp(-depths*rates)
            probability = 2.0**(-self.grid.qubits)+(1-2.0**(-self.grid.qubits))*probability
            return np.sum(successes*np.log(probability)+(shots-successes)*np.log1p(-probability))

        sweep_budget = max(1500, int(max(1,55-self.elapsed())/(1.3*self.sweep_cost)))
        blocks = max(8, min(64, (sweep_budget-1000)//144))
        self.posterior(samples=1, burn=600, thin=1)
        cold = self.state.copy()
        self.temperature = 0.7
        self.posterior(samples=1, burn=400, thin=1)
        hot = self.state.copy()
        outputs = []
        for block in range(blocks):
            self.state = cold
            self.temperature = 1.0
            outputs.append(self.posterior(samples=32, burn=0, thin=3))
            cold = self.state.copy()
            self.state = hot
            self.temperature = 0.7
            self.posterior(samples=1, burn=0, thin=48)
            hot = self.state.copy()
            difference = 0.3*(likelihood(hot)-likelihood(cold))
            if np.log(self.generator.random()) < difference:
                cold, hot = hot, cold
            if self.elapsed()>53:
                break
        self.state = cold
        self.temperature = 1.0
        return np.concatenate(outputs)

    def run(self, exchange):
        while self.spent <= 1968:
            if self.elapsed()>40:
                posterior = self.posterior(samples=256, burn=100, thin=1)
            elif self.elapsed()>32:
                posterior = self.posterior(samples=384, burn=200, thin=2)
            else:
                posterior = self.posterior()
            remaining = (2000-self.spent)//32
            batch_size = min(6, remaining)
            for matching, depth in self.select_batch(posterior, batch_size):
                shots = 48 if self.spent == 1952 else 32
                observation = exchange({'type':'experiment', 'matching':matching, 'depth':depth, 'shots':shots})
                self.observations.append(observation)
                self.spent += shots
        targets = exchange({'type':'ready'})
        posterior = self.final_posterior()
        unused, features = self.grid.features(targets['matchings'])
        rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ features.T))
        weights = (0.003+0.10*rates)**-2
        predictions = np.sum(weights*rates, axis=0)/weights.sum(axis=0)
        predictions = np.clip(predictions, 0, 1-4.0**(-self.grid.qubits))
        exchange({'type':'final', 'predictions':predictions.tolist()})
