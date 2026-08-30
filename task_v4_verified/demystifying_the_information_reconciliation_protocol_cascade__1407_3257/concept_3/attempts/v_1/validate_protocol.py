import hashlib
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, '/tmp/cascade-c3-g1-v1-re90q176/participant/workspace')
from dev_evaluate import run_episode


def main():
    generator = random.Random(297426038)
    results = []
    cells = {}
    for family in ('RR', 'RS', 'SS'):
        for contamination in (0, 32, 16):
            correct = 0
            for unused in range(20):
                case = {'family': family, 'contamination_denominator': contamination, 'seed': generator.randrange(1 << 63)}
                result = run_episode('limited_policy.py', case)
                result['case'] = case
                results.append(result)
                correct += result['correct']
            cells[f'{family}@{contamination}'] = {'correct': correct, 'total': 20}
            print('CELL', family, contamination, correct, '/ 20', flush=True)
    summary = {'policy_sha256': hashlib.sha256(Path('policy.py').read_bytes()).hexdigest(), 'policy_bytes': Path('policy.py').stat().st_size, 'episodes': len(results), 'correct': sum(result['correct'] for result in results), 'cells': cells, 'failures': [result for result in results if result['failure']], 'wall_limit_seconds': 12, 'cpu_limit_seconds': 8, 'address_space_limit_mib': 512, 'maximum_elapsed_seconds': max(result['elapsed_seconds'] for result in results), 'maximum_frames': max(result['frames'] for result in results), 'maximum_queries': max(result['queries'] for result in results)}
    Path('protocol_validation.json').write_text(json.dumps({'summary': summary, 'results': results}, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
