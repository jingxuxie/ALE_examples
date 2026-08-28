import os
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import numpy as np

from test_solver import make_case
from dmrg import Effective, correlations, make_model, run_dmrg
from eigensolver import davidson


def main():
    original = Effective.optimize_arpack
    for family in ['bose_hubbard', 'spin1_chain', 'spinhalf_ladder']:
        case = make_case(family, 32)
        model = make_model(case)
        sector = case.get('particles', 0)
        outputs = []
        for method in ['arpack', 'davidson']:
            if method == 'davidson':
                Effective.optimize = lambda effective, initial, tolerance: davidson(
                    effective, initial, tolerance, original)
            else:
                Effective.optimize = original
            start = time.monotonic()
            energy, state, history = run_dmrg(model, sector, [16, 32, 64, 96, 128], start + 1000)
            measured = correlations(case, model, state)
            outputs.append((energy, measured))
            print(family, method, time.monotonic() - start, energy, flush=True)
        print('differences', outputs[1][0] - outputs[0][0],
              np.max(np.abs(np.array(outputs[1][1]) - outputs[0][1])), flush=True)
    Effective.optimize = original


if __name__ == '__main__':
    main()
