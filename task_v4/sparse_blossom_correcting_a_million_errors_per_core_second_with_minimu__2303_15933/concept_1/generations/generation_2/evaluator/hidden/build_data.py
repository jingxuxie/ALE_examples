import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PARTICIPANT = ROOT / "participant"
sys.dont_write_bytecode = True
sys.path[:0] = [str(PARTICIPANT / "input/runtime"), str(PARTICIPANT / "input"), str(PARTICIPANT)]
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pymatching
import stim
from baseline.submission import Decoder
from models import SPECS, make_model, sample_model, save_model


def main():
    hidden = ROOT / "evaluator/hidden"
    if (hidden / "seeds.json").exists() or (hidden / "frozen.json").exists():
        raise RuntimeError("Independent fixed draws already exist; no resampling")
    splits = dict(calibration=256, challenge=256, holdout=256)
    seeds = {spec["case_id"]: {split: secrets.randbits(128) for split in splits} for spec in SPECS}
    flattened = [seed for values in seeds.values() for seed in values.values()]
    if len(flattened) != len(set(flattened)):
        raise RuntimeError("Seed collision")
    (hidden / "seeds.json").write_text(json.dumps(seeds, indent=2) + "\n")
    reports = []
    for spec in SPECS:
        model = make_model(spec)
        case_id = spec["case_id"]
        save_model(model, PARTICIPANT / "input/cases" / case_id)
        matching = pymatching.Matching.from_detector_error_model(stim.DetectorErrorModel(model["dem_text"]), enable_correlations=True)
        for split, shots in splits.items():
            syndromes, labels, faults = sample_model(model, shots, seeds[case_id][split])
            started = time.process_time()
            predictions = Decoder(model).decode(syndromes)
            elapsed = time.process_time() - started
            if predictions.shape != (shots, 4) or not np.isin(predictions, [0, 1]).all():
                raise ValueError("Invalid promoted baseline output")
            two_pass = matching.decode_batch(syndromes, enable_correlations=True)
            directory = PARTICIPANT / "input/calibration" if split == "calibration" else hidden / split
            directory.mkdir(parents=True, exist_ok=True)
            destination = directory / (case_id + ".npz")
            np.savez_compressed(destination, syndromes=syndromes, labels=labels, baseline=predictions)
            reports.append(dict(case_id=case_id, family=spec["family"], split=split, shots=shots,
                baseline_failures=int(np.any(predictions != labels, axis=1).sum()),
                correlated_matching_failures=int(np.any(two_pass != labels, axis=1).sum()),
                decode_cpu_seconds=elapsed, mean_faults=float(faults.sum(axis=1).mean()),
                sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
            (hidden / "sampling_report.json").write_text(json.dumps(dict(complete=False, cases=reports), indent=2) + "\n")
            print(json.dumps(reports[-1]), flush=True)
    (hidden / "sampling_report.json").write_text(json.dumps(dict(complete=True, cases=reports,
        sampling="Independent unconditional Bernoulli faults; syndrome H e mod 2; logical label L e mod 2; no rejection or balancing",
        seeds_committed_before_decoding=True, pymatching=pymatching.__version__, stim=stim.__version__), indent=2) + "\n")


if __name__ == "__main__":
    main()
