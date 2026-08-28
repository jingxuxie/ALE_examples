import json
import time

import numpy as np

from generate import ROOT
from metrics import WEIGHTS, losses, score_components
from solver import Model, likelihood_fit, membership, row_basis, solve
from weak_baseline import solve as weak_solve


def audit_case(data, oracle):
    model = Model(data)
    calibration, signs = model.experiments('train')
    heldout, heldout_signs = model.experiments('holdout')
    queries = model.queries()
    reference = solve(data)
    alternatives = {'strong_reference': reference, 'weak_scalar_sign_aware': weak_solve(data)}
    empirical = signs * (2 * data['train_plus'] / data['train_shots'] - 1)
    logarithms = -np.log(np.clip(empirical, 0.001, 0.999999))
    rates = np.linalg.lstsq(calibration, logarithms, rcond=1e-10)[0]
    alternatives['oracle_geometry_unweighted_log_lstsq'] = dict(
        reference, query_log_estimate=queries @ rates,
        holdout_mean=heldout_signs * np.exp(-np.maximum(heldout @ rates, 0)))
    alternatives['finite_design_rank_as_structural'] = dict(
        reference, structural_identifiable=reference['calibration_identifiable'])
    alternatives['claims_every_query_identified'] = dict(
        reference, structural_identifiable=np.ones(len(queries)),
        calibration_identifiable=np.ones(len(queries)))

    def frozen_support(prefix):
        rows = []
        for begin, end, observable in zip(data[prefix + '_ptr'][:-1], data[prefix + '_ptr'][1:],
                                          data[prefix + '_observable']):
            row = model.feature(-2, observable) + model.feature(-1, observable)
            for gate in data[prefix + '_gates'][begin:end]:
                channel = int(model.noise[gate])
                if channel >= 0:
                    row = row + model.feature(channel, observable)
            rows.append(row)
        return np.array(rows)

    frozen_rates, _ = likelihood_fit(frozen_support('train'), signs, data['train_shots'],
                                     data['train_plus'], model.channels)
    alternatives['oracle_labels_but_no_support_propagation'] = dict(
        reference, query_log_estimate=queries @ frozen_rates,
        holdout_mean=heldout_signs * np.exp(-frozen_support('holdout') @ frozen_rates))
    baseline_losses = dict(zip(WEIGHTS, oracle['baseline_loss']))
    reference_losses = dict(zip(WEIGHTS, oracle['reference_loss']))
    results = {}
    for name, output in alternatives.items():
        actual = losses(output, oracle)
        components, score = score_components(actual, baseline_losses, reference_losses)
        results[name] = {'score': score, 'components': components, 'losses': actual}
    structural = model.structural_basis()
    observed = row_basis(calibration)
    statistics = {'parameters': model.parameter_count, 'root_experiments': len(model.rooted_experiments()),
                  'structural_rank': len(structural), 'calibration_rank': len(observed),
                  'structural_not_calibration_queries': int(np.sum(
                      membership(queries, structural) & ~membership(queries, observed))),
                  'near_zero_contrasts': int(np.sum(np.abs(empirical) < 0.08)),
                  'negative_aligned_contrasts': int(np.sum(empirical < 0)),
                  'training_rows': len(calibration), 'max_abs_gate_exposure': float(calibration.max())}
    return results, statistics


def main():
    started = time.monotonic()
    records = []
    for pool in ('core', 'challenge'):
        directory = ROOT / 'private' / ('reference/core' if pool == 'core' else 'challenge_pool')
        manifest = json.loads((directory / 'manifest.json').read_text())
        for entry in manifest['cases']:
            case = directory / entry['case_id']
            with np.load(case / 'input.npz', allow_pickle=False) as archive:
                data = {key: archive[key] for key in archive.files}
            with np.load(case / 'oracle.npz', allow_pickle=False) as archive:
                oracle = {key: archive[key] for key in archive.files}
            results, statistics = audit_case(data, oracle)
            records.append(dict(pool=pool, case_id=entry['case_id'], family=entry['family'],
                                alternatives=results, statistics=statistics))
            print(entry['case_id'], {key: round(value['score'], 4) for key, value in results.items()}, flush=True)
    summary = {}
    for pool in ('core', 'challenge'):
        selected = [record for record in records if record['pool'] == pool]
        summary[pool] = {}
        for name in selected[0]['alternatives']:
            families = {family: float(np.mean([record['alternatives'][name]['score']
                                              for record in selected if record['family'] == family]))
                        for family in sorted({record['family'] for record in selected})}
            summary[pool][name] = {'mean': float(np.mean([record['alternatives'][name]['score']
                                                        for record in selected])),
                                   'worst_family': min(families.values()), 'families': families}
    report = {'summary': summary, 'cases': records, 'runtime': time.monotonic() - started,
              'interpretation': 'Author ablations, not independent participant attempts or a proof of hardness.'}
    (ROOT / 'private/reference/ablation_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
