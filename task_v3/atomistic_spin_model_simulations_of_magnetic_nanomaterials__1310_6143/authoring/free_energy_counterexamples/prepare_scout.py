import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
SUBMISSION=ROOT.parents[1]/"pilots/free_energy/attempt"


def main():
    hashes={}
    for name,target_name in [("solve.py","frozen_solve.py"),("sampler.cpp","sampler.cpp"),("reweight.py","reweight.py")]:
        original=SUBMISSION/name
        destination=ROOT/"scout_submission"/target_name
        if not destination.exists():
            patch="*** Begin Patch\n*** Add File: "+str(destination)+"\n"+"".join("+"+line+"\n" for line in original.read_text().splitlines())+"*** End Patch\n"
            subprocess.run(["apply_patch",patch],check=True)
        assert original.read_bytes()==destination.read_bytes(),name
        hashes[name]=hashlib.sha256(original.read_bytes()).hexdigest()
    (ROOT/"scout_protocol.json").write_text(json.dumps({"source_hashes":hashes,
        "SPIN_SECONDS":95,"SPIN_NODES":3,"SPIN_SAVE_BLOCKS":1,
        "interpretation":"Acceptance and raw-torque scout only. Reduced-node MBAR outputs are not counterexample scores. Full frozen default submission required for final claims.",
        "rejected_before_submission":{"ce_weak_interface_twist":"Official source multi-start scout Rhat=26.5463; no reliable reference"}},indent=2)+"\n")


if __name__ == "__main__":
    main()
