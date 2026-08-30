import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
arguments = parser.parse_args()
model = json.loads(Path(arguments.input).read_text())
with Path("columns.txt").open("w") as stream:
    for column, observable in zip(model["columns"], model["observable"]):
        value = int(column, 16)
        words = [(value >> shift) & ((1 << 64) - 1) for shift in (0, 64, 128)]
        stream.write(" ".join(format(word, "016x") for word in words) + " " + str(observable) + "\n")
subprocess.run([str(Path(__file__).with_name("search")), "1", "60", "928331"], check=False)
answer = json.loads(Path("witness.json").read_text())
Path(arguments.output).write_text(json.dumps(answer) + "\n")
