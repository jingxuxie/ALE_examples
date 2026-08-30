import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'participant'
sys.path.insert(0, str(ROOT / 'workspace'))
from atlas import Atlas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', default='10')
    parser.add_argument('--seed', default='81473')
    arguments = parser.parse_args()
    manifest = json.loads((ROOT / 'input' / 'manifest.json').read_text())
    results = []
    for case in manifest['cases']:
        directory = ROOT / 'input' / case['directory']
        output = Path(__file__).parent / (case['id'] + '.json')
        environment = dict(os.environ, ATLAS_SECONDS=arguments.seconds,
                           ATLAS_SEED=arguments.seed, ATLAS_DEBUG='1',
                           OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
        started = time.monotonic()
        subprocess.run([sys.executable, str(Path(__file__).with_name('solve.py')),
                        '--input', str(directory), '--output', str(output)],
                       env=environment, check=True)
        elapsed = time.monotonic() - started
        atlas = Atlas.load(directory)
        result = atlas.score(json.loads(output.read_text())['choices'])
        result['gain'] = 1 - result['objective'] / atlas.metadata['baseline_objective']
        result['case'] = case['id']
        result['seconds'] = elapsed
        results.append(result)
        print(json.dumps(result), flush=True)
    print('mean gain', sum(result['gain'] for result in results) / len(results), flush=True)


if __name__ == '__main__':
    main()
