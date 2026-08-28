import argparse

import numpy as np

from repair import prepare_columns, repair


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    data = np.load(arguments.input, allow_pickle=False)
    columns = prepare_columns(data['H'])
    predictions = np.asarray([repair(columns, syndrome, reliability)
                              for syndrome, reliability in zip(data['syndrome'], data['soft_llr'])], dtype=np.uint8)
    np.savez_compressed(arguments.output, correction=predictions)
