import json
import sys

import numpy as np

sys.path.insert(0, "/participant/input")
from model import Model


def main():
    spec = json.loads(sys.stdin.readline())["spec"]
    model = Model(spec)
    model.fisher(model.bounds.mean(axis=1))
    print(json.dumps({"type": "final", "rates": np.exp(model.bounds.mean(axis=1)).tolist()}), flush=True)


if __name__ == "__main__":
    main()
