import argparse
import ast
import json

import numpy as np

from experiment import report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    arguments = parser.parse_args()
    if arguments.path.endswith('.json'):
        records = json.load(open(arguments.path))
    else:
        records = [ast.literal_eval(line) for line in open(arguments.path) if line.startswith("{'index'")]
    families = np.array([record['family'] for record in records])
    for threshold in [0, 0.05, 0.1, 0.2, 0.4, 1, 100]:
        errors = []
        for record in records:
            best = min(record['fits'], key=lambda item: item['fit']) if record['fits'] else None
            error = best['error'] if best and best['fit'] < threshold else record['gp_error']
            errors.append(error)
        report(np.array(errors), families, str(threshold))
    print('count', len(records), 'cpu', sum(row['cpu'] for row in records))
    bad = []
    for record in records:
        best = min(record['fits'], key=lambda item: item['fit']) if record['fits'] else None
        if best and abs(best['error']) > 2e-5:
            bad.append((record['index'], record['family'], round(record['gp_error'] * 1e6, 2), round(best['fit'], 4), round(best['error'] * 1e6, 2)))
    print('bad', bad)


if __name__ == '__main__':
    main()
