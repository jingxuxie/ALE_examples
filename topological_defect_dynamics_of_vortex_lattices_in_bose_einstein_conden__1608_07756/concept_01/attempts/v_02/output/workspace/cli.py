import json
import sys
from pathlib import Path

from experiment import run


if __name__ == '__main__':
    config = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else json.loads((Path(__file__).resolve().parent.parent / 'config.json').read_text())
    run(sys.argv[1], sys.argv[2], config)
