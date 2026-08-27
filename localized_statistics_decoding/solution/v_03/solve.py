import argparse

import numpy as np

from core import make_decoders, recover


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    data = np.load(arguments.input, allow_pickle=False)
    matrix = data['H'].astype(np.uint8)
    priors = data['prior'].astype(float)
    decoders = make_decoders(matrix, priors)
    corrections = np.asarray([recover(matrix, syndrome, priors, reliability, decoders)
                               for syndrome, reliability in zip(data['syndrome'], data['soft_llr'])], dtype=np.uint8)
    np.savez_compressed(arguments.output, correction=corrections)


if __name__ == '__main__':
    main()
