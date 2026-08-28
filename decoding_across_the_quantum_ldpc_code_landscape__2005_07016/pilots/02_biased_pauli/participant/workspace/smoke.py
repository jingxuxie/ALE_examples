import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np


def main():
    parser = argparse.ArgumentParser(description='Structural check only; no quality labels')
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
        output = Path(directory) / 'answer.npz'
        subprocess.run([sys.executable, str(Path(__file__).with_name('solve.py')),
                        '--input', str(Path(args.input).resolve()), '--output', str(output)],
                       check=True, timeout=180)
        with np.load(args.input, allow_pickle=False) as case, np.load(output, allow_pickle=False) as answer:
            assert set(answer.files) == {'correction_x', 'correction_z'}
            for name in answer.files:
                assert answer[name].shape == (len(case['syndrome']), len(case['frame']))
                assert answer[name].dtype.kind in 'biu'
                assert np.all((answer[name] == 0) | (answer[name] == 1))
            actual = (answer['correction_x'] @ case['gz'].T
                      + answer['correction_z'] @ case['gx'].T) % 2
            assert np.array_equal(actual, case['syndrome'])
    print('Structural smoke passed; logical quality is not measured.')


if __name__ == '__main__':
    main()
