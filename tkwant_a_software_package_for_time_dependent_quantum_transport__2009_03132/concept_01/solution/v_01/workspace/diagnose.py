import argparse
import json
from pathlib import Path
import numpy as np


def diagnose(directory, other=None):
    directory = Path(directory)
    records = []
    for path in sorted(directory.glob('*.npz')):
        data = np.load(path)
        record = dict(case=path.stem, finite=bool(all(np.all(np.isfinite(data[key])) for key in data.files)),
                      density_min=float(np.min(data['density'])), density_max=float(np.max(data['density'])),
                      density_drift=float(np.max(abs(data['density'] - data['density'][0]))))
        if other and (Path(other) / path.name).exists():
            alternative = np.load(Path(other) / path.name)
            record['density_configuration_difference'] = float(np.max(abs(data['density'] - alternative['density'])))
            record['current_configuration_difference'] = float(np.max(abs(data['current'] - alternative['current'])))
        records.append(record)
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    parser.add_argument('--compare')
    args = parser.parse_args()
    print(json.dumps(diagnose(args.directory, args.compare), indent=2))
