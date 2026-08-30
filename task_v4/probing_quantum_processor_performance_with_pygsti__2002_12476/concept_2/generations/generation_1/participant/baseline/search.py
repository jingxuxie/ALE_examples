import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / "witness.json"
    Path(args.output).write_bytes(source.read_bytes())


if __name__ == "__main__":
    main()
