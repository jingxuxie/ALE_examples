import argparse
import pickle
import shutil
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("training")
    parser.add_argument("output")
    arguments = parser.parse_args()
    data = np.load(arguments.training)
    inputs = np.log(np.maximum(data["s"], 1e-15))
    model = ExtraTreesRegressor(n_estimators=64, max_depth=22, min_samples_leaf=3,
                               max_features=1.0, n_jobs=1, random_state=914)
    model.fit(inputs, data["log_weight"])
    destination = Path(arguments.output)
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / "model.pkl").open("wb") as stream:
        pickle.dump(model, stream, protocol=4)
    source = Path(__file__).with_name("predict.py")
    target = destination / "predict.py"
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)


if __name__ == "__main__":
    main()
