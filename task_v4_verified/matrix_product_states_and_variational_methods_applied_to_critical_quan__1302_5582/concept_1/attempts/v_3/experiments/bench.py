import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import time
import importlib
from contractor import measure, save_mps

module = importlib.import_module(sys.argv[1])
for filename in sys.argv[3:]:
    request = json.load(open(filename))
    request['budget_seconds'] = float(sys.argv[2])
    request['wall_seconds'] = max(120., 3 * request['budget_seconds'])
    start = time.process_time()
    tensors = module.optimize(request)
    elapsed = time.process_time() - start
    result = measure(tensors, request)
    print(filename, elapsed, result, flush=True)
    save_mps(filename[:-5] + '_' + sys.argv[1] + '_' + sys.argv[2] + '.npz', tensors)
