import argparse
import hashlib
import json
from pathlib import Path


def verify(root):
    selection = json.loads((root / 'SELECTION.json').read_text())
    manifest = json.loads((root / 'PUBLICATION_MANIFEST.json').read_text())
    records = selection['status_records']
    names = [record['directory'] for record in records]
    if len(names) != len(set(names)) or len(names) != selection['verified_task_count']:
        raise ValueError('The verified-task roster has duplicates or an inconsistent count.')
    if any(not name or '/' in name or '\\' in name or name in {'.', '..'} for name in names):
        raise ValueError('Invalid task directory in the selection record.')
    if any(record['saved_status'] != 'hard_verified_achievable' for record in records):
        raise ValueError('The roster contains a different recorded status.')
    selected = selection['selected_directories']
    existing = selection['already_in_random_sample']
    if len(selected) != len(set(selected)) or len(existing) != len(set(existing)):
        raise ValueError('A task is duplicated within the collection lists.')
    if set(selected) & set(existing) or set(selected) | set(existing) != set(names):
        raise ValueError('The supplement and sample do not partition the full verified roster.')
    tasks = [task['directory'] for task in manifest['tasks']]
    if len(tasks) != len(set(tasks)) or set(tasks) != set(selected):
        raise ValueError('The manifest does not contain exactly the remaining tasks.')
    actual = {path.name for path in root.iterdir() if path.is_dir() and path.name != '__pycache__'}
    if actual != set(selected):
        raise ValueError('The installed task folders do not match the selection.')
    sample = json.loads((root.parent / 'task_v4/SAMPLE.json').read_text())
    if not set(existing).issubset(sample['selected_directories_in_draw_order']):
        raise ValueError('A referenced task is absent from the random sample.')
    file_records = {record['path']: record for record in manifest['files']}
    for name in names:
        directory = root / name if name in selected else root.parent / 'task_v4' / name
        raw = (directory / 'status.json').read_bytes()
        status = json.loads(raw)
        if (status.get('final_status') or status.get('status')) != 'hard_verified_achievable':
            raise ValueError('Recorded status is different for ' + name)
        if name in selected:
            expected = file_records[name + '/status.json']['sha256']
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('Captured status hash differs for ' + name)
    return {'verified': True, 'additional_tasks': len(selected),
            'already_in_random_sample': len(existing), 'verified_total': len(names)}


def main():
    parser = argparse.ArgumentParser(description='Check coverage of all recorded verified-achievable v4 tasks.')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    arguments = parser.parse_args()
    try:
        result = verify(arguments.root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'verified': False, 'reason': str(error)}))
        raise SystemExit(1)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
