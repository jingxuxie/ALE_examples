import argparse
import json
from pathlib import Path

import numpy as np


def compute(job, data_file):
    data = np.loadtxt(data_file, ndmin=2)
    boundaries = np.flatnonzero(np.r_[True, data[1:, 0] != data[:-1, 0], True])
    events = [data[boundaries[index]:boundaries[index + 1], 1:] for index in range(len(boundaries) - 1)]
    histograms = []
    for query in job["queries"]:
        shape = [query["bins"]]
        contact_cell = 0
        if job["kind"] == "resolved":
            shape += [query["ratio_bins"], query["phi_bins"]]
            if query["order"] == 4:
                shape += [query["ratio_bins"], query["phi_bins"]]
            else:
                contact_cell = query["phi_bins"] // 2
        histogram = np.zeros(int(np.prod(shape)))
        for event in events:
            fractions = event[:, 0] / event[:, 0].sum()
            if job["kind"] == "weighted":
                power = query["kappa"] * query["order"]
            elif job["kind"] == "fractional":
                power = query["nu"]
            elif job["kind"] == "resolved" and query["order"] == 3:
                power = 3
            else:
                continue
            histogram[contact_cell] += float(np.sum(fractions**power)) / len(events)
        histograms.append(histogram.tolist())
    return {"histograms": histograms, "claims": {"method": "original-constituent contacts only", "limitations": "No noncontact correlations or subjets are evaluated."}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    job = json.loads(arguments.input.read_text())
    arguments.output.write_text(json.dumps(compute(job, arguments.input.parent / job["events_file"])))


if __name__ == "__main__":
    main()
