import json
from pathlib import Path
import sys
import time

import mpmath as mp


ROOT = Path(__file__).resolve().parents[1]/"concept_2"
sys.path.insert(0,str(ROOT/"participant/input"))
sys.path.insert(0,str(ROOT/"evaluator/hidden"))
from problem import load_witness
from reference import mp_integral,verify


def main():
    directory = Path(sys.argv[1]).resolve()
    witness = load_witness(directory/"witness.json")
    started = time.monotonic()
    coarse = mp_integral(witness,precision=50,order=24,panels=32,native=True)
    fine = mp_integral(witness,precision=80,order=36,panels=64,native=True)
    surrogate = verify(witness)
    with mp.workdps(90):
        native_gaps = [str(abs(mp.mpf(first)-mp.mpf(second))) for first,second in zip(coarse["value"],fine["value"])]
        source_gaps = [str(abs(mp.mpf(first)-mp.mpf(second))) for first,second in zip(fine["value"],surrogate["fine"]["value"])]
        resolved = all(mp.mpf(gap) < mp.mpf("1e-18") for gap in native_gaps+source_gaps)
    report = {"witness":witness,"native_coarse":coarse,"native_fine":fine,
              "native_refinement_gaps":native_gaps,"native_vs_surrogate_gaps":source_gaps,
              "resolved":resolved,"elapsed_seconds":time.monotonic()-started}
    (directory/"direct_native_confirmation.json").write_text(json.dumps(report,indent=2)+"\n")
    if not resolved:
        raise RuntimeError("source-native confirmation failed")
    print(json.dumps({"directory":str(directory),"resolved":resolved,"native_refinement_gaps":native_gaps,"native_vs_surrogate_gaps":source_gaps,"elapsed_seconds":report["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
