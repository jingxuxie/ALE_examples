import json
import sys
from pathlib import Path

from experiment import run


if __name__ == '__main__':
    config = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else {'dt': 0.002}
    run(sys.argv[1], sys.argv[2], config)
