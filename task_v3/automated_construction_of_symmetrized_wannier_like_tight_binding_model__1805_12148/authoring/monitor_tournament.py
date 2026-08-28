import argparse
import concurrent.futures
import json
import pathlib
import time

from evaluate_tournament import evaluate


ROOT = pathlib.Path(__file__).resolve().parents[1]


def monitor(concept, phase, splits):
    status_path = ROOT / 'authoring/tournament' / phase / (concept + '.json')
    deadline = time.monotonic() + 4500
    while time.monotonic() < deadline:
        try:
            status = json.loads(status_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            status = {}
        if 'finished_utc' in status:
            break
        time.sleep(15)
    else:
        raise RuntimeError('No terminal run record for ' + concept)
    return [evaluate(concept, phase, split) for split in splits]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--concepts', nargs='+', required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--splits', nargs='+', default=['test', 'challenge'])
    arguments = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(arguments.concepts)) as executor:
        futures = [executor.submit(monitor, concept, arguments.phase, arguments.splits) for concept in arguments.concepts]
        rows = [row for future in futures for row in future.result()]
    for split in arguments.splits:
        path = ROOT / 'authoring/tournament' / arguments.phase / f'scoreboard_{split}.json'
        path.write_text(json.dumps([row for row in rows if row['split'] == split], indent=2))


if __name__ == '__main__':
    main()
