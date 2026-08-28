import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--calibration', required=True)
    parser.add_argument('--records', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    metadata = json.loads(Path(arguments.calibration).read_text())
    records = np.load(arguments.records)
    mean_occupancy = np.mean([int(value).bit_count() / 8 for value in records['syndrome'].ravel()])
    rate = float(np.clip(mean_occupancy / 3, 0.01, 0.35))
    model = {'offsets': [[float(np.log(rate / (1-rate)))] * metadata['rate_groups']],
             'slopes': [0.0] * metadata['rate_groups'], 'initial': [1.0], 'transition': [[1.0]]}
    Path(arguments.output).write_text(json.dumps(model, indent=2) + '\n')


if __name__ == '__main__':
    main()
