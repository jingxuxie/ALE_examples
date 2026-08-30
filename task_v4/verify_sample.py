import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path


def verify(record):
    population = [item['directory'] for item in record['population']]
    if population != sorted(set(population)):
        raise ValueError('Population must contain sorted, unique task names.')
    if len(population) != record['population_size']:
        raise ValueError('Population size does not match the frozen names.')
    digest = hashlib.sha256(('\n'.join(population) + '\n').encode()).hexdigest()
    if digest != record['population_sha256']:
        raise ValueError('Population name hash does not match.')
    selected = record['selected_directories_in_draw_order']
    reproduced = random.Random(int(record['seed_hex'], 16)).sample(population, record['sample_size'])
    if reproduced != selected:
        raise ValueError('The selected tasks do not reproduce from the recorded seed.')
    lookup = {item['directory']: item for item in record['population']}
    population_counts = dict(Counter(item['saved_status'] for item in record['population']))
    sample_counts = dict(Counter(lookup[name]['saved_status'] for name in selected))
    if population_counts != record['population_status_counts']:
        raise ValueError('Population status counts do not match.')
    if sample_counts != record['sample_status_counts']:
        raise ValueError('Sample status counts do not match.')
    return {'verified': True, 'population_size': len(population),
            'sample_size': len(selected), 'sample_status_counts': sample_counts}


def main():
    parser = argparse.ArgumentParser(description='Replay and check the recorded random task sample.')
    parser.add_argument('--record', type=Path, default=Path(__file__).resolve().parent / 'SAMPLE.json')
    arguments = parser.parse_args()
    try:
        result = verify(json.loads(arguments.record.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'verified': False, 'reason': str(error)}))
        raise SystemExit(1)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
