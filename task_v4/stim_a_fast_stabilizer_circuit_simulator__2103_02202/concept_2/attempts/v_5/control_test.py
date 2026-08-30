import json
import subprocess
from pathlib import Path
from probe import COLUMNS, MODEL


def main():
    directory = Path('control')
    directory.mkdir(exist_ok=True)
    columns = COLUMNS.copy()
    observable = MODEL['observable'].copy()
    columns[11] = 0
    observable[11] = 1
    for fault in range(11):
        columns[11] ^= columns[fault]
        observable[11] ^= observable[fault]
    with (directory / 'columns.txt').open('w') as stream:
        for fault, column in enumerate(columns):
            stream.write(' '.join(f'{(column >> shift) & ((1 << 64) - 1):016x}' for shift in (0, 64, 128)) + f' {observable[fault]}\n')
    commands = [
        ['../vector_exact', '30', '8714253', '10', '-1', 'vector_exact.json'],
        ['../vector_search', '30', '8714253', '11', '132', 'vector_augmented.json'],
        ['../search3', '1', '30', '8714253', '20', 'triples.json'],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=directory, capture_output=True, text=True)
        print(command[0], result.returncode, result.stderr[-1500:])
        assert result.returncode == 0
        support = json.loads((directory / command[-1]).read_text())['faults']
        assert support == list(range(12)), support
    print('All planted-control checks passed')


if __name__ == '__main__':
    main()
