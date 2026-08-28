import argparse
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
from validate import make_case


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (58, 58))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cold', action='store_true')
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    with np.load(directory.parent / 'participant/input/codes/lp882.npz', allow_pickle=False) as code:
        case, _, _ = make_case(code['base_hx'], code['base_hz'], 256, .14, 100, 'x', 801234)
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        isolated = Path(temporary)
        for name in ('solve.py', 'decoder.cpp'):
            shutil.copy2(directory / name, isolated / name)
        if not args.cold:
            shutil.copy2(directory / 'decoder.so', isolated / 'decoder.so')
        np.savez_compressed(isolated / 'case.npz', **case)
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.monotonic()
        environment = os.environ.copy()
        environment['DECODER_STATS'] = '1'
        environment.pop('DECODER_MODE', None)
        subprocess.run([sys.executable, 'solve.py', '--input', str(isolated / 'case.npz'),
                        '--output', str(isolated / 'answer.data')], cwd=isolated,
                       check=True, timeout=180, preexec_fn=limits, env=environment)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        print('CPU seconds: %.3f; wall seconds: %.3f; peak RSS KiB: %d; cold: %s' %
              (cpu, time.monotonic() - start, after.ru_maxrss, args.cold), flush=True)
        assert cpu < 60
        with np.load(isolated / 'answer.data', allow_pickle=False) as answer:
            assert set(answer.files) == {'correction_x', 'correction_z'}
            for key in answer.files:
                assert answer[key].shape == (256, 882)
                assert answer[key].dtype.kind in 'biu'
                assert np.all(answer[key] <= 1)
            actual = (answer['correction_x'] @ case['gz'].T + answer['correction_z'] @ case['gx'].T) & 1
            assert np.array_equal(actual, case['syndrome'])
        print('Resource-limited standalone CLI test passed.', flush=True)


if __name__ == '__main__':
    main()
