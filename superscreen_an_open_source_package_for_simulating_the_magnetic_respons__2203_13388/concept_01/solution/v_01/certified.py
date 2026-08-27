import numpy as np
from scipy import linalg, sparse

from qualification.model import MU0, applied_load, triangle_geometry
from triangle_integrals import triangle_inductance, field_operators, field_from_current


def assemble(case, order=6, material=True, coupling=True):
    triangles, areas, current_x, current_y = triangle_geometry(case)
    interaction = triangle_inductance(triangles, order=order)
    if not coupling:
        interaction[case.triangle_film[:, None] != case.triangle_film[None, :]] = 0
    kinetic = areas * case.lambdas if material else np.zeros(len(areas))
    interaction[np.diag_indices_from(interaction)] += kinetic
    matrix = current_x.T @ (interaction @ current_x) + current_y.T @ (interaction @ current_y)
    free_vertices = np.flatnonzero(case.region == 0)
    holes = len(case.prescribed_current[0])
    columns = np.full(len(case.points), -1, dtype=int)
    columns[free_vertices] = np.arange(len(free_vertices))
    for hole in range(holes):
        columns[case.region == hole + 1] = len(free_vertices) + hole
    active = np.flatnonzero(columns >= 0)
    transform = sparse.csr_matrix((np.ones(len(active)), (active, columns[active])),
                                  shape=(len(case.points), len(free_vertices) + holes))
    reduced = transform.T @ matrix @ transform
    return np.asarray(reduced), transform, current_x, current_y, triangles


def solve(case, config='qualified'):
    options = {'qualified': (6, True, True), 'low_quadrature': (2, True, True),
               'uncoupled': (6, True, False), 'no_kinetic': (6, False, True)}
    order, material, coupling = options[config]
    matrix, transform, current_x, current_y, triangles = assemble(case, order, material, coupling)
    load = (transform.T @ (applied_load(case) - case.vortex_load).T).T
    holes = case.prescribed_current.shape[1]
    internal = matrix.shape[0] - holes
    inner_factor = linalg.cho_factor(matrix[:internal, :internal])
    hole_response = -linalg.cho_solve(inner_factor, matrix[:internal, internal:])
    inductance = MU0 * (matrix[internal:, internal:] + matrix[internal:, :internal] @ hole_response)
    states = []
    fluxoids = []
    for drive, force in enumerate(load):
        state = np.zeros(len(force))
        fixed = np.flatnonzero(np.isfinite(case.prescribed_current[drive])) + internal
        state[fixed] = case.prescribed_current[drive, fixed - internal]
        free = np.setdiff1d(np.arange(len(force)), fixed)
        rhs = -force.copy()
        rhs[internal:] += case.target_fluxoid[drive] / MU0
        state[free] = linalg.solve(matrix[np.ix_(free, free)], rhs[free] - matrix[np.ix_(free, fixed)] @ state[fixed], assume_a='pos')
        states.append(state)
        fluxoids.append(MU0 * (matrix @ state + force)[internal:])
    states = np.array(states)
    stream = (transform @ states.T).T
    current = np.stack(((current_x @ stream.T).T, (current_y @ stream.T).T), axis=-1)
    operators = field_operators(triangles, case.observers)
    return {'stream': stream, 'current': current,
            'field': field_from_current(operators, current, MU0),
            'hole_current': states[:, internal:], 'fluxoid': np.array(fluxoids),
            'inductance': inductance}
