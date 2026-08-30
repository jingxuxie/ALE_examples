import argparse
import json
from pathlib import Path


def synthesize(instance):
    width = instance["n"]
    coefficients = instance["table"].copy()
    for bit in range(width):
        for mask in range(1 << width):
            if mask & (1 << bit):
                coefficients[mask] ^= coefficients[mask ^ (1 << bit)]
    gates = []
    references = {0: 0, **{1 << bit: 1 + bit for bit in range(width)}}
    def product(mask):
        if mask in references:
            return references[mask]
        low = mask & -mask
        left, right = product(mask ^ low), product(low)
        reference = width + 1 + len(gates)
        gates.append({"left": [left], "right": [right]})
        references[mask] = reference
        return reference
    outputs = [[] for _ in range(instance["m"])]
    for mask, coefficient in enumerate(coefficients):
        if coefficient:
            reference = product(mask)
            for bit, expression in enumerate(outputs):
                if coefficient & (1 << bit):
                    expression.append(reference)
    return {"id": instance["id"], "gates": gates, "outputs": [sorted(expression) for expression in outputs]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    suite = json.loads((args.input / "suite.json").read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"circuits": [synthesize(instance) for instance in suite["instances"]]}))


if __name__ == "__main__":
    main()
