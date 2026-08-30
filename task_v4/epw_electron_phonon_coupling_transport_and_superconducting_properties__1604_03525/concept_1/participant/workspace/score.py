import argparse
import json
import numpy as np
from physics import summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--labels', required=True)
    parser.add_argument('--prediction', required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        inputs = dict(archive)
    with np.load(args.labels, allow_pickle=False) as archive:
        labels = dict(archive)
    with np.load(args.prediction, allow_pickle=False) as archive:
        prediction = archive['alpha2f']
    result = summarize(prediction, labels['alpha2f'], labels['family'], inputs,
                       {'core_score_min': 80, 'worst_family_score_min': 70})
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
