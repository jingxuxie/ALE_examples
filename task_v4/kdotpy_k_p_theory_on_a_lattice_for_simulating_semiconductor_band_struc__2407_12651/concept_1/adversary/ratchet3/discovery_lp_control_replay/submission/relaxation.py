import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, vstack


def formulate(atlas):
    candidates = atlas.candidates
    vertex_size = atlas.vertices * candidates
    edge_size = len(atlas.edges) * candidates ** 2
    face_size = atlas.vertices * candidates ** 4
    edge_offset = vertex_size
    face_offset = vertex_size + edge_size
    variable_count = face_offset + face_size + 1
    vertex_ids = np.arange(vertex_size).reshape(atlas.vertices, candidates)
    edge_ids = np.arange(edge_offset, face_offset).reshape(len(atlas.edges), candidates, candidates)
    face_ids = np.arange(face_offset, variable_count - 1).reshape(atlas.vertices, candidates, candidates, candidates, candidates)
    rows, columns, coefficients, right_hand = [], [], [], []

    def equality(indices, values, target=0.0):
        indices = np.asarray(indices).ravel()
        values = np.broadcast_to(values, indices.shape)
        rows.extend([len(right_hand)] * len(indices))
        columns.extend(indices.tolist())
        coefficients.extend(values.tolist())
        right_hand.append(target)

    for vertex in range(atlas.vertices):
        equality(vertex_ids[vertex], 1.0, 1.0)
    for edge, (source, destination) in enumerate(atlas.edges):
        for candidate in range(candidates):
            equality(np.r_[edge_ids[edge, candidate], vertex_ids[source, candidate]], np.r_[np.ones(candidates), -1.0])
            equality(np.r_[edge_ids[edge, :, candidate], vertex_ids[destination, candidate]], np.r_[np.ones(candidates), -1.0])
    assignments = np.array(list(np.ndindex((candidates,) * 4)))
    for face, corners in enumerate(atlas.plaquettes):
        boundaries = [(2 * corners[0], 0, 1), (2 * corners[1] + 1, 1, 2),
                      (2 * corners[3], 3, 2), (2 * corners[0] + 1, 0, 3)]
        flattened = face_ids[face].ravel()
        for edge, first, second in boundaries:
            for first_choice in range(candidates):
                for second_choice in range(candidates):
                    selected = flattened[(assignments[:, first] == first_choice) & (assignments[:, second] == second_choice)]
                    equality(np.r_[selected, edge_ids[edge, first_choice, second_choice]], np.r_[np.ones(len(selected)), -1.0])
    equalities = coo_matrix((coefficients, (rows, columns)), shape=(len(right_hand), variable_count)).tocsr()
    equality_rhs = np.array(right_hand)
    scenario_coefficients = np.zeros((atlas.scenarios, variable_count))
    scenario_coefficients[:, :edge_offset] = atlas.unary.reshape(atlas.scenarios, -1)
    scenario_coefficients[:, edge_offset:face_offset] = atlas.pair.reshape(atlas.scenarios, -1)
    scenario_coefficients[:, face_offset:-1] = atlas.face.reshape(atlas.scenarios, -1)
    scenario_coefficients /= atlas.normalizers[:, None]
    objective = atlas.mean_weight * (atlas.weights @ scenario_coefficients) / atlas.weights.sum()
    objective[-1] = 1.0
    epigraph = scenario_coefficients.copy()
    epigraph[:, -1] = -1.0
    budget = np.zeros((1, variable_count))
    budget[0, :edge_offset] = atlas.costs.ravel()
    chern = np.zeros((atlas.scenarios, variable_count))
    chern[:, face_offset:-1] = atlas.flux.reshape(atlas.scenarios, -1) / (2 * np.pi)
    inequalities = vstack([csr_matrix(epigraph), csr_matrix(budget), csr_matrix(chern), csr_matrix(-chern)], format='csr')
    inequality_rhs = np.r_[np.zeros(atlas.scenarios), atlas.budget,
                           atlas.targets + atlas.chern_tolerance, -atlas.targets + atlas.chern_tolerance]
    upper = np.ones(variable_count)
    upper[-1] = atlas.metadata['baseline_objective']
    for vertex, selected in atlas.anchors.items():
        upper[vertex_ids[vertex]] = 0.0
        upper[vertex_ids[vertex, selected]] = 1.0
    bad_edges = np.any(atlas.link_magnitude < atlas.minimum_link, axis=0)
    bad_faces = np.any(np.pi - np.abs(atlas.flux) < atlas.branch_margin, axis=0)
    upper[edge_ids[bad_edges]] = 0.0
    upper[face_ids[bad_faces]] = 0.0
    return {'objective': objective, 'equalities': equalities, 'equality_rhs': equality_rhs,
            'inequalities': inequalities, 'inequality_rhs': inequality_rhs, 'upper': upper,
            'vertex_ids': vertex_ids, 'edge_ids': edge_ids, 'face_ids': face_ids,
            'scenario_coefficients': scenario_coefficients}


def embed(atlas, formulation, choices):
    vector = np.zeros(len(formulation['objective']))
    vector[formulation['vertex_ids'][np.arange(atlas.vertices), choices]] = 1.0
    vector[formulation['edge_ids'][np.arange(len(atlas.edges)), choices[atlas.edges[:, 0]], choices[atlas.edges[:, 1]]]] = 1.0
    corners = atlas.plaquettes
    vector[formulation['face_ids'][np.arange(atlas.vertices), choices[corners[:, 0]], choices[corners[:, 1]], choices[corners[:, 2]], choices[corners[:, 3]]]] = 1.0
    vector[-1] = np.max(atlas.score(choices)['normalized_loss'])
    return vector


def corrected_dual_bound(formulation, equality_dual, inequality_dual):
    equality_dual = np.asarray(equality_dual, dtype=np.longdouble)
    inequality_dual = np.minimum(np.asarray(inequality_dual, dtype=np.longdouble), 0)
    residual = np.asarray(formulation['objective'], dtype=np.longdouble).copy()
    magnitude = np.abs(residual).sum()
    for matrix, multipliers in [(formulation['equalities'], equality_dual), (formulation['inequalities'], inequality_dual)]:
        entries = matrix.tocoo()
        contributions = np.asarray(entries.data, dtype=np.longdouble) * multipliers[entries.row]
        np.add.at(residual, entries.col, -contributions)
        magnitude += np.abs(contributions).sum()
    equality_term = np.dot(np.asarray(formulation['equality_rhs'], dtype=np.longdouble), equality_dual)
    inequality_term = np.dot(np.asarray(formulation['inequality_rhs'], dtype=np.longdouble), inequality_dual)
    correction = np.dot(np.minimum(residual, 0), np.asarray(formulation['upper'], dtype=np.longdouble))
    allowance = np.longdouble(1e-9) * (1 + magnitude + abs(equality_term) + abs(inequality_term) + abs(correction))
    bound = equality_term + inequality_term + correction - allowance
    return {'lower_bound': float(bound), 'dual_box_correction': float(correction),
            'roundoff_allowance': float(allowance), 'maximum_negative_reduced_cost': float(max(0, -residual.min())),
            'method': 'sign-clipped inequality dual plus exact-box residual correction in long double; numerical, not interval-certified'}


def relaxation(atlas, seconds=20.0):
    started = time.monotonic()
    formulation = formulate(atlas)
    baseline = atlas.seed
    seed_embedding = embed(atlas, formulation, baseline)
    equality_error = float(np.max(np.abs(formulation['equalities'] @ seed_embedding - formulation['equality_rhs'])))
    if equality_error > 1e-9:
        raise ValueError('feasible atlas fails marginal consistency embedding')
    remaining = max(0.1, seconds - (time.monotonic() - started))
    result = linprog(formulation['objective'], A_ub=formulation['inequalities'], b_ub=formulation['inequality_rhs'],
                     A_eq=formulation['equalities'], b_eq=formulation['equality_rhs'],
                     bounds=np.stack((np.zeros(len(formulation['upper'])), formulation['upper']), axis=1),
                     method='highs-ipm', options={'time_limit': remaining, 'presolve': True,
                                                'primal_feasibility_tolerance': 1e-8,
                                                'dual_feasibility_tolerance': 1e-8})
    report = {'status': int(result.status), 'message': result.message, 'seconds': time.monotonic() - started,
              'variables': len(formulation['objective']), 'equalities': len(formulation['equality_rhs']),
              'inequalities': len(formulation['inequality_rhs']), 'success': bool(result.success)}
    if not result.success:
        return None, report
    report.update(corrected_dual_bound(formulation, result.eqlin.marginals, result.ineqlin.marginals))
    report['lp_objective'] = float(result.fun)
    report['upper_gain_bound'] = float(1 - report['lower_bound'] / atlas.metadata['baseline_objective'])
    probabilities = result.x[formulation['vertex_ids']]
    report['fractional_vertices'] = int(np.count_nonzero(probabilities.max(axis=1) < 1 - 1e-6))
    return probabilities, report
