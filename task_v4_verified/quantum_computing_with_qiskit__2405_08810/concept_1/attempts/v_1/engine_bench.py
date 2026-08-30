import importlib.util
import json
import os
import subprocess
import sys
import time

assets = os.environ['ASSETS']
sys.path.insert(0, assets + '/workspace')
from phase_model import check

spec = importlib.util.spec_from_file_location('baseline', assets + '/baseline/solution.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
cases = [json.loads(line) for line in open(assets + '/input/examples.jsonl') if line.strip()]
for index, instance in enumerate(cases):
    base = check(instance, baseline.compile_circuit(instance))
    data = [instance['n'], len(instance['edges']), len(instance['terms'])]
    data.extend(value for edge in instance['edges'] for value in edge)
    data.extend(instance['terms'])
    started = time.monotonic()
    process = subprocess.run(['./engine', *sys.argv[1:]], input=' '.join(map(str, data)), text=True, capture_output=True, check=True)
    response = json.loads(process.stdout)
    result = check(instance, response)
    print(index, 'base', base['cost'], 'ours', result, 'reduction', round(1-result['cost']/base['cost'], 4), 'wall', round(time.monotonic()-started, 3), process.stderr.strip(), flush=True)
