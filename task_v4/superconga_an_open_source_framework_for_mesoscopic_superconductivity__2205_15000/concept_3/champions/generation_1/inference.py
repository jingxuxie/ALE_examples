import time

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares

import physics


class SearchTimeout(Exception):
    pass


class InverseProblem:
    def __init__(self, seconds=83.0):
        self.start_cpu = time.process_time()
        self.start_wall = time.monotonic()
        self.deadline = self.start_cpu + seconds
        self.allowed = np.asarray(physics.SPEC['impurity_sites'])
        self.sectors = physics.sectors()
        self.matrices = [physics.hamiltonian(np.zeros(64), sector) for sector in self.sectors]
        self.matrices[0] = self.matrices[0].real.copy()
        self.actions = []
        self.observations = np.empty(0)
        self.sites = np.empty(0, dtype=int)
        self.energies = np.empty(0)
        self.dense = {}
        self.pool = {}
        self.best = None
        self.evaluations = 0
        self.generator = np.random.default_rng(712817)

    def check_time(self):
        if time.process_time() > self.deadline or time.monotonic() - self.start_wall > 110:
            raise SearchTimeout()

    def add(self, site, energy, observation):
        self.actions.append((int(site), int(energy)))
        self.observations = np.append(self.observations, observation)
        self.sites = np.asarray([action[0] for action in self.actions])
        self.energies = np.asarray([physics.SPEC['energies'][action[1]] for action in self.actions])

    def eigensystem(self, sector, parameters):
        matrix = self.matrices[sector].copy()
        matrix[self.allowed, self.allowed] += parameters
        matrix[self.allowed + 64, self.allowed + 64] -= parameters
        return eigh(matrix, check_finite=False, driver='evr', overwrite_a=True)

    def normal_eigensystem(self, parameters):
        matrix = self.matrices[0][:64, :64].copy()
        matrix[self.allowed, self.allowed] += parameters
        return eigh(matrix, check_finite=False, driver='evr', overwrite_a=True)

    def predict(self, sector, parameters, selected=None, sites=None, energies=None):
        self.check_time()
        self.evaluations += 1
        sites = self.sites if sites is None else sites
        energies = self.energies if energies is None else energies
        if sector == 0:
            eigenvalues, eigenvectors = self.normal_eigensystem(parameters)
            frequency = energies[:, None] + 0.065j
            denominator = frequency ** 2 - eigenvalues ** 2 - 0.55 ** 2
            electron_resolvent = (frequency + eigenvalues) / denominator
            anomalous_resolvent = 0.55 / denominator
            electron = eigenvectors[sites]
            values = -np.imag(np.sum(electron ** 2 * electron_resolvent, axis=1)) / np.pi
            if selected is None:
                return values
            impurity = eigenvectors[self.allowed[selected]]
            forward = (electron * electron_resolvent) @ impurity.T
            anomalous = (electron * anomalous_resolvent) @ impurity.T
            gradient = -np.imag(forward ** 2 - anomalous ** 2) / np.pi
            return values, gradient
        eigenvalues, eigenvectors = self.eigensystem(sector, parameters)
        inverse = 1.0 / (energies[:, None] + 0.065j - eigenvalues)
        electron = eigenvectors[sites]
        values = -np.imag(np.sum(abs(electron) ** 2 * inverse, axis=1)) / np.pi
        if selected is None:
            return values
        impurity_sites = self.allowed[selected]
        columns = np.concatenate((impurity_sites, impurity_sites + 64))
        forward = (electron * inverse) @ eigenvectors[columns].conj().T
        backward = (electron.conj() * inverse) @ eigenvectors[columns].T
        products = forward * backward
        count = len(selected)
        gradient = -np.imag(products[:, :count] - products[:, count:]) / np.pi
        return values, gradient

    def optimize(self, sector, initial, support=None, evaluations=40, regularization=8e-5, weights=None, free=None):
        selected = (np.arange(36) if free is None else np.asarray(free)) if support is None else np.asarray(support)
        initial = np.asarray(initial)[selected].copy()
        if support is None:
            bounds = (-1.6, 1.6)
        else:
            signs = np.where(initial >= 0, 1.0, -1.0)
            bounds = (np.where(signs > 0, 0.55, -1.6), np.where(signs > 0, 1.6, -0.55))
        initial = np.clip(initial, np.asarray(bounds[0]) + 1e-9, np.asarray(bounds[1]) - 1e-9)
        cached_parameters = None
        cached_result = None

        def evaluate(parameters):
            nonlocal cached_parameters, cached_result
            if cached_parameters is not None and np.array_equal(parameters, cached_parameters):
                return cached_result
            potential = np.zeros(36)
            potential[selected] = parameters
            values, gradient = self.predict(sector, potential, selected)
            residual = values - self.observations
            if weights is not None:
                residual = residual * weights
                gradient = gradient * weights[:, None]
            if support is None:
                root = parameters ** 2 + 0.04 ** 2
                penalty = np.sqrt(regularization) * root ** 0.25
                derivative = np.sqrt(regularization) * 0.5 * parameters * root ** -0.75
                residual = np.concatenate((residual, penalty))
                gradient = np.vstack((gradient, np.diag(derivative)))
            cached_parameters = parameters.copy()
            cached_result = residual, gradient
            return cached_result

        result = least_squares(lambda parameters: evaluate(parameters)[0], initial,
                               jac=lambda parameters: evaluate(parameters)[1], bounds=bounds,
                               max_nfev=evaluations, ftol=1e-9, xtol=1e-9,
                               gtol=1e-10 if support is not None else 1e-8)
        parameters = np.zeros(36)
        parameters[selected] = result.x
        residual = evaluate(result.x)[0]
        if weights is not None:
            residual = residual.copy()
            residual[:len(self.observations)] /= weights
        objective = float(residual @ residual)
        if support is None:
            objective += regularization * 0.04 * (36 - len(selected))
        return parameters, objective

    def record(self, sector, parameters, objective):
        support = np.flatnonzero(parameters)
        key = (sector, tuple(support), tuple(np.sign(parameters[support]).astype(int)))
        candidate = (objective, sector, parameters.copy())
        if key not in self.pool or objective < self.pool[key][0]:
            self.pool[key] = candidate
        if self.best is None or objective < self.best[0]:
            self.best = candidate

    def sparse(self, sector, parameters, evaluations=45):
        order = np.argsort(abs(parameters))[::-1]
        for count in range(4, 8):
            support = np.sort(order[:count])
            fitted, objective = self.optimize(sector, parameters, support, evaluations=evaluations)
            self.record(sector, fitted, objective)
            if self.solved():
                return

    def solved(self):
        return self.best is not None and self.best[0] < 1e-12

    def initial_fit(self):
        for sector in range(46):
            parameters, objective = self.optimize(sector, np.zeros(36), evaluations=26)
            self.dense[sector] = (objective, parameters)
        self.refine(8, 65)

    def refine(self, count=6, evaluations=60):
        ordered = sorted(self.dense, key=lambda sector: self.dense[sector][0])
        for sector in ordered[:count]:
            parameters, objective = self.optimize(sector, self.dense[sector][1], evaluations=evaluations)
            self.dense[sector] = (objective, parameters)
            self.sparse(sector, parameters)
            if self.solved():
                return

    def refresh(self):
        previous = sorted(self.pool.values(), key=lambda candidate: candidate[0])[:24]
        self.pool = {}
        self.best = None
        for _, sector, parameters in previous:
            support = np.flatnonzero(parameters)
            parameters, objective = self.optimize(sector, parameters, support, evaluations=20)
            self.record(sector, parameters, objective)
            if self.solved():
                return
        for sector in range(46):
            parameters, objective = self.optimize(sector, self.dense[sector][1], evaluations=15)
            self.dense[sector] = (objective, parameters)
        self.refine(6, 50)

    def table(self, sector, parameters):
        self.check_time()
        energies = np.asarray(physics.SPEC['energies'])
        if sector == 0:
            eigenvalues, eigenvectors = self.normal_eigensystem(parameters)
            frequency = energies[None, :] + 0.065j
            resolvent = (frequency + eigenvalues[:, None]) / (frequency ** 2 - eigenvalues[:, None] ** 2 - 0.55 ** 2)
            return ((eigenvectors ** 2) @ (-resolvent.imag / np.pi)).ravel()
        eigenvalues, eigenvectors = self.eigensystem(sector, parameters)
        lorentzian = 0.065 / (np.pi * ((energies[None, :] - eigenvalues[:, None]) ** 2 + 0.065 ** 2))
        return (abs(eigenvectors[:64]) ** 2 @ lorentzian).ravel()

    def design(self, count):
        candidates = sorted(self.pool.values(), key=lambda candidate: candidate[0])[:8]
        for sector in sorted(self.dense, key=lambda sector: self.dense[sector][0])[:4]:
            objective, parameters = self.dense[sector]
            candidates.append((objective, sector, parameters))
        tables = np.asarray([self.table(sector, parameters) for _, sector, parameters in candidates])
        centered = tables - tables.mean(axis=0)
        variance = np.mean(centered ** 2, axis=0)
        sector, parameters = self.best[1:]
        all_sites = np.repeat(np.arange(64), 41)
        all_energies = np.tile(np.asarray(physics.SPEC['energies']), 64)
        _, gradient = self.predict(sector, parameters, np.arange(36), all_sites, all_energies)
        _, measured = self.predict(sector, parameters, np.arange(36))
        covariance = np.linalg.inv(measured.T @ measured + 1e-4 * np.eye(36))
        used = [site * 41 + energy for site, energy in self.actions]
        selected = []
        for repeat in range(count):
            sensitivity = np.maximum(np.sum((gradient @ covariance) * gradient, axis=1), 0)
            score = variance / (variance.max() + 1e-20) + 0.35 * sensitivity / (sensitivity.max() + 1e-20)
            score[used] = -1
            index = int(np.argmax(score))
            selected.append(divmod(index, 41))
            used.append(index)
            direction = covariance @ gradient[index]
            covariance -= np.outer(direction, direction) / (1 + gradient[index] @ direction)
            direction = centered[:, index]
            norm = float(direction @ direction)
            if norm > 1e-20:
                centered -= np.outer(direction, direction @ centered) / (norm * 1.01)
                variance = np.mean(centered ** 2, axis=0)
        return selected

    def site_trials(self, sector, parameters):
        self.check_time()
        eigenvalues, eigenvectors = self.eigensystem(sector, parameters)
        inverse = 1.0 / (self.energies[:, None] + 0.065j - eigenvalues)
        electron = eigenvectors[self.sites]
        local_electron = eigenvectors[self.allowed]
        local_hole = eigenvectors[self.allowed + 64]
        columns = np.concatenate((self.allowed, self.allowed + 64))
        forward = (electron * inverse) @ eigenvectors[columns].conj().T
        backward = (electron.conj() * inverse) @ eigenvectors[columns].T
        block_ee = inverse @ (abs(local_electron) ** 2).T
        block_hh = inverse @ (abs(local_hole) ** 2).T
        block_eh = inverse @ (local_electron * local_hole.conj()).T
        block_he = inverse @ (local_hole * local_electron.conj()).T
        diagonal = np.sum(abs(electron) ** 2 * inverse, axis=1)
        grid = np.asarray([-1.5, -1.05, -0.6, 0.0, 0.6, 1.05, 1.5])
        delta = grid[None, :] - parameters[:, None]
        delta = delta[None, :, :]
        determinant = ((1 - delta * block_ee[:, :, None]) * (1 + delta * block_hh[:, :, None])
                       + delta ** 2 * (block_eh * block_he)[:, :, None])
        transform_ee = delta * (1 + delta * block_hh[:, :, None]) / determinant
        transform_hh = -delta * (1 - delta * block_ee[:, :, None]) / determinant
        transform_eh = -delta ** 2 * block_eh[:, :, None] / determinant
        transform_he = -delta ** 2 * block_he[:, :, None] / determinant
        correction = (forward[:, :36, None] * (transform_ee * backward[:, :36, None]
                                              + transform_eh * backward[:, 36:, None])
                      + forward[:, 36:, None] * (transform_he * backward[:, :36, None]
                                                + transform_hh * backward[:, 36:, None]))
        predictions = -(diagonal[:, None, None] + correction).imag / np.pi
        errors = np.sum((predictions - self.observations[:, None, None]) ** 2, axis=0)
        return errors, grid

    def neighborhood(self, candidate, breadth=12):
        _, sector, parameters = candidate
        support = np.flatnonzero(parameters)
        proposals = {}
        removals = [-1] + list(support)
        for removed in removals:
            seed = parameters.copy()
            if removed >= 0:
                seed[removed] = 0
            errors, grid = self.site_trials(sector, seed)
            for index in np.argsort(errors, axis=None):
                site, strength_index = divmod(int(index), len(grid))
                proposed = seed.copy()
                proposed[site] = grid[strength_index]
                selected = np.flatnonzero(proposed)
                if not 4 <= len(selected) <= 7:
                    continue
                key = (tuple(selected), tuple(np.sign(proposed[selected]).astype(int)))
                objective = float(errors[site, strength_index])
                if key not in proposals or objective < proposals[key][0]:
                    proposals[key] = (objective, proposed)
        for _, seed in sorted(proposals.values(), key=lambda proposal: proposal[0])[:breadth]:
            fitted, objective = self.optimize(sector, seed, np.flatnonzero(seed), evaluations=50)
            self.record(sector, fitted, objective)
            if self.solved():
                return

    def clustered(self, sector, round_index):
        candidates = []
        for anchor_row in range(1, 4):
            for anchor_column in range(1, 4):
                support = np.flatnonzero((self.allowed // 8 >= anchor_row)
                                         & (self.allowed // 8 < anchor_row + 4)
                                         & (self.allowed % 8 >= anchor_column)
                                         & (self.allowed % 8 < anchor_column + 4))
                seed = np.zeros(36) if round_index == 0 else self.generator.normal(0, 0.4, 36)
                parameters, objective = self.optimize(sector, seed, free=support, evaluations=75)
                candidates.append((objective, parameters, support))
        candidates.sort(key=lambda candidate: candidate[0])
        for _, parameters, support in candidates[:3]:
            parameters, objective = self.optimize(sector, parameters, free=support, evaluations=80)
            if objective < self.dense[sector][0]:
                self.dense[sector] = (objective, parameters)
            self.sparse(sector, parameters, evaluations=65)
            if self.solved():
                return
        if candidates[0][0] < 0.8 * self.best[0]:
            for _, _, support in candidates[:2]:
                for repeat in range(6):
                    seed = self.generator.uniform(-1.6, 1.6, 36)
                    seed[self.generator.random(36) < 0.4] = 0
                    parameters, objective = self.optimize(sector, seed, free=support, evaluations=120)
                    if objective < self.dense[sector][0]:
                        self.dense[sector] = (objective, parameters)
                    if objective < self.best[0]:
                        self.sparse(sector, parameters, evaluations=65)
                    if self.solved():
                        return

    def diversified(self):
        sector_order = [self.best[1]]
        sector_order += [sector for sector in sorted(self.dense, key=lambda sector: self.dense[sector][0])
                         if sector not in sector_order][:3]
        for sector in sector_order:
            for repeat in range(4 if sector == sector_order[0] else 2):
                weights = np.ones(len(self.actions))
                omitted = self.generator.choice(len(self.actions), 12 + 4 * (repeat % 2), replace=False)
                weights[omitted] = 0.04
                seed = np.zeros(36) if repeat % 2 == 0 else self.dense[sector][1].copy()
                parameters, _ = self.optimize(sector, seed, weights=weights, evaluations=100)
                parameters, objective = self.optimize(sector, parameters, evaluations=70)
                if objective < self.dense[sector][0]:
                    self.dense[sector] = (objective, parameters)
                self.sparse(sector, parameters, evaluations=60)
                if self.solved():
                    return

    def restart(self, round_index):
        ordered_dense = sorted(self.dense, key=lambda sector: self.dense[sector][0])
        if round_index % 5 == 0:
            self.clustered(self.best[1], round_index)
            if self.solved():
                return
            seeds = sorted(self.pool.values(), key=lambda candidate: candidate[0])[:3]
            for candidate in seeds:
                self.neighborhood(candidate)
                if self.solved():
                    return
        elif round_index % 5 == 1:
            seeds = sorted(self.pool.values(), key=lambda candidate: candidate[0])[:5]
            for _, sector, parameters in seeds:
                parameters, objective = self.optimize(sector, parameters, evaluations=90,
                                                      regularization=4e-5)
                if objective < self.dense[sector][0]:
                    self.dense[sector] = (objective, parameters)
                self.sparse(sector, parameters, evaluations=70)
                if self.solved():
                    return
            for sector in ordered_dense[:6]:
                parameters, objective = self.optimize(sector, np.zeros(36), evaluations=100,
                                                      weights=0.2 / (self.observations + 0.02))
                if objective < self.dense[sector][0]:
                    self.dense[sector] = (objective, parameters)
                self.sparse(sector, parameters, evaluations=60)
                if self.solved():
                    return
        elif round_index % 5 == 2:
            self.diversified()
        elif round_index % 5 == 3:
            seed = self.best[2].copy()
            for sector in ordered_dense:
                parameters, objective = self.optimize(sector, seed, evaluations=30)
                if objective < self.dense[sector][0]:
                    self.dense[sector] = (objective, parameters)
            self.refine(8, 60)
        else:
            for sector in ordered_dense[:10]:
                seed = self.dense[sector][1].copy()
                seed += self.generator.normal(0, 0.5, 36)
                seed[self.generator.random(36) < 0.3] = 0
                parameters, objective = self.optimize(sector, seed, evaluations=75,
                                                      regularization=8e-5)
                if objective < self.dense[sector][0]:
                    self.dense[sector] = (objective, parameters)
                self.sparse(sector, parameters, evaluations=65)
                if self.solved():
                    return

    def scene(self):
        if self.best is not None:
            _, sector, parameters = self.best
        elif self.dense:
            sector = min(self.dense, key=lambda item: self.dense[item][0])
            parameters = self.dense[sector][1].copy()
            support = np.argsort(abs(parameters))[-7:]
            result = np.zeros(36)
            result[support] = np.where(parameters[support] >= 0, 1, -1) * np.clip(abs(parameters[support]), 0.55, 1.6)
            parameters = result
        else:
            sector = 0
            parameters = np.zeros(36)
            parameters[:4] = 0.55
        return {'impurities': [{'site': int(self.allowed[index]), 'strength': float(strength)}
                               for index, strength in enumerate(parameters) if strength != 0],
                'vortices': self.sectors[sector]}
