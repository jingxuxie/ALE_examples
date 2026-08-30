import argparse
import concurrent.futures
import time
from pathlib import Path

import numpy as np

from pair_model import CASOracle, FAMILIES, sample_model


def generate_one(task):
    seed, family_index = task
    model = sample_model(seed, FAMILIES[family_index])
    return CASOracle(model).all_energies(), model['orbital_energy'], family_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=12000)
    parser.add_argument('--seed', type=int, default=910000)
    parser.add_argument('--output', default='train.npz')
    arguments = parser.parse_args()
    started = time.time()
    tasks = [(arguments.seed + index, index % 6) for index in range(arguments.count)]
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for index, result in enumerate(executor.map(generate_one, tasks, chunksize=20)):
            results.append(result)
            if index % 600 == 599:
                print(index + 1, round(time.time() - started, 2), flush=True)
    energies, orbitals, families = zip(*results)
    np.savez_compressed(Path(arguments.output), energies=energies, orbitals=orbitals, families=families)
    print('saved', arguments.output, time.time() - started, flush=True)


if __name__ == '__main__':
    main()
