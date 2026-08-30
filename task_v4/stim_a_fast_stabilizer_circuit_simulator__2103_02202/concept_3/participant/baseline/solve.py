import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description="Write the supplied exact, over-budget baseline artifact.")
    parser.add_argument("--output", default=".", help="Output directory, or explicit circuit.json path; default: current directory")
    arguments = parser.parse_args()
    output = Path(arguments.output)
    if output.name != "circuit.json":
        output = output / "circuit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().with_name("circuit.json")
    if output.resolve() != source:
        shutil.copyfile(source, output)
    print(str(output))


if __name__ == "__main__":
    main()
