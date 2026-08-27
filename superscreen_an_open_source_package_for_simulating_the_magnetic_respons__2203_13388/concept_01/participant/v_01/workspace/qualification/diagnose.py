import argparse
import json
from pathlib import Path

import numpy as np

from .model import load_case, summarize, triangle_geometry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('suite')
    parser.add_argument('output')
    args = parser.parse_args()
    suite_path, output = Path(args.suite), Path(args.output)
    for configuration in sorted((output / 'raw').iterdir()):
        for filename in json.loads(suite_path.read_text())['cases']:
            case = load_case(suite_path.parent / filename)
            with np.load(configuration / filename) as archive:
                result = dict(archive)
            _, _, current_x, current_y = triangle_geometry(case)
            derived = np.stack(((current_x @ result['stream'].T).T, (current_y @ result['stream'].T).T), axis=-1)
            rows = summarize(case, result)
            print(json.dumps({'case': case.meta['id'], 'configuration': configuration.name,
                              'reciprocity_error': rows[0]['reciprocity_error'],
                              'linearity_error': rows[0]['linearity_error'],
                              'max_fluxoid_constraint_error': max(row['fluxoid_constraint_error'] for row in rows),
                              'current_stream_inconsistency': float(np.linalg.norm(derived - result['current']))}))


if __name__ == '__main__':
    main()
