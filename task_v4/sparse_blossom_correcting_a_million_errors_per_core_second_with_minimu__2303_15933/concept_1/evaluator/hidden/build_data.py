import hashlib
import json
import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARTICIPANT = ROOT / "participant"
sys.path[:0] = [str(PARTICIPANT / "input/runtime"), str(PARTICIPANT / "input"), str(PARTICIPANT)]

import numpy as np
import pymatching
import stim

from baseline.decoder import Decoder
from models import SPECS, make_model, sample_model, save_model


def main():
    if (ROOT / "evaluator/hidden/frozen.json").exists():
        raise RuntimeError("Refusing to regenerate a frozen challenge")
    seed_records = {}
    inventory = []
    baseline_reports = []
    for spec in SPECS:
        model = make_model(spec)
        case_id = spec["case_id"]
        save_model(model, PARTICIPANT / "input/cases" / case_id)
        matcher = Decoder(model)
        plain = pymatching.Matching.from_detector_error_model(stim.DetectorErrorModel(model["dem_text"]))
        seed_records[case_id] = {}
        for split, shots in [("calibration", 512), ("pilot", 128), ("challenge", 1024), ("holdout", 1024)]:
            seed = secrets.randbits(128)
            seed_records[case_id][split] = str(seed)
            syndromes, labels, faults = sample_model(model, shots, seed)
            started = time.perf_counter()
            predictions = matcher.decode(syndromes)
            elapsed = time.perf_counter() - started
            uncorrelated = plain.decode_batch(syndromes)
            if split == "calibration":
                destination = PARTICIPANT / "input/calibration" / (case_id + ".npz")
            else:
                destination = ROOT / "evaluator/hidden" / split / (case_id + ".npz")
            destination.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(destination, syndromes=syndromes, labels=labels, baseline=predictions)
            baseline_reports.append(dict(case_id=case_id, family=spec["family"], split=split, shots=shots,
                                         failures=int(np.any(predictions != labels, axis=1).sum()),
                                         uncorrelated_failures=int(np.any(uncorrelated != labels, axis=1).sum()),
                                         decode_seconds=elapsed))
            if split != "calibration":
                inventory.append(dict(path=str(destination.relative_to(ROOT)), sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
        inventory.append(dict(path=str((PARTICIPANT / "input/cases" / case_id / "model.dem").relative_to(ROOT)),
                              sha256=hashlib.sha256(model["dem_text"].encode()).hexdigest(),
                              detectors=model["num_detectors"], mechanisms=model["num_mechanisms"]))
        print(case_id, model["num_detectors"], model["num_mechanisms"], baseline_reports[-2:], flush=True)
    (ROOT / "evaluator/hidden/seeds.json").write_text(json.dumps(seed_records, indent=2) + "\n")
    (ROOT / "evaluator/hidden/inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    (ROOT / "attempts/baseline_sampling.json").write_text(json.dumps(dict(pymatching=pymatching.__version__, stim=stim.__version__, cases=baseline_reports), indent=2) + "\n")


if __name__ == "__main__":
    main()
