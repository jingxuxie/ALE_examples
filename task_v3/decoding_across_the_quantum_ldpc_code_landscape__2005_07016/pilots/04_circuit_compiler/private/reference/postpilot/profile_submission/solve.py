import time

started = time.process_time()
import argparse
import gc
import json
import sys
import candidate

loaded = time.process_time()
parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
arguments = parser.parse_args()
gc.disable()
with open(arguments.input, encoding="utf-8") as source:
    case = json.load(source)
parsed = time.process_time()
instructions = candidate.prepare_operations(case.pop("operations"))
prepared = time.process_time()
terms = candidate.compile_terms(case, instructions)
compiled = time.process_time()
del instructions
with open(arguments.output, "w", encoding="utf-8") as destination:
    candidate.write_answer(destination, case, terms)
finished = time.process_time()
print(json.dumps({"profile": {"import_cpu": loaded - started,
    "argparse_and_input_cpu": parsed - loaded, "prepare_cpu": prepared - parsed,
    "compile_cpu": compiled - prepared, "output_cpu": finished - compiled,
    "inside_script_cpu": finished - started}}), file=sys.stderr)
