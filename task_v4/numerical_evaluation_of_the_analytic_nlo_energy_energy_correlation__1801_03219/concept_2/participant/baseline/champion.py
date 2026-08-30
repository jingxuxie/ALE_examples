from pathlib import Path
import sys


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True,exist_ok=True)
    (output/"witness.json").write_bytes(Path(__file__).with_name("witness.json").read_bytes())


if __name__ == "__main__":
    main()
