import argparse
import json
import os
from pathlib import Path
import stat
import sys


os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from model import evaluate, load_artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()
    path = arguments.submission
    if path.is_dir():
        path = path / 'witness.json'
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError('Submission must be a regular, unlinked JSON artifact, not a filesystem reference.')
        result = evaluate(load_artifact(path))
    except (ValueError, TypeError, OSError, RecursionError) as error:
        result = {'core_score': 0.0, 'worst_family_score': 0.0, 'passed': False,
                  'valid': False, 'admissible': False, 'resource_score': 0.0,
                  'runtime_seconds': 0.0, 'reason': str(error)}
    payload = json.dumps(result, indent=2) + '\n'
    if arguments.output:
        arguments.output.write_text(payload)
    print(payload, end='')


if __name__ == '__main__':
    main()
