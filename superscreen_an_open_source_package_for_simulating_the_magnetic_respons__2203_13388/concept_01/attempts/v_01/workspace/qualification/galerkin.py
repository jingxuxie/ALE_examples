import time

import numpy as np
from numba import njit
from scipy.linalg import cho_factor, cho_solve

from .model import MU0, applied_load, triangle_geometry


@njit(cache=True)
def triangle_integrals(position, vertices):
    vectors = vertices - position
    radii = np.sqrt(np.sum(vectors * vectors, axis=1))
    height = position[2] - vertices[0, 2]
    twice_area = ((vertices[1, 0] - vertices[0, 0]) * (vertices[2, 1] - vertices[0, 1])
                  - (vertices[1, 1] - vertices[0, 1]) * (vertices[2, 0] - vertices[0, 0]))
    denominator = (radii[0] * radii[1] * radii[2]
                   + np.dot(vectors[0], vectors[1]) * radii[2]
                   + np.dot(vectors[1], vectors[2]) * radii[0]
                   + np.dot(vectors[2], vectors[0]) * radii[1])
    solid_angle = 0.0
    if height != 0.0:
        solid_angle = 2 * np.arctan2(height * twice_area, denominator)
    potential = -height * solid_angle
    field_x, field_y = 0.0, 0.0
    for edge in range(3):
        following = (edge + 1) % 3
        edge_x = vertices[following, 0] - vertices[edge, 0]
        edge_y = vertices[following, 1] - vertices[edge, 1]
        length = np.sqrt(edge_x * edge_x + edge_y * edge_y)
        normal_x, normal_y = edge_y / length, -edge_x / length
        distance = vectors[edge, 0] * normal_x + vectors[edge, 1] * normal_y
        radius_sum = radii[edge] + radii[following]
        difference = radius_sum - length
        if difference < 1e-8 * length:
            projection = (vectors[edge, 0] * edge_x + vectors[edge, 1] * edge_y) / length
            perpendicular_squared = distance * distance + height * height
            if projection <= 0.0 and projection + length >= 0.0:
                difference = perpendicular_squared * (1.0 / max(radii[edge] - projection, 1e-300)
                                                       + 1.0 / max(radii[following] + projection + length, 1e-300))
        integral = np.log1p(2.0 * length / max(difference, 1e-300))
        potential += distance * integral
        field_x += normal_x * integral
        field_y += normal_y * integral
    return potential, field_x, field_y, solid_angle


def quadrature(order):
    nodes, weights = np.polynomial.legendre.leggauss(order)
    nodes, weights = (nodes + 1) / 2, weights / 2
    first, second = np.meshgrid(nodes, nodes, indexing='ij')
    barycentric = np.stack((1 - first, first * (1 - second), first * second), axis=-1).reshape(-1, 3)
    weighted = (2 * first * weights[:, None] * weights[None, :]).ravel()
    return np.ascontiguousarray(barycentric), np.ascontiguousarray(weighted)


@njit(cache=True)
def integrate_pair(target, source, area, barycentric, weights):
    value = 0.0
    for index in range(len(weights)):
        position = barycentric[index] @ target
        potential, _, _, _ = triangle_integrals(position, source)
        value += weights[index] * potential
    return area * value


@njit(cache=True)
def adaptive_pair(target, source, area, coarse_rule, coarse_weights, fine_rule, fine_weights, tolerance, depth):
    triangles = np.empty((4 * depth + 1, 3, 3))
    levels = np.empty(4 * depth + 1, dtype=np.int64)
    areas = np.empty(4 * depth + 1)
    triangles[0], levels[0], areas[0] = target, depth, area
    count = 1
    result = 0.0
    while count:
        count -= 1
        local = triangles[count].copy()
        remaining = levels[count]
        local_area = areas[count]
        fine = integrate_pair(local, source, local_area, fine_rule, fine_weights)
        coarse = integrate_pair(local, source, local_area, coarse_rule, coarse_weights)
        if remaining == 0 or abs(fine - coarse) < tolerance * abs(fine):
            result += fine
            continue
        middle_first = (local[0] + local[1]) / 2
        middle_second = (local[1] + local[2]) / 2
        middle_third = (local[2] + local[0]) / 2
        triangles[count, 0], triangles[count, 1], triangles[count, 2] = local[0], middle_first, middle_third
        triangles[count + 1, 0], triangles[count + 1, 1], triangles[count + 1, 2] = middle_first, local[1], middle_second
        triangles[count + 2, 0], triangles[count + 2, 1], triangles[count + 2, 2] = middle_third, middle_second, local[2]
        triangles[count + 3, 0], triangles[count + 3, 1], triangles[count + 3, 2] = middle_first, middle_second, middle_third
        levels[count:count + 4] = remaining - 1
        areas[count:count + 4] = local_area / 4
        count += 4
    return result


@njit(cache=True)
def magnetic_integrals(vertices, areas, films, near_rule, near_weights,
                       middle_rule, middle_weights, far_rule, far_weights, coupled, adaptive):
    count = len(areas)
    matrix = np.zeros((count, count))
    centers = np.empty((count, 3))
    radii = np.zeros(count)
    for triangle in range(count):
        centers[triangle] = (vertices[triangle, 0] + vertices[triangle, 1] + vertices[triangle, 2]) / 3
        for corner in range(3):
            radii[triangle] = max(radii[triangle], np.linalg.norm(vertices[triangle, corner] - centers[triangle]))
    for target in range(count):
        for source in range(target + 1):
            if not coupled and films[target] != films[source]:
                continue
            separation = np.linalg.norm(centers[target] - centers[source])
            size = radii[target] + radii[source]
            if separation > 3.0 * size:
                barycentric, weights = far_rule, far_weights
            elif separation > 1.5 * size:
                barycentric, weights = middle_rule, middle_weights
            else:
                barycentric, weights = near_rule, near_weights
            if (adaptive and films[target] != films[source] and separation < 1.5 * size
                    and abs(centers[target, 2] - centers[source, 2]) < 0.2 * size):
                forward = adaptive_pair(vertices[target], vertices[source], areas[target], middle_rule,
                                        middle_weights, near_rule, near_weights, 2e-7, 3)
                reverse = adaptive_pair(vertices[source], vertices[target], areas[source], middle_rule,
                                        middle_weights, near_rule, near_weights, 2e-7, 3)
            else:
                forward = integrate_pair(vertices[target], vertices[source], areas[target], barycentric, weights)
                reverse = integrate_pair(vertices[source], vertices[target], areas[source], barycentric, weights)
            matrix[target, source] = (forward + reverse) / 2
            matrix[source, target] = matrix[target, source]
    return matrix / (4 * np.pi)


@njit(cache=True)
def field_integrals(observers, vertices):
    result = np.empty((len(observers), len(vertices), 3))
    for observer in range(len(observers)):
        for triangle in range(len(vertices)):
            _, field_x, field_y, field_z = triangle_integrals(observers[observer], vertices[triangle])
            result[observer, triangle, 0] = field_x
            result[observer, triangle, 1] = field_y
            result[observer, triangle, 2] = field_z
    return result


def field_from_integrals(integrals, current):
    field = np.empty((len(current), len(integrals), 3))
    field[:, :, 0] = current[:, :, 1] @ integrals[:, :, 2].T
    field[:, :, 1] = -current[:, :, 0] @ integrals[:, :, 2].T
    field[:, :, 2] = current[:, :, 0] @ integrals[:, :, 1].T - current[:, :, 1] @ integrals[:, :, 0].T
    return MU0 / (4 * np.pi) * field


def evaluate_field(observers, vertices, current):
    return field_from_integrals(field_integrals(observers, vertices), current)


def warm_kernels():
    vertices = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
    rule, weights = quadrature(2)
    magnetic_integrals(vertices, np.array([0.5]), np.array([0], dtype=np.int64),
                       rule, weights, rule, weights, rule, weights, True, True)
    field_integrals(np.array([[0.2, 0.2, 0.1]]), vertices)


class SheetModel:
    def __init__(self, case, config='qualified'):
        start = time.perf_counter()
        self.case = case
        self.config = config
        self.vertices, self.area, current_x, current_y = triangle_geometry(case)
        free = np.flatnonzero(case.region == 0)
        self.free_count = len(free)
        self.holes = case.prescribed_current.shape[1]
        self.reduction = np.zeros((len(case.points), len(free) + self.holes))
        self.reduction[free, np.arange(len(free))] = 1
        for hole in range(self.holes):
            self.reduction[case.region == hole + 1, len(free) + hole] = 1
        self.current_x = current_x @ self.reduction
        self.current_y = current_y @ self.reduction
        hole_faces = np.all(case.region[case.triangles] > 0, axis=1) & np.all(
            case.region[case.triangles] == case.region[case.triangles[:, :1]], axis=1)
        self.current_x[hole_faces] = 0
        self.current_y[hole_faces] = 0
        active = np.flatnonzero(~hole_faces)
        materials = case.lambdas.copy()
        if config == 'smoothed_material':
            sums, counts = np.zeros(len(case.points)), np.zeros(len(case.points))
            np.add.at(sums, case.triangles[active].ravel(), np.repeat(materials[active], 3))
            np.add.at(counts, case.triangles[active].ravel(), 1)
            nodal = sums / np.maximum(counts, 1)
            materials[active] = nodal[case.triangles[active]].mean(axis=1)
        order = {'coarse': 4, 'qualified': 12, 'fixed12': 12, 'refined': 24,
                 'reference': 40, 'high_reference': 72}.get(config, 12)
        near_rule, near_weights = quadrature(order)
        middle_rule, middle_weights = quadrature(min(order, 6))
        far_rule, far_weights = quadrature(min(order, 4))
        magnetic = magnetic_integrals(np.ascontiguousarray(self.vertices[active]), self.area[active],
                                     case.triangle_film[active], near_rule, near_weights, middle_rule,
                                     middle_weights, far_rule, far_weights, config != 'no_coupling',
                                     config not in ('coarse', 'fixed12', 'refined', 'reference', 'high_reference'))
        kinetic = self.area * materials
        self.matrix = (self.current_x.T @ (kinetic[:, None] * self.current_x)
                       + self.current_y.T @ (kinetic[:, None] * self.current_y))
        for operator in (self.current_x[active], self.current_y[active]):
            self.matrix += operator.T @ magnetic @ operator
        self.factor = cho_factor(self.matrix[:len(free), :len(free)])
        self.hole_response = -cho_solve(self.factor, self.matrix[:len(free), len(free):])
        self.inductance = MU0 * (self.matrix[len(free):, len(free):]
                                + self.matrix[len(free):, :len(free)] @ self.hole_response)
        self.hole_faces = [np.flatnonzero(np.all(case.region[case.triangles] == hole + 1, axis=1))
                           for hole in range(self.holes)]
        if config == 'bare_flux_control':
            self.bare_operator = np.zeros((self.holes, self.matrix.shape[0]))
            rule, weights = quadrature(12)
            for hole, faces in enumerate(self.hole_faces):
                observers = np.einsum('qv,tvk->tqk', rule, self.vertices[faces]).reshape(-1, 3)
                integration_weights = (self.area[faces, None] * weights).ravel()
                for start_index in range(0, len(observers), 128):
                    integral = field_integrals(observers[start_index:start_index + 128], self.vertices)
                    weighted_x = integration_weights[start_index:start_index + 128] @ integral[:, :, 0]
                    weighted_y = integration_weights[start_index:start_index + 128] @ integral[:, :, 1]
                    self.bare_operator[hole] += MU0 / (4 * np.pi) * (
                        weighted_y @ self.current_x - weighted_x @ self.current_y)
            self.bare_inductance = self.bare_operator @ np.vstack((self.hole_response, np.eye(self.holes)))
        self.setup_seconds = time.perf_counter() - start
        self.cached_observers = None
        self.cached_integrals = None

    def solve(self, case=None):
        start = time.perf_counter()
        case = self.case if case is None else case
        free_count = self.free_count
        source = (case.vortex_load - applied_load(case)) @ self.reduction
        particular = cho_solve(self.factor, source[:, :free_count].T).T
        offset = MU0 * (particular @ self.matrix[free_count:, :free_count].T - source[:, free_count:])
        control_inductance = self.inductance
        control_offset = offset
        if self.config == 'bare_flux_control':
            applied_flux = np.column_stack([MU0 * np.sum(self.area[faces][None] *
                case.drive_H[:, case.triangles[faces]].mean(axis=2), axis=1) for faces in self.hole_faces]) if self.holes else np.empty((len(particular), 0))
            control_inductance = self.bare_inductance
            control_offset = particular @ self.bare_operator[:, :free_count].T + applied_flux
        currents = case.prescribed_current.copy()
        for drive in range(len(currents)):
            unknown = np.flatnonzero(~np.isfinite(currents[drive]))
            known = np.flatnonzero(np.isfinite(currents[drive]))
            if len(unknown):
                target = case.target_fluxoid[drive, unknown] - control_offset[drive, unknown]
                target -= control_inductance[np.ix_(unknown, known)] @ currents[drive, known]
                currents[drive, unknown] = np.linalg.solve(control_inductance[np.ix_(unknown, unknown)], target)
        reduced = np.column_stack((particular + currents @ self.hole_response.T, currents))
        stream = reduced @ self.reduction.T
        current = np.stack((reduced @ self.current_x.T, reduced @ self.current_y.T), axis=-1)
        fluxoid = MU0 * (reduced @ self.matrix[free_count:].T - source[:, free_count:])
        residual = reduced @ self.matrix.T - source
        solve_seconds = time.perf_counter() - start
        start = time.perf_counter()
        if self.cached_observers is None or not np.array_equal(case.observers, self.cached_observers):
            self.cached_observers = case.observers.copy()
            self.cached_integrals = field_integrals(case.observers, self.vertices)
        field = field_from_integrals(self.cached_integrals, current)
        readout_seconds = time.perf_counter() - start
        result = {'stream': stream, 'current': current, 'field': field, 'hole_current': currents,
                  'fluxoid': fluxoid, 'inductance': self.inductance,
                  'equilibrium_residual': residual[:, :free_count],
                  'reduced_matrix': self.matrix,
                  'timing_setup': np.array(self.setup_seconds), 'timing_solve': np.array(solve_seconds),
                  'timing_readout': np.array(readout_seconds)}
        if self.config == 'bare_flux_control':
            result['bare_flux'] = currents @ self.bare_inductance.T + control_offset
        return result


def solve(case, config='qualified'):
    start = time.perf_counter()
    warm_kernels()
    warmup_seconds = time.perf_counter() - start
    result = SheetModel(case, config=config).solve()
    result['timing_warmup'] = np.array(warmup_seconds)
    return result
