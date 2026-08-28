import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    case=json.loads((ROOT/"cases/ce_bulk_twoion_competition.json").read_text())
    case.update(case_id="ce_compensated_exchange_stiffness",temperature=1.05,seed=1100521)
    degree=[0]*case["n_spins"]
    for first,second,exchange,axial in case["bonds"]:
        degree[first]+=1
        degree[second]+=1
    for index,row in enumerate(case["onsite"]):
        plane=0.125*degree[index]
        row[:]=[plane,plane,0,0,0,0,0]
    for row in case["bonds"]:
        row[3]=0.25
    payload=json.dumps(case,separators=(",",":"))+"\n"
    path=ROOT/"cases"/(case["case_id"]+".json")
    if path.exists():
        assert path.read_text()==payload
    else:
        path.write_text(payload)
    model=ROOT/"models"/(case["case_id"]+".txt")
    with model.open("w") as stream:
        stream.write(f"{case['n_spins']} {len(case['bonds'])}\n")
        for row in case["onsite"]:
            stream.write(" ".join(format(value,".17g") for value in row)+"\n")
        for row in case["bonds"]:
            stream.write(" ".join(map(str,row))+"\n")
    manifest=json.loads((ROOT/"manifest.json").read_text())
    entry={"id":case["case_id"],"n_spins":case["n_spins"],"path":str(path.relative_to(ROOT)),
           "sha256":hashlib.sha256(payload.encode()).hexdigest()}
    if not any(item["id"]==entry["id"] for item in manifest):
        manifest.append(entry)
    (ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (ROOT/"compensation_region.json").write_text(json.dumps({"case":case["case_id"],"n_spins":2048,
        "source":"https://arxiv.org/pdf/2002.02548", "source_locations":"Eq. (1), Eq. (5), Eq. (11), Fig. 2 discussion: cancellation at T=0 and finite anisotropy at finite T",
        "construction":"b=.25; Qxx_i=Qyy_i=b*degree_i/2; Qzz_i=0",
        "identity":"H_anis = constant + (b/2) sum_bonds (s_iz-s_jz)^2",
        "interpretation":"Exactly orientation-independent uniform-spin energy. Nonuniform thermal fluctuations carry directional free energy. Same frozen Hamiltonian and N; stress-model coefficients, not fitted material values.",
        "scout_limit":"This third isolated kernel scout tests acceptance/raw torque only; no full-reference expense without an observed discrepancy."},indent=2)+"\n")


if __name__ == "__main__":
    main()
