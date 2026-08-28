import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
REFERENCE=ROOT/"private/reference"
sys.path.insert(0,str(ROOT/"participant/workspace"))
from model import adjacency, energy_and_torque, local_energy


def main():
    provenance=json.loads((REFERENCE/"provenance.json").read_text())
    source=ROOT.parents[1]/"authoring/vampire"
    verified=[]
    for name,entry in provenance.items():
        if not isinstance(entry,dict):
            continue
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==entry["source_sha256"]
        assert hashlib.sha256((REFERENCE/entry["destination"]).read_bytes()).hexdigest()==entry["extracted_sha256"]
        verified.append(name)
    report={"source_hashes_verified":verified,"families":{},"status":"PENDING"}
    random=np.random.default_rng(738917)
    manifest=json.loads((ROOT/"private/challenge_pool/manifest.json").read_text())
    entries=[entry for entry in manifest["initial"] if entry["id"].endswith("00")]
    with tempfile.TemporaryDirectory(dir=REFERENCE,prefix="check_") as directory:
        state_path=Path(directory)/"spins.txt"
        for entry in entries:
            case=json.loads((ROOT/entry["path"]).read_text())
            count=case["n_spins"]
            spins=random.normal(size=(count,3))
            spins/=np.linalg.norm(spins,axis=1)[:,None]
            def native(state):
                np.savetxt(state_path,state,fmt="%.17g")
                result=subprocess.run([str(REFERENCE/"inspect_state"),str(REFERENCE/"native"/(case["case_id"]+".txt")),str(state_path)],check=True,capture_output=True,text=True)
                return np.fromstring(result.stdout,sep=" ")
            observation=native(spins)
            energy,torque=energy_and_torque(case,spins)
            step=1e-5
            rotation=np.array([[np.cos(step),0,np.sin(step)],[0,1,0],[-np.sin(step),0,np.cos(step)]])
            plus=native(spins@rotation.T)
            minus=native(spins@rotation)
            finite_difference=-(plus[1]-minus[1])/(2*step)
            neighbors=adjacency(case)
            local_before=local_energy(case,spins,31,neighbors)
            proposed=spins.copy()
            proposed[31]=random.normal(size=3)
            proposed[31]/=np.linalg.norm(proposed[31])
            changed=native(proposed)
            independent_energy,_=energy_and_torque(case,proposed)
            checks={"n_spins":count,"native_python_energy_abs":abs(observation[1]-energy),
                    "native_python_torque_abs":abs(observation[0]-torque),
                    "torque_rotation_finite_difference_abs":abs(finite_difference-torque),
                    "local_total_delta_abs":abs((changed[2]-observation[2])-(independent_energy-energy)),
                    "local_python_abs":abs(observation[2]-local_before),
                    "dimensionless_exponent_abs":abs(observation[3]-local_before)}
            assert max(value for key,value in checks.items() if key!="n_spins")<1e-6,checks
            report["families"][case["family"]]=checks
    report["status"]="PASS"
    (REFERENCE/"independent_checks.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report),flush=True)


if __name__ == "__main__":
    main()
