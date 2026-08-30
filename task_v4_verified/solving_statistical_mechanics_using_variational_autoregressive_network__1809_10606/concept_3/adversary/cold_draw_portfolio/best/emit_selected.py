import argparse
import json
from pathlib import Path
import sys
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    sys.path.insert(0, str(arguments.assets.resolve()))
    from transfer import model_from_edges
    specification = json.loads((arguments.assets / "input/model.json").read_text())
    queries = json.loads((arguments.assets / "input/queries.json").read_text())
    with np.load(Path(__file__).with_name("parameters.npz"), allow_pickle=False) as archive:
        signs = np.asarray(specification["edge_signs"])
        posterior = model_from_edges(specification, archive["posterior_magnitudes"] * signs, archive["posterior_fields"])
        anchor = model_from_edges(specification, archive["anchor_magnitudes"] * signs, archive["anchor_fields"])
        weight = float(archive["weight"])
    predictions = []
    for query in queries:
        delta = np.zeros_like(posterior.fields)
        delta.flat[query["field_indices"]] = query["field_values"]
        prediction = weight * posterior.joint(query["beta"], query["readout"], delta)
        prediction += (1 - weight) * anchor.joint(query["beta"], query["readout"], delta)
        predictions.append(prediction / prediction.sum())
    arguments.output.mkdir(parents=True, exist_ok=True)
    np.savez(arguments.output / "predictions.npz", probabilities=np.ascontiguousarray(predictions, dtype="<f8"),
             query_ids=np.asarray([query["id"] for query in queries], dtype="<U24"))


if __name__ == "__main__":
    main()
