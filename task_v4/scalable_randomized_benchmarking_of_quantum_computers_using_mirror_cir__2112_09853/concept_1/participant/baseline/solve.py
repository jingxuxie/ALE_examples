import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    artifact = {'single': [[[20, 20, 20] for class_index in range(6)] for site in range(4)],
                'cx': [[4] * 15 for edge in range(8)]}
    arguments.output.write_text(json.dumps(artifact, indent=2) + '\n')


if __name__ == '__main__':
    main()
