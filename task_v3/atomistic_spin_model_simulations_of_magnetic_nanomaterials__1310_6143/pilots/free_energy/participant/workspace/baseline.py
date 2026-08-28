import json
import math
import sys


def predict(case):
    count=case["n_spins"]
    coordination=2*sum(bond[2] for bond in case["bonds"])/count
    magnetization=max(0.05,1-case["temperature"]/coordination)
    quadratic=[sum(tensor[axis] for tensor in case["onsite"])*magnetization**2 for axis in range(6)]
    cubic=sum(tensor[6] for tensor in case["onsite"])*magnetization**4
    quadratic[2] += sum(bond[3] for bond in case["bonds"])*magnetization**2
    origin=-quadratic[2]-cubic
    torque=[]
    free=[]
    for theta in case["angles"]:
        horizontal=math.sin(theta)
        vertical=math.cos(theta)
        energy=-quadratic[0]*horizontal**2-quadratic[2]*vertical**2-2*quadratic[4]*horizontal*vertical-cubic*(horizontal**4+vertical**4)
        field_x=2*quadratic[0]*horizontal+2*quadratic[4]*vertical+4*cubic*horizontal**3
        field_z=2*quadratic[2]*vertical+2*quadratic[4]*horizontal+4*cubic*vertical**3
        torque.append((vertical*field_x-horizontal*field_z)/count)
        free.append((energy-origin)/count)
    return {"version":1,"case_id":case["case_id"],"torque":torque,"free_energy":free}


if __name__ == "__main__":
    with open(sys.argv[1]) as stream:
        case=json.load(stream)
    with open(sys.argv[2],"w") as stream:
        json.dump(predict(case),stream)
