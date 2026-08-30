import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'

import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent.parent / 'participant' / 'input'


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def run(input_path, output_path):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter()
    subprocess.run([sys.executable, str(HERE / 'predict.py'), str(input_path), str(output_path)], check=True, preexec_fn=limits)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
    print(input_path.name, 'CPU', cpu, 'wall', time.perf_counter()-start, flush=True)
    with np.load(output_path) as result:
        assert result.files == ['log_weight']
        prediction = result['log_weight']
    assert prediction.dtype == np.float64 and np.all(np.isfinite(prediction))
    return prediction, cpu


for name in ['train', 'validation', 'frame_validation']:
    prediction, cpu = run(DATA / (name + '.npz'), HERE / '_predictions.npz')
    with np.load(DATA / (name + '.npz')) as data:
        error = prediction - data['log_weight']
        family = data['family']
        frame = data['frame'] if 'frame' in data else np.zeros(len(error), dtype=int)
    worst = 0
    for phase in np.unique(family):
        for frame_id in np.unique(frame):
            part = error[(family == phase) & (frame == frame_id)]
            rmse = np.sqrt(np.mean(part**2))
            worst = max(worst, rmse)
            if name == 'frame_validation':
                print('group', phase, frame_id, 'RMSE', rmse)
    rmse = np.sqrt(np.mean(error**2))
    coverage = np.mean(np.abs(np.expm1(error)) <= 1e-8)
    print('RMSE', rmse, 'worst group', worst, 'coverage', coverage, flush=True)
    assert rmse <= 1e-9 and worst <= 5e-9 and coverage >= .99

with np.load(HERE / '_stress.npz') as data:
    selected = np.concatenate([np.flatnonzero(data['family'] == family)[:40000] for family in range(5)])
    np.savez_compressed(HERE / '_benchmark.npz', s=data['s'][selected], p=data['p'][selected], family=data['family'][selected])
for repeat in range(3):
    prediction, cpu = run(HERE / '_benchmark.npz', HERE / '_predictions.npz')
    assert prediction.shape == (200000,)
    assert cpu <= 2.4
for name in ['_predictions.npz', '_benchmark.npz']:
    (HERE / name).unlink()
