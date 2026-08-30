import json
import sys
from pathlib import Path


root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "input" if (root / "input").is_dir() else root.parent / "input"))

from estimation import fit, fixed_design
from simulator import parameter_dict


def main():
    history = []
    design = fixed_design()
    for line in sys.stdin:
        message = json.loads(line)
        if message["type"] == "observation":
            history.append(message)
        if len(history) < len(design):
            output = design[len(history)]
        else:
            output = {"type": "estimate", "parameters": parameter_dict(fit(history))}
        print(json.dumps(output, allow_nan=False), flush=True)
        if output["type"] == "estimate":
            return


if __name__ == "__main__":
    main()
