import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    destination = Path(arguments.output)
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).with_name("state.npz"), destination / "state.npz")


if __name__ == "__main__":
    main()
