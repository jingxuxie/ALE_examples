import argparse
import json
from pathlib import Path

from checker import evaluate

parser = argparse.ArgumentParser()
parser.add_argument("--submission", type=Path, required=True)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
result = evaluate(args.submission)
text = json.dumps(result, indent=2)
if args.report:
    args.report.write_text(text + "\n")
print(text)
