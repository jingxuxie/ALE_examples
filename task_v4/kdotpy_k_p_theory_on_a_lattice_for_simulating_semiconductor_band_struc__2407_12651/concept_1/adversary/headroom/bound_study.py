import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
sys.path.insert(0, str(HERE / 'submission'))
from atlas import Atlas
from relaxation import embed, formulate
from certificate import exact_box_dual, save_certificate


def optimize_formulation(formulation, seconds):
    return linprog(formulation['objective'], A_ub=formulation['inequalities'], b_ub=formulation['inequality_rhs'],
                   A_eq=formulation['equalities'], b_eq=formulation['equality_rhs'],
                   bounds=np.stack((np.zeros(len(formulation['upper'])), formulation['upper']), axis=1),
                   method='highs-ipm', options={'time_limit': seconds, 'presolve': True,
                                              'primal_feasibility_tolerance': 1e-8,
                                              'dual_feasibility_tolerance': 1e-8})


def small_validation():
    random = np.random.default_rng(932)
    metadata = json.loads((ROOT / 'participant/input/gap_hotspots_0/case.json').read_text())
    metadata.update(nx=3, ny=2, budget=4, anchors={})
    metadata['scenarios'] = [dict(row, normalizer=1.0, target_chern=0) for row in metadata['scenarios'][:2]]
    arrays = {'frames': np.eye(4, 2) + 0.18 * (random.normal(size=(2, 6, 2, 4, 2)) + 1j * random.normal(size=(2, 6, 2, 4, 2))),
              'energies': random.normal(size=(2, 6, 2, 2)), 'costs': np.tile([0, 1], (6, 1)),
              'guide': np.zeros((2, 6, 2)), 'target_flux': np.zeros((2, 6)), 'seed_choices': np.zeros(6, dtype=int)}
    atlas = Atlas(metadata, arrays)
    metadata['baseline_objective'] = atlas.score(atlas.seed)['objective']
    choices = np.array(list(itertools.product(range(2), repeat=6)))
    scores = atlas.evaluate_many(choices)
    optimum = float(np.min(np.where(scores['feasible'], scores['objective'], np.inf)))
    formulation = formulate(atlas)
    result = optimize_formulation(formulation, 10)
    assert result.success
    certificate = exact_box_dual(formulation, result.eqlin.marginals, result.ineqlin.marginals)
    assert certificate['lower_bound'] <= optimum + 1e-12
    max_error = 0.0
    count = 0
    for selection, feasible, objective in zip(choices, scores['feasible'], scores['objective']):
        if not feasible or objective > metadata['baseline_objective']:
            continue
        vector = embed(atlas, formulation, selection)
        error = max(np.max(np.abs(formulation['equalities'] @ vector - formulation['equality_rhs'])),
                    np.max(formulation['inequalities'] @ vector - formulation['inequality_rhs']),
                    np.max(vector - formulation['upper']), abs(formulation['objective'] @ vector - objective))
        max_error = max(max_error, float(error))
        count += 1
    assert max_error < 1e-9
    adversarial_dual = exact_box_dual(formulation, random.normal(size=len(formulation['equality_rhs'])),
                                     random.normal(size=len(formulation['inequality_rhs'])))
    assert adversarial_dual['lower_bound'] <= optimum
    return {'passed': True, 'enumerated': 64, 'feasible_below_baseline_embedded': count,
            'maximum_embedding_error': max_error, 'exact_discrete_optimum': optimum,
            'lp_lower_bound': certificate['lower_bound'], 'arbitrary_dual_check': True}


def main():
    started = time.monotonic()
    validation = small_validation()
    certificates = HERE / 'certificates'
    certificates.mkdir(exist_ok=True)
    cases_root = ROOT / 'evaluator' / 'hidden' / 'cases'
    cases = json.loads((cases_root / 'manifest.json').read_text())['cases']
    report = {'validation': validation, 'cases': [], 'complete': False,
              'scope': 'Frozen hidden cases only; no fresh attempts inspected; no frozen files changed.'}
    for case in cases:
        if time.monotonic() - started > 220:
            break
        case_started = time.monotonic()
        atlas = Atlas.load(cases_root / case['directory'])
        with np.load(cases_root / case['directory'] / 'arrays.npz', allow_pickle=False) as archive:
            baseline = archive['baseline_choices']
        formulation = formulate(atlas)
        vector = embed(atlas, formulation, baseline)
        embedding_error = max(float(np.max(np.abs(formulation['equalities'] @ vector - formulation['equality_rhs']))),
                              float(np.max(formulation['inequalities'] @ vector - formulation['inequality_rhs'])),
                              float(np.max(vector - formulation['upper'])),
                              float(abs(formulation['objective'] @ vector - atlas.score(baseline)['objective'])))
        assert embedding_error < 1e-9
        result = optimize_formulation(formulation, 22)
        row = {'case_id': case['id'], 'family': case['family'], 'baseline_objective': atlas.metadata['baseline_objective'],
               'lp_success': bool(result.success), 'lp_status': int(result.status), 'embedding_error': embedding_error}
        if result.success:
            row.update(exact_box_dual(formulation, result.eqlin.marginals, result.ineqlin.marginals))
            row['lp_primal_objective'] = float(result.fun)
            row['upper_gain_bound'] = 1 - row['lower_bound'] / atlas.metadata['baseline_objective']
            certificate_path = certificates / (case['id'] + '.npz')
            save_certificate(certificate_path, formulation, result.eqlin.marginals, result.ineqlin.marginals)
            row['certificate'] = str(certificate_path.relative_to(HERE))
            probabilities = result.x[formulation['vertex_ids']]
            np.save(certificates / (case['id'] + '_marginals.npy'), probabilities)
            rounded = atlas.score(probabilities.argmax(axis=1))
            row['rounded_score'] = rounded
            if rounded['feasible']:
                row['rounded_gain'] = 1 - rounded['objective'] / atlas.metadata['baseline_objective']
        row['seconds'] = time.monotonic() - case_started
        report['cases'].append(row)
        report['elapsed_seconds'] = time.monotonic() - started
        report['complete'] = len(report['cases']) == len(cases)
        print(json.dumps({key: row[key] for key in ['case_id', 'lp_success', 'seconds', 'upper_gain_bound', 'rounded_gain'] if key in row}), flush=True)
        (HERE / 'bounds.json').write_text(json.dumps(report, indent=2) + '\n')
    if report['complete'] and all(row['lp_success'] for row in report['cases']):
        families = sorted({row['family'] for row in report['cases']})
        family_bounds = {family: float(np.mean([row['upper_gain_bound'] for row in report['cases'] if row['family'] == family])) for family in families}
        report['family_upper_gain_bounds'] = family_bounds
        report['overall_upper_gain_bound'] = float(np.mean(list(family_bounds.values())))
        report['worst_family_upper_gain_bound'] = min(family_bounds.values())
        report['targets_excluded_by_bounds'] = report['overall_upper_gain_bound'] < 0.12 or report['worst_family_upper_gain_bound'] < 0.08
        (HERE / 'bounds.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({key: value for key, value in report.items() if key not in ['cases']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
