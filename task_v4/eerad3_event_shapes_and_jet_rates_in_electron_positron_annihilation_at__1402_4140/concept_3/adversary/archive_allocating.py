import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def main(draft, reason):
    destination_root = ROOT / 'adversary' / draft
    if destination_root.exists():
        raise RuntimeError('Draft archive already exists')
    destination_root.mkdir()
    target = json.loads((ROOT / 'evaluator/hidden/target.json').read_text())
    expected = dict(target['required_sha256'])
    expected['evaluator/binary_driver.f90'] = expected['evaluator/hidden/driver.f90']
    archived, replaced = {}, []
    for section in ['participant', 'evaluator']:
        for source in sorted((ROOT / section).rglob('*')):
            if not source.is_file() or '__pycache__' in source.parts:
                continue
            relative = str(source.relative_to(ROOT))
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if relative in expected and digest != expected[relative]:
                if relative == 'evaluator/binary_driver.f90':
                    content = (ROOT / 'evaluator/hidden/driver.f90').read_bytes()
                    digest = hashlib.sha256(content).hexdigest()
                if digest != expected[relative]:
                    replaced.append(relative)
                    continue
            destination = destination_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            archived[relative] = digest
    for relative in ['status.json', 'adversary/ratchet_unique.py', 'adversary/generation_2_progress.md',
                     'adversary/generation_2_unique_controls.json', 'adversary/generation_2_schema_controls.json',
                     'adversary/generation_2_staging_audit.json', 'adversary/unique_two_campaigns.log',
                     'adversary/unique_memfd_calibration.log', 'adversary/unique_memfd_stage.log',
                     'adversary/unique_mmap_calibration.log', 'adversary/unique_mmap_stage.log',
                     'adversary/unique_mmap_controls.log']:
        source = ROOT / relative
        if source.exists():
            shutil.copyfile(source, destination_root / source.name)
    for pattern in ['unique_calibration_*.json', 'unique_repeat_*.json']:
        for source in sorted((ROOT / 'adversary').glob(pattern)):
            shutil.move(source, destination_root / source.name)
    (destination_root / 'archive.json').write_text(json.dumps({
        'superseded': True, 'reason': reason,
        'resource_target_committed': False, 'generation_2_frozen': False,
        'files_sha256': archived, 'already_replaced_by_main_and_not_misrepresented_as_old': replaced,
        'protected_allocating_sha256': expected}, indent=2) + '\n')
    print('Archived', draft, '; already replaced canonical files:', replaced)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--draft', default='allocating_memfd_draft')
    parser.add_argument('--reason', default='Native allocation, zeroing and copying dominated short baseline measurements')
    arguments = parser.parse_args()
    main(arguments.draft, arguments.reason)
