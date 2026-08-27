import argparse
import json
from pathlib import Path

from oqs.experiment import campaign, run_case
from oqs.io import load_case


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    individual = subparsers.add_parser('solve')
    individual.add_argument('case')
    individual.add_argument('destination')
    individual.add_argument('--config', default='production')
    suite = subparsers.add_parser('campaign')
    suite.add_argument('input')
    suite.add_argument('output')
    arguments = parser.parse_args()
    configurations = json.loads((Path(__file__).parent / 'configs.json').read_text())
    if arguments.command == 'solve':
        run_case(load_case(arguments.case), arguments.destination,
                 configurations[arguments.config], arguments.config)
    else:
        campaign(arguments.input, arguments.output, configurations)


if __name__ == '__main__':
    main()
