import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from experiment import read, report, ROOT
from features import feature_matrix, particle_features, cluster_features, transport_features, describe_batch
from predict import load_model, estimate

cases = read('simulated.jsonl')[:320]
started = time.monotonic()
features = feature_matrix(cases)
print('fresh simulated', len(cases), 'seconds', time.monotonic() - started, flush=True)
report(cases, estimate(features, load_model()), 'fresh_simulations')
np.savez('simulation_validation_features.npz', features=features, count=len(cases))
cases = read(ROOT / 'validation.jsonl') * 2
values = np.array([case['fields'] for case in cases])
values -= values.mean(axis=1, keepdims=True)
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
for name, method in [('base', describe_batch), ('transport', transport_features), ('particle', particle_features), ('cluster', cluster_features)]:
    started, cpu = time.monotonic(), time.process_time()
    method(values)
    print(name, 'serial', time.monotonic() - started, time.process_time() - cpu, flush=True)
    started, cpu = time.monotonic(), time.process_time()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(method, np.array_split(values, 4)))
    print(name, 'parallel', time.monotonic() - started, time.process_time() - cpu, flush=True)
