import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]


def main():
    moved = []
    for surface in ('participant', 'evaluator'):
        for directory in sorted((CONCEPT / surface).rglob('__pycache__')):
            if not directory.exists():
                continue
            destination = ROOT / 'quarantine' / directory.relative_to(CONCEPT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            for path in directory.rglob('*'):
                if path.is_file():
                    moved.append({'path': str(path.relative_to(CONCEPT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            shutil.move(str(directory), str(destination))
        for path in list((CONCEPT / surface).rglob('*.pyc')):
            destination = ROOT / 'quarantine' / path.relative_to(CONCEPT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            moved.append({'path': str(path.relative_to(CONCEPT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            shutil.move(str(path), str(destination))
    source = CONCEPT / 'champions' / 'generation_3' / 'state.npz'
    expected = '036e6d9068edb0ac38ce3d3fc4bd935dffcd0b86189f5af25bc4b2f46dde0bea'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    shutil.copyfile(source, CONCEPT / 'participant' / 'baseline' / 'state.npz')
    (ROOT / 'tmp').mkdir(exist_ok=True)
    (ROOT / 'cache_quarantine.json').write_text(json.dumps({'moved': moved, 'baseline_sha256': expected}, indent=2) + '\n')


if __name__ == '__main__':
    main()
