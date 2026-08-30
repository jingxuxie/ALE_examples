import json
from pathlib import Path
from probe import COLUMNS, MODEL


def inspect(path):
    try:
        artifact = json.loads(path.read_text())
        faults = artifact['faults']
        if set(artifact) != {'faults'} or not faults or len(set(faults)) != len(faults):
            return None
        if any(type(fault) is not int or not 0 <= fault < 512 for fault in faults):
            return None
        syndrome = 0
        logical = 0
        for fault in faults:
            syndrome ^= COLUMNS[fault]
            logical ^= MODEL['observable'][fault]
        weight = len(faults)
        detector_weight = syndrome.bit_count()
        valid = weight <= 36 and not detector_weight and logical == 1
        score = 1.0 if valid else 0.10 + 0.15 * min(1, 36 / weight) + 0.45 * (1 - detector_weight / 192) + 0.10 * logical
        return score, weight, detector_weight, logical, valid, sorted(faults)
    except (ValueError, KeyError, TypeError, OSError):
        return None


def main():
    candidates = []
    for path in Path('.').glob('*.json'):
        result = inspect(path)
        if result is not None:
            print(path.name, result[:5])
            candidates.append((result[0], str(path), result))
    score, source, result = max(candidates)
    temporary = Path('witness.pending')
    temporary.write_text(json.dumps({'faults': result[-1]}, separators=(',', ':')) + '\n')
    temporary.replace('witness.json')
    print('SELECTED', source, 'score', score, 'valid', result[4])


if __name__ == '__main__':
    main()
