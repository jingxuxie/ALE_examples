import argparse
import json
from pathlib import Path

from test_solver import make_case
from solve import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('family')
    parser.add_argument('length', type=int)
    parser.add_argument('--seed', type=int, default=317)
    parser.add_argument('--budget', type=float, default=560.)
    args = parser.parse_args()
    case = make_case(args.family, args.length, args.seed)
    stem = f'{args.family}_{args.length}_{args.seed}'
    directory = Path(__file__).resolve().parent
    (directory / (stem + '.json')).write_text(json.dumps(case))
    result = solve(case, args.budget, verbose=True)
    (directory / (stem + '.out.json')).write_text(json.dumps(result))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
