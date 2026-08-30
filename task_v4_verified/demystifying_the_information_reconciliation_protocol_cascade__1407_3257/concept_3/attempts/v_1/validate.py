import collections
import hashlib
import json
from pathlib import Path
import random
import resource
import sys
import time

sys.path.insert(0, '/tmp/cascade-c3-g1-v1-re90q176/participant/input')
from simulator import Device
from policy import Policy


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 293140778
    generator = random.Random(seed)
    results = []
    cells = {}
    policy_hash = hashlib.sha256(Path('policy.py').read_bytes()).hexdigest()
    for family in ('RR', 'RS', 'SS'):
        for contamination in (0, 32, 16):
            correct = 0
            for unused in range(count):
                episode_seed = generator.randrange(1 << 63)
                device = Device(family, contamination, episode_seed)
                policy = Policy(device.handle)
                started = time.process_time()
                failure = None
                try:
                    prediction = policy.run()
                    device.handle({'op': 'guess', 'family': prediction})
                except Exception as error:
                    prediction = None
                    failure = repr(error)
                elapsed = time.process_time() - started
                valid = failure is None and elapsed < 8
                success = valid and prediction == family
                correct += success
                result = {'family': family, 'contamination': contamination, 'seed': episode_seed, 'prediction': prediction, 'correct': success, 'failure': failure, 'frames': device.frames, 'queries': device.queries, 'cpu_seconds': elapsed}
                if not success:
                    print('FAIL', json.dumps(result), flush=True)
                    result['trace'] = policy.trace
                    result['neighbors'] = device.neighbors
                results.append(result)
            cell = f'{family}@{contamination}'
            cells[cell] = {'correct': correct, 'total': count}
            print('CELL', cell, correct, '/', count, flush=True)
    summary = {'policy_sha256': policy_hash, 'seed': seed, 'episodes': len(results), 'correct': sum(result['correct'] for result in results), 'cells': cells, 'protocol_failures': dict(collections.Counter(result['failure'] for result in results if result['failure'])), 'maximum_frames': max(result['frames'] for result in results), 'maximum_queries': max(result['queries'] for result in results), 'maximum_cpu_seconds': max(result['cpu_seconds'] for result in results), 'average_cpu_seconds': sum(result['cpu_seconds'] for result in results) / len(results), 'peak_test_process_memory_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    Path(f'validation_{seed}.json').write_text(json.dumps({'summary': summary, 'results': results}, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
