import importlib.util
import json
import os
import sys
import time

assets = os.environ['ASSETS']
sys.path.insert(0, assets + '/workspace')
from phase_model import check
import solution

spec = importlib.util.spec_from_file_location('baseline', assets + '/baseline/solution.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
cases = [json.loads(line) for line in open(assets + '/input/examples.jsonl') if line.strip()]
for index, instance in enumerate(cases):
    started = time.monotonic()
    base = check(instance, baseline.compile_circuit(instance))
    base_time = time.monotonic() - started
    started = time.monotonic()
    response = solution.compile_circuit(instance)
    result = check(instance, response)
    print(index, 'baseline', base, 'base_time', round(base_time, 3), 'ours', result, 'time', round(time.monotonic() - started, 3), 'reduction', round(1-result['cost']/base['cost'], 4), flush=True)
