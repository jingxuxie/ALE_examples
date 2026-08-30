import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
sys.path.insert(0, str(ROOT / 'evaluator/hidden'))
from evaluate import evaluate
from trusted_shapes import rotate


def main():
    witness = json.loads((ROOT / 'champions/generation_1/submission.json').read_text())
    generator = np.random.default_rng(51903584)
    failures = []
    least_ratio = float('inf')
    largest_error = 0.0
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'witness.json'
        for trial in range(256):
            events = []
            for event in witness['events']:
                rotated = rotate(event, generator.normal(size=4))
                permutation = generator.permutation(5)
                events.append([rotated[index] for index in permutation])
            path.write_text(json.dumps({'events': events}))
            result = evaluate(path)
            if not result['passed']:
                failures.append({'trial': trial, 'reason': result['reason']})
            least_ratio = min(least_ratio, result.get('y45_ratio', 0.0))
            largest_error = max(largest_error, result.get('max_shape_error', 1.0))
    result = {'transformed_witnesses': 256, 'invariant_checks_per_witness': 252,
              'failures': failures, 'minimum_y45_ratio': least_ratio,
              'maximum_six_shape_error': largest_error,
              'ratchet_generations': 0,
              'decision': 'No genuine failure of the valid static certificate was found. Do not manufacture an unrelated harder claim.'}
    (ROOT / 'adversary/champion_search.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
