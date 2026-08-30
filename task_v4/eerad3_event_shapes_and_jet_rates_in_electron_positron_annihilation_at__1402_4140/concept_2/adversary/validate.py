import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
sys.path.insert(0, str(ROOT / 'participant/workspace'))
from evaluate import evaluate
from shapes import calculate, random_event
from trusted_shapes import observables, NAMES


def main():
    witness_path = ROOT / 'champions/search_best.json'
    witness = json.loads(witness_path.read_text())
    result = evaluate(witness_path)
    assert result['passed'], result
    generator = np.random.default_rng(191044)
    events = [random_event(generator).tolist() for unused in range(200)] + witness['events']
    discrepancy = 0.0
    for event in events:
        public, trusted = calculate(event), observables(event)
        discrepancy = max(discrepancy, *(abs(public[key]-trusted[key]) for key in NAMES+('y34','y45')))
        assert public['hemisphere_occupancy'] == trusted['hemisphere_occupancy']
    assert discrepancy < 2e-12
    defective = {'copy': {'events': [witness['events'][0], witness['events'][0]]},
                 'wrong_shape': {'events': [witness['events'][0]]},
                 'negative_energy': {'events': [[[-row[0], *row[1:]] for row in witness['events'][0]], witness['events'][1]]}}
    rejections = {}
    with tempfile.TemporaryDirectory() as directory:
        for name, payload in defective.items():
            path = Path(directory) / f'{name}.json'
            path.write_text(json.dumps(payload))
            score = evaluate(path)
            assert not score['passed']
            rejections[name] = {'passed': score['passed'], 'valid': score['valid'], 'reason': score['reason']}
        for name, raw in [('nan', '{"events":NaN}'), ('duplicate', '{"events":[],"events":[]}')]:
            path = Path(directory) / f'{name}.json'
            path.write_text(raw)
            score = evaluate(path)
            assert not score['valid']
            rejections[name] = score['reason']
    native = ROOT / 'adversary/native_driver'
    source = ROOT.parent / 'research/releases/src/analyses'
    subprocess.run(['gfortran', '-O2', '-ffixed-line-length-none', str(source/'eventshapes.f'),
                    str(source/'jetalgo.f'), str(ROOT/'adversary/native_driver.f90'), '-o', str(native)], check=True)
    stream = str(len(events))+'\n'+'\n'.join(' '.join(format(value,'.17g') for value in row)
                                                  for event in events for row in event)+'\n'
    completed = subprocess.run([str(native)], input=stream, text=True, capture_output=True, check=True)
    actual = np.array([[float(value) for value in line.split()] for line in completed.stdout.splitlines()])
    expected = np.array([[observables(event)[key] for key in NAMES+('y34','y45')] for event in events])
    native_error = float(np.max(np.abs(actual-expected)))
    assert native_error < 2e-12, native_error
    report = {'private_witness_passed': True, 'private_witness_score': result,
              'public_trusted_max_difference': discrepancy, 'native_max_difference': native_error,
              'independent_random_events': 200, 'negative_controls': rejections}
    (ROOT/'adversary/checker_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'adversary/witness_metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key != 'private_witness_score'},indent=2))


if __name__ == '__main__':
    main()
