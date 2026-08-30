import pickle
import sys
from pathlib import Path

import numpy as np


def main():
    data = np.load(sys.argv[1])
    with (Path(__file__).resolve().parent / "model.pkl").open("rb") as stream:
        model = pickle.load(stream)
    prediction = model.predict(np.log(np.maximum(data["s"], 1e-15)))
    np.savez(sys.argv[2], log_weight=prediction)


if __name__ == "__main__":
    main()
