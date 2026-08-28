import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def make_case(family, index, split):
    variation = index + {"initial": 0, "challenge": 3, "confirmation": 9}[split]
    size = [16, 16, 8] if family != "cubic_particle" else [14, 14, 14]
    periodic = [True, True, False] if family != "cubic_particle" else [False, False, False]
    count = math.prod(size)
    temperature = [0.55, 0.9, 0.7, 1.0][variation % 4] + 0.01*(variation//4)
    onsite = []
    bonds = []
    positions = []
    exchange_soft = 0.62 + 0.04*(variation % 3)
    bulk = 0.011 + 0.002*(variation % 4) + 0.0001*variation
    surface = 0.055 + 0.013*(variation % 4)
    for depth in range(size[2]):
        for row in range(size[1]):
            for column in range(size[0]):
                position = [column, row, depth]
                positions.append(position)
                tensor = [0.0]*7
                if family == "surface_reorientation":
                    tensor[2] = bulk
                    if depth in [0,size[2]-1]:
                        tensor[0] = surface
                        tensor[1] = surface
                elif family == "interface_spring":
                    tensor[2 if depth < size[2]//2 else 0] = 0.04 + 0.009*(variation % 3)
                    if depth in [size[2]//2-1, size[2]//2]:
                        tensor[2] += 0.012
                else:
                    tensor[6] = 0.026 + 0.005*(variation % 3)
                    tensor[2] = 0.008
                    for axis in range(3):
                        if position[axis] in [0,size[axis]-1]:
                            tensor[axis] += (0.095 if axis == 0 else 0.055)*(1+0.1*(variation % 3))
                onsite.append(tensor)
                first = column+size[0]*(row+size[1]*depth)
                for axis in range(3):
                    target = position.copy()
                    target[axis] += 1
                    if target[axis] == size[axis]:
                        if not periodic[axis]:
                            continue
                        target[axis] = 0
                    second = target[0]+size[0]*(target[1]+size[1]*target[2])
                    exchange = 1.0
                    axial = 0.0
                    if family == "interface_spring":
                        if depth >= size[2]//2:
                            exchange = exchange_soft
                        if axis == 2 and depth == size[2]//2-1:
                            exchange = 0.42 + 0.04*(variation % 3)
                            axial = 0.1 + 0.02*(variation % 3)
                    bonds.append([first,second,exchange,axial])
    return {"version":1,"case_id":f"{split}_{family}_{index:02d}","family":family,
            "n_spins":count,"temperature":temperature,"seed":771031+variation*293,
            "shape":size,"periodic":periodic,"onsite":onsite,"bonds":bonds,
            "angles":[math.pi*index/16 for index in range(9)]}


def native(case, path):
    with path.open("w") as stream:
        stream.write(f"{case['n_spins']} {len(case['bonds'])}\n")
        for tensor in case["onsite"]:
            stream.write(" ".join(map(str,tensor))+"\n")
        for bond in case["bonds"]:
            stream.write(" ".join(map(str,bond))+"\n")


if __name__ == "__main__":
    families = ["surface_reorientation", "interface_spring", "cubic_particle"]
    manifest = {"initial":[],"challenge":[],"confirmation":[]}
    for split, number in [("initial",2),("challenge",4),("confirmation",2)]:
        for family in families:
            for index in range(number):
                case = make_case(family,index,split)
                directory = ROOT / ("participant/input/cases" if split == "initial" else "private/challenge_pool/cases")
                directory.mkdir(parents=True,exist_ok=True)
                path = directory / (case["case_id"]+".json")
                payload = json.dumps(case,separators=(",",":"))+"\n"
                path.write_text(payload)
                native_dir = ROOT / "private/reference/native"
                native_dir.mkdir(parents=True,exist_ok=True)
                native(case,native_dir/(case["case_id"]+".txt"))
                manifest[split].append({"id":case["case_id"],"path":str(path.relative_to(ROOT)),"family":family,
                                        "sha256":hashlib.sha256(payload.encode()).hexdigest()})
    (ROOT/"private/challenge_pool").mkdir(parents=True,exist_ok=True)
    (ROOT/"private/challenge_pool/manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (ROOT/"private/challenge_pool/ratchet_reserve.json").write_text(json.dumps({
        "status":"UNGENERATED: not used for fitting, reference validation, or current scoring",
        "seeds":[971779,981043,991013,1001033,1012037,1023119],
        "regions":{"temperature":[0.6,0.8,0.95],"slab_shapes":[[18,18,8],[16,16,10]],
                   "interface_exchange":[0.35,0.55],"surface_scale":[0.085,0.115],"particle_shapes":[[15,15,15]]}
    },indent=2)+"\n")
