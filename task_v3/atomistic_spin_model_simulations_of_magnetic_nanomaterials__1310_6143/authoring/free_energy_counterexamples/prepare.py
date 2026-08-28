import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
PILOT=ROOT.parents[1]/"pilots/free_energy"


def main():
    for folder in ["cases","models","reference/source","reference/raw","reference/results","tmp","submissions"]:
        (ROOT/folder).mkdir(parents=True,exist_ok=True)
    film=json.loads((PILOT/"participant/input/cases/initial_surface_reorientation_00.json").read_text())
    spring=json.loads((PILOT/"participant/input/cases/initial_interface_spring_00.json").read_text())
    cases=[]
    case=copy.deepcopy(film)
    case.update(case_id="ce_surface_compensation",temperature=0.80,seed=1100383)
    for index,row in enumerate(case["onsite"]):
        depth=index//256
        row[:]=[0.40 if depth in [0,7] else 0.0,0.40 if depth in [0,7] else 0.0,0.10,0,0,0,0]
    cases.append(case)
    case=copy.deepcopy(film)
    case.update(case_id="ce_bulk_twoion_competition",family="bulk_twoion_competition",temperature=1.12,seed=1100411)
    for index,row in enumerate(case["onsite"]):
        plane=0.24+(0.035 if index//256 in [0,7] else 0)
        row[:]=[plane,plane,0,0,0,0,0]
    for bond in case["bonds"]:
        bond[3]=0.12
    cases.append(case)
    case=copy.deepcopy(spring)
    case.update(case_id="ce_weak_interface_twist",temperature=0.65,seed=1100449)
    for index,row in enumerate(case["onsite"]):
        depth=index//256
        row[:]=[0.18 if depth>=4 else 0,0,0.18 if depth<4 else 0,0,0,0,0]
        if depth in [3,4]:
            row[2]+=0.012
    for bond in case["bonds"]:
        first_layer,second_layer=bond[0]//256,bond[1]//256
        bond[2]=0.65 if min(first_layer,second_layer)>=4 else 1.0
        bond[3]=0.0
        if {first_layer,second_layer}=={3,4}:
            bond[2]=0.18
            bond[3]=0.10
    cases.append(case)
    manifest=[]
    for case in cases:
        path=ROOT/"cases"/(case["case_id"]+".json")
        payload=json.dumps(case,separators=(",",":"))+"\n"
        if path.exists():
            assert path.read_text()==payload,"Counterexample input already frozen"
        else:
            path.write_text(payload)
        model=ROOT/"models"/(case["case_id"]+".txt")
        with model.open("w") as stream:
            stream.write(f"{case['n_spins']} {len(case['bonds'])}\n")
            for row in case["onsite"]:
                stream.write(" ".join(format(value,".17g") for value in row)+"\n")
            for row in case["bonds"]:
                stream.write(" ".join(map(str,row))+"\n")
        manifest.append({"id":case["case_id"],"n_spins":case["n_spins"],"path":str(path.relative_to(ROOT)),
                         "sha256":hashlib.sha256(payload.encode()).hexdigest()})
    (ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    sources={}
    for name in ["engine.cpp","official_cmc.inc","official_angle.inc","VAMPIRE_license","VAMPIRE_BSD_licence"]:
        original=PILOT/"private/reference"/name
        target=ROOT/"reference/source"/name
        if not target.exists():
            patch="*** Begin Patch\n*** Add File: "+str(target)+"\n"+"".join("+"+line+"\n" for line in original.read_text().splitlines())+"*** End Patch\n"
            subprocess.run(["apply_patch",patch],check=True)
        assert original.read_bytes()==target.read_bytes()
        sources[name]={"original":str(original),"sha256":hashlib.sha256(original.read_bytes()).hexdigest()}
    command=["g++","-O3","-std=c++17","-DNDEBUG",str(ROOT/"reference/driver.cpp"),"-o",str(ROOT/"reference/cmc")]
    subprocess.run(command,check=True,env=dict(os.environ,TMPDIR=str(ROOT/"tmp")))
    (ROOT/"source_provenance.json").write_text(json.dumps({"files":sources,"compile":command,
        "kernel":"Unchanged official VAMPIRE cmc_step and mc_angle; new initialization/measurement wrapper only"},indent=2)+"\n")


if __name__ == "__main__":
    main()
