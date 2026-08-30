import argparse
import numpy as np
from threadpoolctl import threadpool_limits
from optimizer import fit
from physics import score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        catalogue = dict(archive)
    best = None
    best_score = -1.0
    with threadpool_limits(limits=1):
        for strategy in ['degree', 'probe']:
            indices, multipliers, _ = fit(catalogue, 43, 32, strategy)
            quality = score(catalogue, indices, multipliers)['score']
            if quality > best_score:
                best_score = quality
                best = (indices, multipliers)
    np.savez(args.output, indices=best[0], multipliers=best[1])


if __name__ == '__main__':
    main()
