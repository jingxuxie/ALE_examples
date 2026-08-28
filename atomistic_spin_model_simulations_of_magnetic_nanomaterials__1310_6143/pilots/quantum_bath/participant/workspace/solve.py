import json
import sys
import numpy as np
from common import initialize, classical_integrate


def main():
    case = json.load(open(sys.argv[1]))
    spins, material, neighbors, parameters = initialize(case)
    spins, trace = classical_integrate(spins, material, neighbors, parameters,
        np.array(case['exchange']), np.array(case['field']), case['dt'], case['steps'],
        np.array(case['sample_steps']))
    np.savez(sys.argv[2], spins=spins, trace=trace, memory=np.zeros((len(spins), 6)),
             covariance=np.zeros((len(parameters), len(case['lags']))))


if __name__ == '__main__':
    main()
