import argparse
import json
from pathlib import Path

from test_solver import make_case
from solve import solve


def hard_case(family, length):
    case = make_case(family, length)
    if family == 'spinhalf_ladder':
        case['field'] = [0.] * length
        for bond in case['bonds']:
            first, last = bond['sites']
            exchange = 0.5 if first // 2 == last // 2 else 2.5
            bond['jxy'] = exchange
            bond['jz'] = exchange
    elif family == 'spin1_chain':
        case['single_ion'] = [0.] * length
        case['field'] = [0.] * length
        for bond in case['bonds']:
            bond['jxy'] = 1.
            bond['jz'] = 1.
    else:
        case['interaction'] = [4.] * length
        case['potential'] = [0.] * length
        for bond in case['bonds']:
            bond['hopping'] = 1.25
    return case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('family')
    parser.add_argument('length', type=int)
    parser.add_argument('--budget', type=float, default=560.)
    args = parser.parse_args()
    case = hard_case(args.family, args.length)
    directory = Path(__file__).resolve().parent
    stem = f'hard_{args.family}_{args.length}'
    (directory / (stem + '.json')).write_text(json.dumps(case))
    result = solve(case, args.budget, verbose=True)
    (directory / (stem + '.out.json')).write_text(json.dumps(result))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
