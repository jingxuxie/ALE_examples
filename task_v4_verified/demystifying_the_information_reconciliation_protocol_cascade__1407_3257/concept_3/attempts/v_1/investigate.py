import collections
import json
import random
import sys
import time

sys.path.insert(0, '/tmp/cascade-c3-g1-v1-re90q176/participant/input')
from simulator import Device
from policy import Policy


def run_case(family, contamination, seed, verbose=False):
    device = Device(family, contamination, seed)
    policy = Policy(device.handle)
    started = time.process_time()
    failure = None
    try:
        prediction = policy.run()
    except Exception as error:
        prediction = None
        failure = repr(error)
    elapsed = time.process_time() - started
    result = {'family': family, 'contamination': contamination, 'seed': seed, 'prediction': prediction, 'frames': device.frames, 'queries': device.queries, 'cpu': elapsed, 'failure': failure}
    discoveries = []
    for entry in policy.trace:
        if entry[0] == 'discover':
            center = entry[1]
            neighbors = device.neighbors[center]
            triangles = sum(second in device.neighbors[first] and third in device.neighbors[first] and third in device.neighbors[second] for first, second, third in __import__('itertools').combinations(neighbors, 3))
            discoveries.append({'center': center, 'kind': 'R' if triangles else 'S', 'good_core': sum(site in neighbors for site, count in entry[3]), 'true_neighbors': neighbors})
    result['discoveries'] = discoveries
    if verbose or prediction != family:
        print(json.dumps(result), policy.trace, flush=True)
    return result


if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    offset = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
    results = []
    for family in ('RR', 'RS', 'SS'):
        for contamination in (0, 32, 16):
            cell = []
            for index in range(count):
                result = run_case(family, contamination, offset + index + len(results) * 13)
                cell.append(result)
                results.append(result)
            print('CELL', family, contamination, sum(result['prediction'] == family for result in cell), '/', count, 'cpu', sum(result['cpu'] for result in cell) / count, flush=True)
    print('TOTAL', sum(result['prediction'] == result['family'] for result in results), '/', len(results), flush=True)
    with open('investigate_results.json', 'w') as handle:
        json.dump(results, handle)
