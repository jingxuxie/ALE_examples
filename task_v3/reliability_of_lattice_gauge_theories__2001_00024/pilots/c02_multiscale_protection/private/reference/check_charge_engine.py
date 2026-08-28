import argparse
import json
import pathlib

from charge_engine import np, predict

BASE = pathlib.Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("identifier")
    parser.add_argument("--split", default="screening")
    parser.add_argument("--bond", type=int, default=128)
    parser.add_argument("--step", type=float, default=0.0125)
    arguments = parser.parse_args()
    record = json.loads((BASE / "private" / "challenge_pool" / arguments.split / (arguments.identifier + ".json")).read_text())
    case = record["case"]
    result, metadata = predict(case["experiment"], record["true_parameters"], case["times"], case["pairs"],
                               bond=arguments.bond, step=arguments.step)
    differences = {name: {"maximum": float(np.max(abs(np.array(result[name]) - record["reference"][name]))),
                          "rmse": float(np.sqrt(np.mean((np.array(result[name]) - record["reference"][name])**2)))}
                   for name in ["density", "violation", "correlation"]}
    output = {"id": record["id"], "metadata": metadata, "differences_vs_quimb": differences, "prediction": result}
    directory = BASE / "private" / "reference" / "charge_checks"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (record["id"] + ".json")).write_text(json.dumps(output, indent=2))
    print(json.dumps({key: value for key, value in output.items() if key != "prediction"}), flush=True)


if __name__ == "__main__":
    main()
