import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser(description="Emit the identity local-Clifford construction.")
parser.add_argument("--output", type=Path)
arguments = parser.parse_args()
artifact = json.dumps({"z_image": [2] * 24}, indent=2) + "\n"
if arguments.output is None:
    print(artifact, end="")
else:
    arguments.output.write_text(artifact)
