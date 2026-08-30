from pathlib import Path
import sys


def main():
    source = Path(__file__).resolve().with_name("model.json")
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True,exist_ok=True)
    (destination/"model.json").write_bytes(source.read_bytes())


if __name__ == "__main__":
    main()
