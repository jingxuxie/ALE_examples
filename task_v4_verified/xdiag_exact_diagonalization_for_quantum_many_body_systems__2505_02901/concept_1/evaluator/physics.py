import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import csr_matrix


class QuantumCase:
    def __init__(self, case, propagators=False, tolerance=3e-11):
        self.case = case
        self.length = case["L"]
        self.states = [mask for mask in range(1 << self.length)
                       if bin(mask).count("1") == case["nup"]]
        self.index = {mask: index for index, mask in enumerate(self.states)}
        self.dimension = len(self.states)
        self.occupation = np.array([[(mask >> site) & 1 for site in range(self.length)]
                                    for mask in self.states], dtype=float)
        self.initial = np.zeros(self.dimension, dtype=complex)
        self.initial[self.index[sum(1 << site for site in case["initial_up_sites"])]] = 1
        self.sensors = {sensor["sensor_id"]: sensor for sensor in case["sensors"]}
        self.phases = np.exp(-1j * self.occupation @ np.array(
            [action["phase"] for action in case["actions"]]).T)
        self.parts = [self.hamiltonian(regime) for regime in case["regimes"]]
        self.tolerance = tolerance
        self.propagators = propagators
        self.unitaries = {}
        self.initial_cache = {}
        self.routes = {}
        self.permutations = {}
        self.stagger = self.occupation @ np.array([(-1) ** site for site in range(self.length)])
        self.left = case["entropy_sites"]
        self.right = [site for site in range(self.length) if site not in self.left]
        self.row_indices = np.array([sum(((mask >> site) & 1) << offset
                                        for offset, site in enumerate(self.left))
                                     for mask in self.states])
        self.column_indices = np.array([sum(((mask >> site) & 1) << offset
                                           for offset, site in enumerate(self.right))
                                        for mask in self.states])
        self.normalizer = math.log(2 ** min(len(self.left), len(self.right)))

    def hamiltonian(self, regime):
        static = np.zeros((self.dimension, self.dimension))
        driven = np.zeros_like(static)
        for site in range(self.length):
            alternating = (-1) ** site
            for distance, factor, xy_name, zz_name in (
                (1, 1 + alternating * self.case["delta"] * regime["delta_multiplier"], "J1xy", "J1z"),
                (2, regime["j2_multiplier"], "J2xy", "J2z"),
            ):
                other = (site + distance) % self.length
                for column, mask in enumerate(self.states):
                    first = (mask >> site) & 1
                    second = (mask >> other) & 1
                    diagonal = (first - 0.5) * (second - 0.5) * self.case[zz_name]
                    static[column, column] += factor * diagonal
                    drive_factor = (alternating * self.case["drive_amplitude"]
                                    * regime["drive_multiplier"] if distance == 1 else 0)
                    driven[column, column] += drive_factor * diagonal
                    if first != second:
                        row = self.index[mask ^ (1 << site) ^ (1 << other)]
                        offdiagonal = self.case[xy_name] / 2
                        static[row, column] += factor * offdiagonal
                        driven[row, column] += drive_factor * offdiagonal
        return csr_matrix(static), csr_matrix(driven), self.case["drive_omega"] * regime["omega_multiplier"]

    def integrate(self, vectors, start, stop, regime, times=None):
        if abs(stop - start) < 1e-14:
            return vectors.copy()
        static, driven, frequency = self.parts[regime]
        shape = vectors.shape

        def derivative(time, flattened):
            state = flattened.reshape(shape)
            return (-1j * (static @ state + math.sin(frequency * time) * (driven @ state))).ravel()

        solution = solve_ivp(derivative, (start, stop), vectors.ravel(), method="DOP853",
                             rtol=self.tolerance, atol=self.tolerance / 100,
                             t_eval=[stop] if times is None else times)
        if not solution.success or not np.isfinite(solution.y).all():
            raise ValueError("quantum integration failed")
        if times is not None:
            return [solution.y[:, index].reshape(shape) for index in range(len(times))]
        return solution.y[:, -1].reshape(shape)

    def evolve(self, vectors, start, stop, regime):
        if not self.propagators:
            return self.integrate(vectors, start, stop, regime)
        if regime not in self.unitaries:
            times = sorted({0.0, self.case["t_final"], self.case["open_loop_time"]}
                           | {sensor["time"] for sensor in self.case["sensors"]})
            matrices = self.integrate(np.eye(self.dimension, dtype=complex), 0,
                                      times[-1], regime, times)
            self.unitaries[regime] = dict(zip(times, matrices))
        unitary = self.unitaries[regime]
        return unitary[stop] @ (unitary[start].conj().T @ vectors)

    def project(self, state, sensor, sector):
        identifier = sensor["sensor_id"]
        if identifier not in self.permutations:
            self.permutations[identifier] = np.array([
                self.index[sum(1 << sensor["permutation"][site]
                               for site in range(self.length) if (mask >> site) & 1)]
                for mask in self.states])
        mapping = self.permutations[identifier]
        current = state.astype(complex, copy=True)
        result = np.zeros_like(current)
        for power in range(sensor["order"]):
            result += np.exp(-2j * np.pi * sector * power / sensor["order"]) * current
            permuted = np.empty_like(current)
            permuted[mapping] = current
            current = permuted
        return result / sensor["order"]

    def loss(self, state):
        norm = float(np.vdot(state, state).real)
        if norm < 1e-24:
            return 0.0
        state = state / math.sqrt(norm)
        matrix = np.zeros((1 << len(self.left), 1 << len(self.right)), dtype=complex)
        matrix[self.row_indices, self.column_indices] = state
        eigenvalues = np.linalg.svd(matrix, compute_uv=False) ** 2
        positive = eigenvalues[eigenvalues > 1e-16]
        entropy = -float(positive @ np.log(positive))
        imbalance = float(np.abs(state) ** 2 @ self.stagger) * 2 / self.length
        return 1 - entropy / self.normalizer + self.case["imbalance_weight"] * imbalance ** 2

    def before_first(self, sensor, regime):
        key = sensor["sensor_id"], regime
        if key not in self.initial_cache:
            self.initial_cache[key] = self.evolve(self.initial, 0.0, sensor["time"], regime)
        return self.initial_cache[key]

    def open_table(self):
        result = np.zeros((len(self.case["regimes"]), len(self.case["actions"])))
        for regime in range(len(self.case["regimes"])):
            initial = self.evolve(self.initial, 0.0, self.case["open_loop_time"], regime)
            states = self.evolve(initial[:, None] * self.phases, self.case["open_loop_time"],
                                 self.case["t_final"], regime)
            for action in range(len(self.case["actions"])):
                result[regime, action] = self.loss(states[:, action])
        return result

    def route(self, first_id, sector, second_id):
        key = first_id, sector, second_id
        if key in self.routes:
            return self.routes[key]
        first, second = self.sensors[first_id], self.sensors[second_id]
        probabilities = np.zeros((len(self.case["regimes"]), second["order"]))
        numerators = np.zeros(probabilities.shape + (len(self.case["actions"]),))
        bridge = np.exp(-1j * self.occupation @ np.array(first["bridge_phase_by_sector"][sector]))
        for regime in range(len(self.case["regimes"])):
            raw = self.project(self.before_first(first, regime), first, sector) * bridge
            middle = self.evolve(raw, first["time"], second["time"], regime)
            columns = []
            for outcome in range(second["order"]):
                collapsed = self.project(middle, second, outcome)
                probability = float(np.vdot(collapsed, collapsed).real)
                probabilities[regime, outcome] = probability
                normalized = collapsed / math.sqrt(probability) if probability > 1e-24 else collapsed * 0
                columns.append(normalized[:, None] * self.phases)
            final = self.evolve(np.concatenate(columns, axis=1), second["time"],
                                self.case["t_final"], regime)
            for outcome in range(second["order"]):
                for action in range(len(self.case["actions"])):
                    column = outcome * len(self.case["actions"]) + action
                    numerators[regime, outcome, action] = probabilities[regime, outcome] * self.loss(final[:, column])
        self.routes[key] = probabilities, numerators
        return probabilities, numerators

    def catalog(self):
        catalog = {"open": self.open_table()}
        sensor_indices = {sensor["sensor_id"]: index for index, sensor in enumerate(self.case["sensors"])}
        allowed = self.case["calibration_test"]["allowed_second_sensor_ids_by_sector"]
        for first_id, sectors in allowed.items():
            for sector, seconds in enumerate(sectors):
                for second_id in seconds:
                    name = "route_{}_{}_{}".format(sensor_indices[first_id], sector, sensor_indices[second_id])
                    probability, numerator = self.route(first_id, sector, second_id)
                    catalog[name] = numerator
                    catalog["probability_" + name] = probability
        return catalog
