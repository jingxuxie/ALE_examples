import os
import sys
import time
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import importlib
from contractor import measure, save_mps

module, request_path, output = sys.argv[1:4]
request = json.load(open(request_path))
optimizer = importlib.import_module(module)
state = optimizer.optimize(request, 0.0, time.monotonic())
save_mps(output, state)
print('RESULT', time.process_time(), json.dumps(measure(state, request)), flush=True)
