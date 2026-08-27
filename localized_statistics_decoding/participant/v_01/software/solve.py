import argparse
import json
from pathlib import Path

from inference import decode_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    dataset = json.loads(Path(arguments.input).read_text())
    result = {'cases': [decode_case(case) for case in dataset['cases']]}
    Path(arguments.output).write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
