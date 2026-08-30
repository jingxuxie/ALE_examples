import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser(description="Emit the supplied champion local-Clifford construction.")
parser.add_argument("--output", type=Path)
arguments = parser.parse_args()
artifact = Path(__file__).with_name("design.json").read_text()
if arguments.output is None:
    print(artifact, end="")
else:
    arguments.output.write_text(artifact)
