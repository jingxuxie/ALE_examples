import json
from pathlib import Path


def make_witness():
    weights = [[0.0] * 16 for position in range(16)]
    for position in range(1, 12):
        weights[position][0] = 9.2
    return {
        'schema_version': 1,
        'bonds': [1, 1, 1, 1, 1, -1, 1, 1,
                  -1, 1, -1, 1, 1, 1, -1, 1,
                  1, 1, 1, 1, 1, 1, 1, 1,
                  -1, 1, -1, 1, -1, 1, 1, -1],
        'beta': 1.6,
        'order': [5, 0, 1, 2, 3, 7, 8, 9, 10, 11, 12, 14, 4, 6, 13, 15],
        'weights': weights,
        'pattern': [1, -1, -1, -1, 1, -1, 1, 1, 1, 1, 1, 1, 1, -1, -1, 1],
        'radius': 4,
    }


if __name__ == '__main__':
    destination = Path(__file__).resolve().parent / 'witness.json'
    destination.write_text(json.dumps(make_witness(), indent=2, allow_nan=False) + '\n')
    print(destination)
