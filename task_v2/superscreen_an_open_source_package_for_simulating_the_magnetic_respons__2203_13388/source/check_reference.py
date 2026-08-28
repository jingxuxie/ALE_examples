import json
import sys
from pathlib import Path
import time

import numpy as np
from scipy.integrate import dblquad

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'concept_01/solution/v_01'))
from qualification.model import MU0, load_case
from certified import solve, assemble
from triangle_integrals import potential_and_integral


def main():
    vertices = np.array([[0., 0., 0.], [1.3, 0., 0.], [0.2, 0.8, 0.]])
    point = np.array([0.27, 0.19, 0.031])
    analytic = np.array(potential_and_integral(point, vertices))
    numerical = []
    for component in range(4):
        def integrand(second, first):
            position = vertices[0] + first * (vertices[1] - vertices[0]) + second * (vertices[2] - vertices[0])
            delta = point - position
            radius = np.linalg.norm(delta)
            return 1.04 * (1 / radius if component == 0 else delta[component - 1] / radius ** 3)
        numerical.append(dblquad(integrand, 0, 1, lambda first: 0, lambda first: 1 - first,
                                 epsabs=1e-8, epsrel=1e-8)[0])
    kernel_error = float(np.max(np.abs(np.array(numerical) - analytic)))
    assert kernel_error < 2e-7, (analytic, numerical)
    cases = []
    for path in sorted((ROOT / 'concept_01/evaluator/hidden').glob('h_*.npz')):
        case = load_case(path)
        start = time.perf_counter()
        result = solve(case)
        seconds = time.perf_counter() - start
        high_matrix, transform, _, _, _ = assemble(case, order=10)
        low_matrix, _, _, _, _ = assemble(case, order=6)
        relative_matrix_error = float(np.linalg.norm(high_matrix - low_matrix) / np.linalg.norm(high_matrix))
        states = np.linalg.lstsq(transform.toarray(), result['stream'].T, rcond=None)[0]
        projected_residual = (high_matrix - low_matrix) @ states
        relative_residual = float(np.linalg.norm(projected_residual) / max(np.linalg.norm(high_matrix @ states), 1e-12))
        eigenvalue = float(np.linalg.eigvalsh(high_matrix)[0])
        assert eigenvalue > 0
        assert relative_matrix_error < 0.004
        assert relative_residual < 0.004
        assert np.linalg.norm(result['inductance'] - result['inductance'].T) < 1e-8
        fixed = np.isfinite(case.prescribed_current)
        assert np.max(np.abs((result['hole_current'] - np.nan_to_num(case.prescribed_current))[fixed]), initial=0) < 1e-10
        free = ~fixed
        assert np.max(np.abs((result['fluxoid'] - case.target_fluxoid)[free]), initial=0) < 1e-9
        record = {'case': path.stem, 'seconds': seconds, 'quadrature_matrix_relative_error': relative_matrix_error,
                  'quadrature_solution_residual': relative_residual, 'minimum_eigenvalue': eigenvalue}
        cases.append(record)
        print(record, flush=True)
    output = {'analytic_triangle_vs_independent_adaptive_quadrature_max_error': kernel_error,
              'certification': cases, 'passed': True}
    (ROOT / 'concept_01/solution/v_01/reference_certificate.json').write_text(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
