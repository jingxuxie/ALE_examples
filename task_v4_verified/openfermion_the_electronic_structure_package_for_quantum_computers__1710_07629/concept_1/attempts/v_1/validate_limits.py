import json
import os
import resource
import runpy
import sys
import time
from pathlib import Path

request_path, response_path, report_path = sys.argv[1:]
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
resource.setrlimit(resource.RLIMIT_CPU, (175, 175))
if hasattr(os, 'sched_setaffinity'):
    available = os.sched_getaffinity(0)
    os.sched_setaffinity(0, {min(available)})
started = time.monotonic()
cpu_started = time.process_time()
sys.argv = [str(Path(__file__).with_name('solver.py')), request_path, response_path]
runpy.run_path(sys.argv[0], run_name='__main__')
report = {'wall_seconds': time.monotonic() - started, 'cpu_seconds': time.process_time() - cpu_started,
          'maximum_resident_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
try:
    report['threads'] = len(os.listdir('/proc/self/task'))
except OSError:
    pass
Path(report_path).write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
