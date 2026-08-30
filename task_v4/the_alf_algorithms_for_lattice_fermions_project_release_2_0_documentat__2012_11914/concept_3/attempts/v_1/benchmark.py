import json
import os
import resource
import runpy
import sys
import time

os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
sys.argv = ['solve.py', sys.argv[1], sys.argv[2]]
started = time.monotonic()
runpy.run_path('solve.py', run_name='__main__')
print(json.dumps({'elapsed_seconds': time.monotonic() - started, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
