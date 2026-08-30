from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from prepare_generation_2 import put


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'adversary/generation_1_snapshot'
DESTINATION = ROOT / 'adversary/unfrozen_throughput_draft'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    seal = json.loads((ROOT / 'adversary/frozen_generation_1.json').read_text())
    for filename, expected in seal['sha256'].items():
        assert digest(SNAPSHOT / filename) == expected, filename
    assert not DESTINATION.exists(), 'Refusing to overwrite the archived unfrozen draft'
    DESTINATION.mkdir()
    paths = {}
    for folder in ['participant', 'evaluator']:
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                paths[str(path.relative_to(ROOT))] = digest(path)
        shutil.move(str(ROOT / folder), str(DESTINATION / folder))
        shutil.copytree(SNAPSHOT / folder, ROOT / folder,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for filename in ['status.json', 'README.md']:
        shutil.copyfile(ROOT / filename, DESTINATION / filename)
    for filename in ['unique_calibration_incumbent.json', 'calibration_early_stop.json',
                     'generation_2_progress.md', 'generation_2_science.md']:
        shutil.copyfile(ROOT / 'adversary' / filename, DESTINATION / filename)
    put(DESTINATION / 'manifest.json', {'archived_utc': datetime.now(timezone.utc).isoformat(),
        'reason': 'Unfrozen throughput proposal failed its predeclared robustness policy; no champion quality failure found',
        'frozen': False, 'fresh_attempts': 0, 'hardness_claimed': False, 'sha256': paths,
        'original_snapshot_verified_files': len(seal['sha256'])})
    for filename, expected in seal['sha256'].items():
        if filename.startswith(('participant/', 'evaluator/')):
            assert digest(ROOT / filename) == expected, filename
    print('Restored sealed generation one; archived unfrozen throughput proposal;', len(seal['sha256']), 'snapshot hashes verified')


if __name__ == '__main__':
    main()
