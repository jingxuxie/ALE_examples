import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=root.parent / "input/model.json")
    parser.add_argument("--output", type=Path, default=Path("witness.json"))
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--threads", type=int, default=1)
    arguments = parser.parse_args()
    if arguments.seconds <= 0:
        arguments.output.write_bytes((root / "witness.json").read_bytes())
        return
    model = json.loads(arguments.input.read_text())
    with tempfile.TemporaryDirectory(prefix="champion_search_") as temporary:
        directory = Path(temporary)
        with (directory / "columns.txt").open("w") as stream:
            for column, observable in zip(model["columns"], model["observable"]):
                value = int(column, 16)
                words = [(value >> shift) & ((1 << 64) - 1) for shift in (0, 64, 128)]
                stream.write(" ".join(format(word, "016x") for word in words) + " " + str(observable) + "\n")
        subprocess.run([str(root / "search"), str(arguments.threads), str(arguments.seconds), "928331"], cwd=directory, check=False)
        arguments.output.write_bytes((directory / "witness.json").read_bytes())


if __name__ == "__main__":
    main()
