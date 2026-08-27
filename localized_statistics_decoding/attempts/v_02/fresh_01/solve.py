import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import argparse
import json
from pathlib import Path

from inference import decode_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    model = json.loads(Path(__file__).with_name('model.json').read_text())
    dataset = json.loads(Path(arguments.input).read_text())
    predictions = {'cases': [decode_case(case, model) for case in dataset['cases']]}
    Path(arguments.output).write_text(json.dumps(predictions, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
