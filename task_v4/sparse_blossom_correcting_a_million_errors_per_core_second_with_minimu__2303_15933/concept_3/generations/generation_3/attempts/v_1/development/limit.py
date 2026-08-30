import os
import resource
import sys

resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
os.execv('/usr/bin/python3', ['/usr/bin/python3'] + sys.argv[1:])
