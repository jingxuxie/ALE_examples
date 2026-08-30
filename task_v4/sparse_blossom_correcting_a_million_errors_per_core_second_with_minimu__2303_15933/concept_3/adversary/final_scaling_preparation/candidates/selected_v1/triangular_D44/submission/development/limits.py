import os
import resource
import sys

resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
os.execv(sys.executable, [sys.executable] + sys.argv[1:])
