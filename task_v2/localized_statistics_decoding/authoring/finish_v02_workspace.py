import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def write_code(path, content):
    patch = '*** Begin Patch\n*** Add File: ' + str(path) + '\n'
    patch += ''.join('+' + line + '\n' for line in content.splitlines()) + '*** End Patch\n'
    subprocess.run(['apply_patch'], input=patch, text=True, check=True, capture_output=True)


def main():
    write_code(ROOT / 'participant/v_02/software/binary.py', (ROOT / 'participant/v_01/software/binary.py').read_text())
    evaluator = (ROOT / 'evaluator/v_01/evaluate.py').read_text()
    evaluator = evaluator.replace(
        "    mode_error = distribution_error(predicted.get('mode_posterior'), expected['mode_posterior'])",
        "    log_error /= max(1, expected['observed_checks'])\n"
        "    switches = predicted.get('switch_probability')\n"
        "    if isinstance(switches, list) and len(switches) == len(expected['switch_probability']):\n"
        "        switch_errors = [finite_error(value, truth, probability=True) for value, truth in zip(switches, expected['switch_probability'])]\n"
        "    else:\n"
        "        switch_errors = [math.inf]\n"
        "    switch_error = sum(switch_errors) / len(switch_errors)")
    evaluator = evaluator.replace('ramp(error, 0.02, 0.15)', 'ramp(error, 0.03, 0.20)')
    evaluator = evaluator.replace('ramp(error, 0.025, 0.15)', 'ramp(error, 0.03, 0.20)')
    evaluator = evaluator.replace("'log_evidence': ramp(log_error, 0.08, 2.0)", "'log_evidence': ramp(log_error, 0.01, 0.06)")
    evaluator = evaluator.replace("'mode_posterior': ramp(mode_error, 0.02, 0.15)",
                                  "'switch_probability': sum(ramp(error, 0.04, 0.30) for error in switch_errors) / len(switch_errors)")
    evaluator = evaluator.replace("0.4 * components['joint_logical'] + 0.25 * components['query_parity']\n"
                                  "             + 0.2 * components['log_evidence'] + 0.1 * components['mode_posterior']\n"
                                  "             + 0.05 * components['logical_decision']",
                                  "0.4 * components['joint_logical'] + 0.2 * components['query_parity']\n"
                                  "             + 0.2 * components['log_evidence'] + 0.2 * components['switch_probability']")
    evaluator = evaluator.replace("'log_evidence_abs': rounded(log_error), 'mode_tv': rounded(mode_error)",
                                  "'log_evidence_per_observed_bit_abs': rounded(log_error), 'switch_abs_mean': rounded(switch_error)")
    evaluator = evaluator.replace("'validation': False}", "'validation': False, 'model': (submission / 'model.json').is_file(), 'training': (submission / 'train.py').is_file()}")
    write_code(ROOT / 'evaluator/v_02/evaluate.py', evaluator)
    for path in (ROOT / 'evaluator/v_02/hidden').glob('*expected.json'):
        expected = json.loads(path.read_text())
        if path.name == 'public_expected.json':
            inputs = json.loads((ROOT / 'participant/v_02/input/validation.json').read_text())
        else:
            inputs = json.loads(path.with_name(path.name.replace('_expected', '')).read_text())
        by_id = {case['id']: case for case in inputs['cases']}
        for case in expected['cases']:
            case['observed_checks'] = sum(value is not None for shot in by_id[case['id']]['shots'] for value in shot['syndrome'])
        path.write_text(json.dumps(expected, indent=2) + '\n')


if __name__ == '__main__':
    main()
