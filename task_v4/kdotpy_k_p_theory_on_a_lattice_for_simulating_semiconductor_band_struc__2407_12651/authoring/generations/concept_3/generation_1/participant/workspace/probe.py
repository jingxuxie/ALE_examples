import argparse
import json

from model import read_witness, sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness")
    parser.add_argument("--mesh", type=int, default=81)
    parser.add_argument("--uncertainty-points", type=int, default=3)
    arguments = parser.parse_args()
    print(json.dumps(sample(read_witness(arguments.witness), arguments.mesh, arguments.uncertainty_points), indent=2))


if __name__ == "__main__":
    main()
