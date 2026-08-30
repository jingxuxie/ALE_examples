import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
options = parser.parse_args()
parameters = [-1.0, 1., 1., 1., 1., -.3, -.1, .1, .3,
              .05, -.05, .05, -.05, .16, .16, .16, .16,
              .16, .16, .16, .16, .2, 1.1, -1.4, 2.2]
Path(options.output).write_text(json.dumps({'parameters': parameters}, indent=2))
