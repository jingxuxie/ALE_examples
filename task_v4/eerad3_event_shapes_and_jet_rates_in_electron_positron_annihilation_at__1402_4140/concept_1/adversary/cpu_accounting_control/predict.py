import sys
import time

import numpy as np


def main():
    started = time.process_time()
    while time.process_time() - started < 2.0:
        sum(value * value for value in range(1000))
    data = np.load(sys.argv[1])
    np.savez(sys.argv[2], log_weight=np.full(len(data['s']), 20.0))


if __name__ == '__main__':
    main()
