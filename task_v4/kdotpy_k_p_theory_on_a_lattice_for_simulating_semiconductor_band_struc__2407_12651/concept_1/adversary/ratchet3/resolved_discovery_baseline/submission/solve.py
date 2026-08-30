import argparse
import json
import sys
from pathlib import Path

workspace = Path(__file__).resolve().parents[1] / 'workspace'
if workspace.is_dir():
    sys.path.insert(0, str(workspace))

from atlas import Atlas, single_descent


def solve(directory):
    atlas = Atlas.load(directory)
    return single_descent(atlas, atlas.seed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    choices = solve(arguments.input)
    Path(arguments.output).write_text(json.dumps({'choices': choices.tolist()}) + '\n')


if __name__ == '__main__':
    main()
