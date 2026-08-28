import argparse
import json
import math
from pathlib import Path
import statistics


HERE = Path(__file__).resolve().parent


def normalized_score(result, validation):
    expected = validation['expected_gap_meV']
    actual = result['results'][0]['gap_meV']
    strength = result['results'][0]['strength_meV']
    scale = max(0.20*expected, 0.001)
    gap_score = 1/(1+((actual-expected)/scale)**2)
    true_strength = validation['source_strength_meV']
    calibration = 1/(1+((strength-true_strength)/(0.02*true_strength))**2)
    weak = 0.85/(1+(expected/scale)**2)+0.15/(1+50**2)
    return max(0, (0.85*gap_score+0.15*calibration-weak)/(1-weak))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-exit-code', type=int, required=True)
    parser.add_argument('--pivoted-exit-code', type=int, required=True)
    parser.add_argument('--bounded-exit-code', type=int, required=True)
    arguments = parser.parse_args()
    validation = json.loads((HERE / 'fullsize_source_validation.json').read_text())
    trace_path = HERE / 'mmd_full_trace.jsonl'
    events = [json.loads(line) for line in trace_path.read_text().splitlines()] if trace_path.exists() else []
    phases = [event for event in events if event['event'] == 'phase_complete']
    completed = [event for event in events if event['event'] == 'search_complete']
    expected = validation['expected_gap_meV']
    grid_covered = all(any(abs(event['phase']-math.pi*index/30) < 1e-12 for event in phases) for index in range(31))
    report = dict(
        scope='first archived spot only; not validation of the complete challenge pool',
        source_matrix_validation='fullsize_source_validation.json',
        source_matrix_dimension=124800, archived_expected_gap_meV=expected,
        pivoted_mmd_exit_code=arguments.pivoted_exit_code,
        pivoted_mmd_budget_seconds=360, symmetric_full_exit_code=arguments.full_exit_code,
        symmetric_full_budget_seconds=600, address_space_limit_gib=12,
        full_grid_covered=grid_covered, completed_phase_evaluations=len(phases),
        completed_full_search=bool(completed),
        peak_rss_mib=max((event.get('peak_rss_mib', 0) for event in events), default=0),
        max_eigenpair_residual=max((max(event['residuals']) for event in phases), default=None),
        factor_seconds=sum(event['factor_seconds'] for event in phases),
        eigensolve_seconds=sum(event['eigensolve_seconds'] for event in phases),
        last_elapsed_seconds=events[-1]['elapsed_seconds'] if events else None,
        stored_lookup_is_runtime_proof=False,
    )
    if phases:
        report['phase_seconds'] = dict(min=min(event['total_seconds'] for event in phases),
                                       median=statistics.median(event['total_seconds'] for event in phases),
                                       max=max(event['total_seconds'] for event in phases))
        best = min(phases, key=lambda event:event['minimum_abs_meV'])
        report['best_completed_phase_witness'] = dict(
            phase=best['phase'], energy_meV=best['minimum_abs_meV'],
            archive_absolute_difference_meV=abs(best['minimum_abs_meV']-expected),
            elapsed_seconds=best['elapsed_seconds'], residuals=best['residuals'],
            is_completed_global_minimization=False)
    if completed and arguments.full_exit_code == 0:
        result = json.loads((HERE / 'mmd_full_spot.json').read_text())
        actual = result['results'][0]['gap_meV']
        normalized = normalized_score(result, validation)
        within_budget = result['runtime_seconds'] < 600
        report.update(computed_gap_meV=actual, gap_absolute_error_meV=abs(actual-expected),
                      single_spot_normalized_score=normalized, runtime_seconds=result['runtime_seconds'],
                      minimizing_phase=completed[-1]['minimizing_phase'], within_600_seconds=within_budget,
                      first_spot_reference_gate='passed' if within_budget and grid_covered and normalized > 0.9 else 'failed')
    else:
        report['first_spot_reference_gate'] = 'not_validated_within_budget'
        report['reason'] = 'No completed 31-point grid plus local refinement; phase witnesses are not a global-gap result.'
    witness_path = HERE / 'mmd_symmetric_zero_witness.json'
    if witness_path.exists():
        witness = json.loads(witness_path.read_text())['results'][0]
        report['zero_phase_witness'] = witness
        report['zero_phase_witness_absolute_difference_meV'] = abs(witness['phase_minimum_abs_meV']-expected)
    bounded_events = [json.loads(line) for line in (HERE / 'mmd_bounded_trace.jsonl').read_text().splitlines()]
    bounded_phases = [event for event in bounded_events if event['event'] == 'phase_complete']
    bounded_search = [event for event in bounded_events if event['event'] == 'search_complete']
    alternative = dict(exit_code=arguments.bounded_exit_code,
                       initial_grid_points=9, refinement='bounded',
                       is_source_31_point_fmin_replay=False,
                       completed_phase_evaluations=len(bounded_phases),
                       max_eigenpair_residual=max((max(event['residuals']) for event in bounded_phases), default=None),
                       peak_rss_mib=max((event.get('peak_rss_mib', 0) for event in bounded_events), default=0),
                       elapsed_seconds=bounded_events[-1]['elapsed_seconds'] if bounded_events else None)
    if bounded_phases:
        best = min(bounded_phases, key=lambda event:event['minimum_abs_meV'])
        alternative['best_completed_phase_witness'] = dict(
            phase=best['phase'], energy_meV=best['minimum_abs_meV'],
            archive_absolute_difference_meV=abs(best['minimum_abs_meV']-expected),
            elapsed_seconds=best['elapsed_seconds'], residuals=best['residuals'],
            is_completed_global_minimization=False)
    if bounded_search and arguments.bounded_exit_code == 0:
        bounded_result = json.loads((HERE / 'mmd_bounded_spot.json').read_text())
        actual = bounded_result['results'][0]['gap_meV']
        alternative.update(computed_gap_meV=actual, gap_absolute_error_meV=abs(actual-expected),
                           single_spot_normalized_score=normalized_score(bounded_result, validation),
                           runtime_seconds=bounded_result['runtime_seconds'],
                           minimizing_phase=bounded_search[-1]['minimizing_phase'],
                           archive_value_reproduced=abs(actual-expected) < 1e-6,
                           within_600_seconds=bounded_result['runtime_seconds'] < 600)
    report['bounded_search_alternative'] = alternative
    (HERE / 'resource_gate_report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
