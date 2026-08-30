from pathlib import Path
import resource
import runpy

resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
runpy.run_path(str(Path(__file__).with_name('policy.py')), run_name='__main__')
