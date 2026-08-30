import json
import os
import random
import subprocess
import sys
from pathlib import Path

source = Path(os.environ['P'])
sys.path.insert(0, str(source / 'workspace'))
from design_common import load_case, generate_supports, score_case

generator = random.Random(930293)
patterns = [[generator.randrange(3) for _ in range(24)] for _ in range(3)]
patterns.append([int(axis) for axis in '221100100221221100100221'])
for pattern in patterns:
    text = ''.join(map(str, pattern))
    rows = subprocess.check_output(['./optimize', 'check', '1', text], text=True).splitlines()[1:10]
    observed = [list(map(float, row.split()[2:])) for row in rows]
    expected = []
    for scale in range(1, 4):
        case = load_case(source / f'input/scale_{scale}.json.gz')
        records = generate_supports(case, 731 + 37 * (scale - 1), 512)
        scores = score_case(case, records, pattern)
        for family in ['iid_28', 'iid_30', 'iid_32']:
            expected.append([scores[family]['fraction'], scores[family]['mean_ambiguity']])
    assert all(abs(actual - reference) < 1e-6
               for actual_row, reference_row in zip(observed, expected)
               for actual, reference in zip(actual_row, reference_row)), (text, observed, expected)
    print(text, 'PASS', flush=True)
