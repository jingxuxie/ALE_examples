import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logsumexp

from exact import STATES, FEATURES, LOWER, LIMIT, evaluate


class Model:
    def __init__(self, witness):
        self.witness = dict(witness)
        self.spins = np.ascontiguousarray(STATES[32768:, witness['order']])
        self.energy = -FEATURES[32768:] @ np.asarray(witness['bonds'])
        distance = (STATES[32768:] != witness['pattern']).sum(axis=1)
        self.sector = np.minimum(distance, 16 - distance) <= witness['radius']
        self.last = None
        self.calls = 0

    def pack(self, witness=None):
        witness = self.witness if witness is None else witness
        return np.r_[np.array(witness['weights'])[LOWER], witness['beta']]

    def unpack(self, parameters):
        result = dict(self.witness)
        weights = np.zeros((16, 16))
        weights[LOWER] = parameters[:120]
        lengths = np.abs(weights).sum(axis=1)
        weights *= np.minimum(1.0, (LIMIT - 1e-13) / np.maximum(lengths, 1e-100))[:, None]
        result['weights'] = weights.tolist()
        result['beta'] = float(parameters[120])
        return result

    def calc(self, parameters):
        if self.last is not None and np.array_equal(parameters, self.last):
            return self.values, self.jacobians
        self.last = parameters.copy()
        self.calls += 1
        weights = np.zeros((16, 16))
        weights[LOWER] = parameters[:120]
        beta = parameters[120]
        logits = self.spins @ weights.T
        conditional = expit(logits)
        logq = -np.logaddexp(0, -self.spins * logits).sum(axis=1)
        probq = 2 * np.exp(logq)
        logz = logsumexp(-beta * self.energy) + np.log(2.0)
        probp = 2 * np.exp(-beta * self.energy - logz)
        reward = beta * self.energy + logq
        mean = probq @ reward
        centered = reward - mean
        residual = (self.spins + 1) / 2 - conditional
        weighted_residual = probq[:, None] * residual

        def differentiate(observable):
            return ((weighted_residual * observable[:, None]).T @ self.spins)[LOWER]

        gradkl = differentiate(centered)
        energyq = probq @ self.energy
        energyp = probp @ self.energy
        gradenergy = differentiate(self.energy)
        gradvar = differentiate(centered ** 2 + 2 * centered)
        gradentropy = differentiate(-logq)
        gradsector = differentiate(self.sector)
        varenergy = probp @ ((self.energy - energyp) ** 2)
        gradbeta = energyq - energyp
        variance = probq @ (centered ** 2)
        entropy = -probq @ logq
        reversekl = mean + logz
        energyerror = beta * gradbeta
        targetmass = probp @ self.sector
        proposalmass = probq @ self.sector
        self.values = np.array([variance, entropy, reversekl, energyerror, targetmass, proposalmass])
        self.jacobians = np.array([
            np.r_[gradvar, 2 * probq @ (centered * self.energy)],
            np.r_[gradentropy, 0.0],
            np.r_[gradkl, gradbeta],
            np.r_[beta * gradenergy, gradbeta + beta * varenergy],
            np.r_[np.zeros(120), -probp @ (self.sector * (self.energy - energyp))],
            np.r_[gradsector, 0.0],
        ])
        self.gradkl = gradkl
        self.weights = weights
        self.probq = probq
        self.centered = centered
        self.weighted_residual = weighted_residual
        self.conditional = conditional
        self.gradenergy = gradenergy
        return self.values, self.jacobians

    def hessian_product(self, direction):
        matrix = np.zeros((16, 16))
        matrix[LOWER] = direction
        direction_logits = self.spins @ matrix.T
        directional_score = np.sum(((self.spins + 1) / 2 - self.conditional) * direction_logits, axis=1)
        first = (self.weighted_residual * ((self.centered + 1) * directional_score)[:, None]).T @ self.spins
        second = (-(self.probq * self.centered)[:, None] * self.conditional * (1 - self.conditional) * direction_logits).T @ self.spins
        return np.r_[(first + second)[LOWER], self.gradenergy @ direction]

    def objective(self, parameters, gradweight=0.0):
        values, jacobians = self.calc(parameters)
        objective = values[0]
        derivative = jacobians[0].copy()
        if gradweight:
            objective += gradweight * (self.gradkl @ self.gradkl)
            derivative += 2 * gradweight * self.hessian_product(self.gradkl)
        return objective, derivative

    def constraints(self, parameters):
        values, jacobians = self.calc(parameters)
        lengths = np.abs(self.weights).sum(axis=1)[1:]
        values_out = np.r_[LIMIT - 2e-12 - lengths,
                           values[1] - 3.001, values[2] - 0.401,
                           0.319 - values[3], 0.319 + values[3],
                           values[4] - 0.3501, (0.000999 - values[5]) * 100]
        return values_out

    def constraints_jac(self, parameters):
        values, jacobians = self.calc(parameters)
        length_jac = np.zeros((15, 121))
        length_jac[LOWER[0] - 1, np.arange(120)] = -np.sign(parameters[:120])
        return np.vstack([length_jac, jacobians[1], jacobians[2], -jacobians[3], jacobians[3],
                          jacobians[4], -100 * jacobians[5]])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', default='optimized.json')
    parser.add_argument('--maxiter', type=int, default=300)
    parser.add_argument('--beta', type=float)
    parser.add_argument('--gradweight', type=float, default=0.0)
    arguments = parser.parse_args()
    witness = json.loads(Path(arguments.source).read_text())
    if arguments.beta:
        witness['beta'] = arguments.beta
    model = Model(witness)
    initial = model.pack()
    start = time.time()
    counter = 0
    best_score = 0.0

    def callback(parameters):
        nonlocal counter, best_score
        counter += 1
        if counter % 10 == 0:
            report = evaluate(model.unpack(parameters))
            print(counter, model.calls, round(time.time() - start, 2),
                  {key: round(report[key], 7) for key in ['reward_variance', 'gradient_infinity',
                      'entropy', 'energy_error_per_spin', 'target_sector_mass', 'proposal_sector_mass', 'core_score']}, flush=True)
            if report['core_score'] > best_score:
                best_score = report['core_score']
                Path(arguments.output).write_text(json.dumps(model.unpack(parameters)))

    result = minimize(lambda parameters: model.objective(parameters, arguments.gradweight), initial,
                      method='SLSQP', jac=True,
                      bounds=[(-LIMIT, LIMIT)] * 120 + [(1, 3)],
                      constraints={'type': 'ineq', 'fun': model.constraints, 'jac': model.constraints_jac},
                      callback=callback,
                      options={'maxiter': arguments.maxiter, 'ftol': 1e-11, 'disp': True})
    final = model.unpack(result.x)
    Path(arguments.output.replace('.json', '_last.json')).write_text(json.dumps(final))
    report = evaluate(final)
    if report['core_score'] > best_score:
        Path(arguments.output).write_text(json.dumps(final))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
