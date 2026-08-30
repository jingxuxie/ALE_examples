import argparse
import json

from model import evaluate, load_artifact


parser = argparse.ArgumentParser()
parser.add_argument('artifact')
arguments = parser.parse_args()
try:
    result = evaluate(load_artifact(arguments.artifact))
except (ValueError, OSError) as error:
    result = {'passed': False, 'valid': False, 'reason': str(error), 'core_score': 0.0}
print(json.dumps(result, indent=2))
