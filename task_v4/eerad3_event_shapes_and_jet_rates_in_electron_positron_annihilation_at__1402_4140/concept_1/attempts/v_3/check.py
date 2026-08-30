import argparse
import ctypes
import os
import time
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('data', nargs='?', default=os.environ.get('DATA'))
    arguments = parser.parse_args()
    if not arguments.data:
        parser.error('Provide the labelled input directory or set DATA')
    library = ctypes.CDLL(str(Path(__file__).resolve().with_name('kernel.so')))
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
    library.predict.argtypes = [ctypes.c_size_t, pointer, ctypes.c_void_p, pointer, ctypes.c_int]
    library.predict.restype = None
    for name in ['validation', 'train', 'frame_validation']:
        with np.load(Path(arguments.data) / (name + '.npz')) as data:
            invariants = np.ascontiguousarray(data['s'])
            labels = data['log_weight']
            families = data['family']
            frames = data['frame'] if 'frame' in data else np.zeros(len(labels), dtype=int)
        output = np.empty(len(invariants), dtype=np.float64)
        start = time.process_time()
        library.predict(len(output), invariants, None, output, 0)
        elapsed = time.process_time() - start
        error = output - labels
        rmse = np.mean(error**2)**0.5
        coverage = np.mean(np.abs(np.expm1(error)) <= 1e-8)
        print(f'{name}: count={len(output)} kernel_cpu={elapsed:.4f}s '
              f'log_rmse={rmse:.6g} max_log_error={np.max(abs(error)):.6g} '
              f'relative_coverage={coverage:.6f}')
        assert np.isfinite(output).all()
        assert rmse <= 1e-9 and coverage >= 0.99
        for family in np.unique(families):
            for frame in np.unique(frames):
                group = error[(families == family) & (frames == frame)]
                group_rmse = np.mean(group**2)**0.5
                print(f'  phase={family} frame={frame} log_rmse={group_rmse:.6g}')
                assert group_rmse <= 5e-9


if __name__ == '__main__':
    main()
