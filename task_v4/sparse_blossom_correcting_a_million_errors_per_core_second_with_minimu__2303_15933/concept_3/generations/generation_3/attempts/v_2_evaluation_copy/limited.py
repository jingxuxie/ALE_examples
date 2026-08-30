import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import resource
import sys
import time
resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
resource.setrlimit(resource.RLIMIT_CPU, (59, 60))
import solution
if '--portable' in sys.argv:
    import ctypes
    from pathlib import Path
    portable = ctypes.CDLL(str(Path(solution.__file__).parent / 'kernel.so'))
    for name in ('evaluate', 'distribution', 'joint_evaluate'):
        getattr(portable, name).argtypes = getattr(solution.LIB, name).argtypes
        getattr(portable, name).restype = getattr(solution.LIB, name).restype
    solution.LIB = portable
solution.main()
print('measured_cpu', time.process_time(), 'rss_kib', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      file=sys.stderr, flush=True)
