import argparse
import json
from pathlib import Path
from model import diagnose


parser = argparse.ArgumentParser()
parser.add_argument('witness')
parser.add_argument('--size', type=int, default=33)
options = parser.parse_args()
payload = json.loads(Path(options.witness).read_text())
print(json.dumps(diagnose(payload['parameters'], options.size), indent=2, allow_nan=False))
