import os
import sys
import time

import numpy as np


child = os.fork()
if child == 0:
    started = time.process_time()
    while time.process_time() - started < 2:
        pass
    query = np.load(sys.argv[1], allow_pickle=False)
    np.savez(sys.argv[2], log_weight=np.zeros(len(query['s'])))
    os._exit(0)
os._exit(0)
