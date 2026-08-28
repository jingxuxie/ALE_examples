import json
import os
from pathlib import Path
import socket
import sys
import numpy as np
import scipy
import numba

case = json.load(open(sys.argv[1]))
result = dict(numpy=np.__version__, scipy=scipy.__version__, numba=numba.__version__,
    forbidden_visible={path: Path(path).exists() for path in case['forbidden']},
    credentials_visible=any(key in os.environ for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']))
try:
    connection = socket.create_connection(('1.1.1.1', 443), timeout=1)
    connection.close()
    result['network_connected'] = True
except OSError:
    result['network_connected'] = False
Path(sys.argv[2]).write_text(json.dumps(result, indent=2))
