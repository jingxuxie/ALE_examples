"""Expensive direct-source confirmation, independent of all Chebyshev tables."""

import argparse
import json
import sys
import time
from pathlib import Path

import mpmath as mp


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input"))
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from problem import load_witness
from reference import mp_integral, verify
from search import save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", nargs="?", type=Path, default=ROOT / "adversary/best_screen")
    parser.add_argument("--report", type=Path, default=ROOT / "adversary/native_confirmation.json")
    arguments = parser.parse_args()
    started = time.monotonic()
    witness = load_witness(arguments.submission)
    coarse = mp_integral(witness, precision=50, order=24, panels=32, native=True)
    print(json.dumps({"stage": "native_coarse", "values": coarse["value"]}), flush=True)
    fine = mp_integral(witness, precision=80, order=36, panels=64, native=True)
    print(json.dumps({"stage": "native_fine", "values": fine["value"]}), flush=True)
    surrogate = verify(witness)
    with mp.workdps(85):
        gaps = [str(abs(mp.mpf(first) - mp.mpf(second))) for first, second in zip(coarse["value"], fine["value"])]
        source_gaps = [str(abs(mp.mpf(first) - mp.mpf(second))) for first, second in zip(fine["value"], surrogate["fine"]["value"])]
        resolved = all(mp.mpf(value) < mp.mpf("1e-18") for value in gaps + source_gaps)
    save(arguments.report.resolve(), {"witness": witness, "native_coarse": coarse, "native_fine": fine,
                                               "native_refinement_gaps": gaps, "native_vs_surrogate_gaps": source_gaps,
                                               "resolved": resolved, "seconds": time.monotonic() - started})
    if not resolved:
        raise RuntimeError("direct-source confirmation failed")


if __name__ == "__main__":
    main()
