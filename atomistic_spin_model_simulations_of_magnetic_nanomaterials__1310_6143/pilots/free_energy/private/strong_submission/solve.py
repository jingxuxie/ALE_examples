import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np


def main():
    case=json.loads(Path(sys.argv[1]).read_text())
    source=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="cmc_reference_") as directory:
        directory=Path(directory)
        binary=directory/"reference"
        subprocess.run(["g++","-std=c++17","-O3","-DNDEBUG",str(source/"engine.cpp"),"-o",str(binary)],check=True)
        model=directory/"model.txt"
        with model.open("w") as stream:
            stream.write(f"{case['n_spins']} {len(case['bonds'])}\n")
            for row in case["onsite"]:
                stream.write(" ".join(format(value,".17g") for value in row)+"\n")
            for first,second,exchange,axial in case["bonds"]:
                stream.write(f"{first} {second} {exchange:.17g} {axial:.17g}\n")
        torque=np.zeros(len(case["angles"]))
        environment=os.environ.copy()
        environment["REFERENCE_HOT_START"]="1"
        for index,angle in enumerate(case["angles"][1:-1],1):
            means=[]
            for chain in range(2):
                token=f"{case['case_id']}_strong_{angle:.10f}_{chain}"
                seed=int(hashlib.sha256(token.encode()).hexdigest()[:15],16)
                result=subprocess.run([str(binary),str(model),str(case["temperature"]),str(angle),"6000","10000","200",str(seed)],
                                      env=environment,check=True,capture_output=True,text=True)
                blocks=np.array([[float(value) for value in line.split()] for line in result.stdout.splitlines()])
                means.append(float(blocks[:,0].mean()))
            torque[index]=np.mean(means)
        angles=np.array(case["angles"])
        harmonics=2*np.arange(1,5)
        coefficients=np.linalg.lstsq(np.sin(np.outer(angles,harmonics)),torque,rcond=None)[0]
        free=(-(1-np.cos(np.outer(angles,harmonics)))/harmonics)@coefficients
        Path(sys.argv[2]).write_text(json.dumps({"version":1,"case_id":case["case_id"],"torque":torque.tolist(),"free_energy":free.tolist()})+"\n")


if __name__ == "__main__":
    main()
