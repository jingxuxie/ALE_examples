import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]/"pilots/free_energy/private/reference"


def main():
    (ROOT/"source").mkdir(exist_ok=True)
    (ROOT/"tmp").mkdir(exist_ok=True)
    files={}
    for name in ["engine.cpp","official_cmc.inc","official_angle.inc","VAMPIRE_license","VAMPIRE_BSD_licence"]:
        original=SOURCE/name
        destination=ROOT/"source"/name
        text=original.read_text()
        if not destination.exists():
            patch="*** Begin Patch\n*** Add File: "+str(destination)+"\n"+"".join("+"+line+"\n" for line in text.splitlines())+"*** End Patch\n"
            subprocess.run(["apply_patch",patch],check=True)
        assert original.read_bytes()==destination.read_bytes(),name
        files[name]={"original":str(original),"sha256":hashlib.sha256(original.read_bytes()).hexdigest(),"byte_identical_copy":True}
    environment=os.environ.copy()
    environment["TMPDIR"]=str(ROOT/"tmp")
    command=["g++","-std=c++17","-O3","-DNDEBUG",str(ROOT/"source/engine.cpp"),"-o",str(ROOT/"frozen_engine")]
    subprocess.run(command,check=True,env=environment)
    provenance={"source_files":files,"compile_command":command,
        "compiler":subprocess.check_output(["g++","--version"],text=True).splitlines()[0],
        "binary_sha256":hashlib.sha256((ROOT/"frozen_engine").read_bytes()).hexdigest(),
        "parent_source_provenance":json.loads((SOURCE/"provenance.json").read_text()),
        "modified_pilot_files":False,"model_agents_launched":False}
    (ROOT/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")


if __name__ == "__main__":
    main()
