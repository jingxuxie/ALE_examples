import concurrent.futures
import json
import os
import sys
from pathlib import Path
from subspace_synth import synthesize, SUITE
from compact import usage

sys.path.insert(0, os.environ['ROOT'] + '/workspace')
from verify import check

def run(index):
    return index, synthesize(SUITE[index], 4, 4, 20)

def quality(circuit, instance):
    resources = usage(circuit, instance['n'])
    ratios = [resources[key] / instance['caps'][key] for key in resources]
    return max(ratios), sum(ratios), resources['and'], resources['affine']

if __name__ == '__main__':
    data = json.loads(Path('circuits.json').read_text())
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for index, candidate in pool.map(run, [1, 2, 4, 5]):
            if candidate is None:
                print(SUITE[index]['id'], 'search timed out', flush=True)
                continue
            result = check(SUITE[index], candidate)
            print(json.dumps(result), flush=True)
            if result['exact']:
                Path('candidate_' + SUITE[index]['id'] + '.json').write_text(json.dumps(candidate))
                if quality(candidate, SUITE[index]) < quality(data['circuits'][index], SUITE[index]):
                    data['circuits'][index] = candidate
                    Path('circuits.json').write_text(json.dumps(data, separators=(',', ':')))
    for path in ['global10a.json', 'global10b.json', 'global10c.json']:
        try:
            candidate = json.loads(Path(path).read_text())
            result = check(SUITE[0], candidate)
            if result['exact'] and quality(candidate, SUITE[0]) < quality(data['circuits'][0], SUITE[0]):
                data['circuits'][0] = candidate
        except (ValueError, KeyError, TypeError):
            pass
    Path('circuits.json').write_text(json.dumps(data, separators=(',', ':')))
