import argparse
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("concept")
parser.add_argument("generation", type=int)
parser.add_argument("submission", type=Path)
parser.add_argument("--output", type=Path)
arguments = parser.parse_args()
generation = ROOT / arguments.concept / "generations" / f"generation_{arguments.generation}"
sys.path.insert(0, str(generation / "evaluator"))
specification = importlib.util.spec_from_file_location("generation_evaluator", generation / "evaluator/evaluate.py")
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)
evaluator.SANDBOX = ROOT / "authoring/sandbox.py"
result = evaluator.evaluate(arguments.submission)
text = json.dumps(result, indent=2, allow_nan=False) + "\n"
if arguments.output:
    arguments.output.write_text(text)
print(text, end="")
