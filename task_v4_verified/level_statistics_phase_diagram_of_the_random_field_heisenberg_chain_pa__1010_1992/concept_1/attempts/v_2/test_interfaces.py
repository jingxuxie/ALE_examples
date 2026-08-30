import json
from pathlib import Path
import subprocess
import sys
import tempfile

from predict import Predictor, read_cases
import numpy as np


def main():
    predictor = Predictor()
    assert predictor.predict([]) == {'predictions': []}
    fields10 = [0.7, -1.2, 2.4, -0.4, 0.1, 1.9, -2.1, 0.5, 1.2, -0.8]
    fields12 = [0.2, 0.8, -1.4, 1.1, -0.9, 2.1, 0.7, -0.4, -2.0, 0.3, 1.8, -1.2]
    cases = []
    for fields in (fields10, fields12):
        values = np.asarray(fields)
        for index, transformed in enumerate((values, values + 7, -values, values[::-1], np.roll(values, 3))):
            cases.append({'id': f'{len(values)}_quote"_newline\n_{index}', 'L': len(values),
                          'fields': transformed.tolist()})
    untouched = json.dumps(cases)
    result = predictor.predict(cases)
    assert json.dumps(cases) == untouched
    assert set(result) == {'predictions'}
    assert len(result['predictions']) == len(cases)
    for case, prediction in zip(cases, result['predictions']):
        assert set(prediction) == {'id', 'f'}
        assert prediction['id'] == case['id']
        assert 0 <= prediction['f'] <= 1
    values = [prediction['f'] for prediction in result['predictions']]
    assert max(values[:5]) - min(values[:5]) < 0.003
    assert max(values[5:]) - min(values[5:]) < 1e-10
    with tempfile.TemporaryDirectory(dir='.') as directory:
        path = Path(directory) / 'cases.json'
        for payload in (cases, {'cases': cases}):
            path.write_text(json.dumps(payload))
            assert read_cases(path) == cases
        path.write_text('\n'.join(json.dumps(case) for case in cases))
        assert read_cases(path) == cases
        output = Path(directory).resolve() / 'predictions.json'
        process = subprocess.run([sys.executable, str(Path(__file__).with_name('predict.py').resolve()),
                                  '--input', str(path.resolve()), '--output', str(output)],
                                 cwd=directory, capture_output=True, text=True, timeout=60)
        assert process.returncode == 0, process.stderr
        assert process.stdout == ''
        file_predictions = json.loads(output.read_text())['predictions']
        assert [entry['id'] for entry in file_predictions] == [case['id'] for case in cases]
        assert all(0 <= entry['f'] <= 1 for entry in file_predictions)
    print('Interface, immutability, and symmetry checks passed.')


if __name__ == '__main__':
    main()
