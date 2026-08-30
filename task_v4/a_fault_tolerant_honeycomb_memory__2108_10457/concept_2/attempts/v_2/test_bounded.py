import itertools
import json
import os
import subprocess
from pathlib import Path

from engine import Samples


baseline = json.loads(Path(os.environ['P'] + '/baseline/design.json').read_text())['z_image']
samples = Samples(1, 8721382, 64, .32)
for test_index, cells in enumerate([(0, 1, 2, 3, 4, 5), (0, 4, 8, 12, 16, 20), (3, 7, 11, 15, 19, 23)]):
    restriction = list(map(str, baseline))
    for cell in cells:
        restriction[cell] = '?'
    expected = {}
    for values in itertools.product(range(3), repeat=len(cells)):
        axes = baseline.copy()
        for cell, value in zip(cells, values):
            axes[cell] = value
        correct = round(samples.score(axes) * 64)
        if correct >= 10:
            expected[''.join(map(str, axes))] = correct
    for order in range(2):
        for canonical in range(2):
            filtered = {pattern: score for pattern, score in expected.items() if not canonical or pattern[0] == min(pattern[index] for index in range(0, 24, 3))}
            tag = f'test_bounded_{test_index}_{order}_{canonical}'
            subprocess.run(['./bounded_test', '10', '.32', '8721382', tag, str(order), '-', ''.join(restriction), str(canonical)], check=True, capture_output=True)
            actual = {pattern: int(score) for pattern, score in (line.split() for line in Path(tag + '.raw').read_text().splitlines())}
            assert actual == filtered, (test_index, order, canonical, len(filtered), len(actual))
            print('passed', test_index, order, canonical, 'survivors', len(actual), flush=True)
