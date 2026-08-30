import copy
import json
from pathlib import Path
import sys
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
import evaluate


def main():
    cases = json.loads((evaluate.HIDDEN / 'cases.json').read_text())
    references = json.loads((evaluate.HIDDEN / 'references.json').read_text())
    target = json.loads((evaluate.HIDDEN / 'target.json').read_text())
    control = {'metamorphic_trials_checked': [], 'baseline_errors_classified': []}
    child_index = next(index for index, case in enumerate(cases) if case.get('parent'))
    records = [[0.0] * 84 for case in cases]
    assert evaluate.check(cases[0], references[0], records[0], target)
    for trial_index in range(3):
        trials = [copy.deepcopy(records) for trial in range(3)]
        trials[trial_index][child_index][25] = sum(vector[3] for vector in cases[child_index]['p']) / 100

        def fake_measure(*args):
            evaluate.measure.last_accounting = []
            evaluate.measure.last_record_trials = trials
            return trials[-1], 1.0, [1.0, 1.0, 1.0]

        with patch.object(evaluate, 'build', return_value=Path('/unused/runner')), \
                patch.object(evaluate, 'measure', side_effect=fake_measure), \
                patch.object(evaluate, 'check', return_value=[]):
            result = evaluate.evaluate(ROOT / 'participant/workspace')
        assert result['valid'] and not result['passed']
        assert any('metamorphic_covariance' in failure['checks'] for failure in result['failures'])
        control['metamorphic_trials_checked'].append(trial_index + 1)
    for phase in ['build', 'measure']:
        failure = RuntimeError('execution_failure: synthetic pristine baseline failure')
        builds = [Path('/unused/runner'), failure] if phase == 'build' else [Path('/unused/runner')] * 2
        with patch.object(evaluate, 'build', side_effect=builds), \
                patch.object(evaluate, 'measure', side_effect=failure):
            try:
                evaluate.evaluate(ROOT / 'participant/workspace')
                raise AssertionError('Pristine baseline failure was accepted')
            except RuntimeError as error:
                result = evaluate.exception_result(error)
        expected = 'environment_error' if phase == 'build' else 'measurement_error'
        assert result['error_type'] == expected and result['infrastructure_error']
        assert not result['valid'] and not result['passed']
        assert all(result[key] == 0 for key in ['core_score', 'worst_family_score', 'runtime_score'])
        control['baseline_errors_classified'].append(expected)
    control['zero_records_fail_physics'] = True
    control['passed'] = True
    (ROOT / 'adversary/release_audit_unit_controls.json').write_text(json.dumps(control, indent=2) + '\n')
    print('All-trial covariance, baseline-error classification, zero-output physics: PASS')


if __name__ == '__main__':
    main()
