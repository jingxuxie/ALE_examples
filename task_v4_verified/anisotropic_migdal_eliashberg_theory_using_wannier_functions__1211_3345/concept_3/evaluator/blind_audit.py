"""Blind expensive inference on an independent private audit split."""

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "champions" / "portfolio"))
from inference import dictionary, infer
from evaluate import score, target_configuration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--starts", type=int, default=2)
    arguments = parser.parse_args()
    configuration, target_hash = target_configuration()
    with np.load(ROOT / "evaluator" / "hidden" / "audit_features.npz", allow_pickle=False) as archive:
        observed, sigma = archive["observed"][:arguments.count], archive["sigma"][:arguments.count]
        sheet_count = archive["sheet_count"][:arguments.count]
    bank = dictionary()
    predictions, details = [], []
    started = time.process_time()
    for index in range(len(observed)):
        prediction, diagnostic, fits = infer(observed[index], sigma[index], bank, starts=arguments.starts, sheet_count=int(sheet_count[index]))
        predictions.append(prediction)
        details.append(diagnostic)
        print(index, diagnostic["best_family"], diagnostic["best_chi_square"], time.process_time() - started, flush=True)
        np.savez_compressed(ROOT / "evaluator" / "hidden" / "blind_audit_prediction.npz", spectral_mass=np.asarray(predictions))
    with np.load(ROOT / "evaluator" / "hidden" / "audit_labels.npz", allow_pickle=False) as archive:
        labels, families = archive["spectral_mass"][:len(predictions)], archive["family"][:len(predictions)]
    report = dict(target_sha256=target_hash, score=score(np.asarray(predictions), labels, families, configuration),
                  cpu_seconds=time.process_time() - started, cases=len(predictions), details=details,
                  initialization="public-seed independently sampled model bank, then every family, never truth initialized",
                  hidden_access="inference receives observed and sigma only; labels loaded after inference",
                  runtime_status="expensive audit, not a scored runtime-qualified submission",
                  caveat="finite blind multistart success does not certify global identifiability")
    (ROOT / "evaluator" / "hidden" / "blind_audit.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
