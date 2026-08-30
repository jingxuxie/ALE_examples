import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).with_name("predictions.npz"), arguments.output / "predictions.npz")


if __name__ == "__main__":
    main()
