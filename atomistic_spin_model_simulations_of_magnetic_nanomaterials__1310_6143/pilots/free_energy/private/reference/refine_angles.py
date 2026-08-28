import json
import math

import numpy as np

from generate import REFERENCE, ROOT, load, matrices, summarize


def main():
    manifest=json.loads((ROOT/"private/challenge_pool/manifest.json").read_text())
    report={"gold_grid_points":17,"gold_sine_modes":7,"strong_grid_points":9,
            "strong_sine_modes":4,"cases":{},"status":"PENDING"}
    for entries in manifest.values():
        for entry in entries:
            case=json.loads((ROOT/entry["path"]).read_text())
            path=REFERENCE/"results"/(case["case_id"]+".json")
            reference=json.loads(path.read_text())
            angles=np.linspace(0,math.pi/2,17)
            torque=np.zeros(17)
            uncertainty=np.zeros(17)
            torque[::2]=reference["torque"]
            uncertainty[::2]=reference["torque_sem"]
            midpoint_rhat=[]
            for index in range(1,16,2):
                mean,sem,rhat,_=summarize(load(case,angles[index],"validation",2))
                torque[index]=mean[0]
                uncertainty[index]=sem[0]
                midpoint_rhat.append(rhat[:3].tolist())
            _,dense=matrices(angles,modes=7)
            _,coarse=matrices(np.array(case["angles"]))
            weights=dense[::2]
            free=weights@torque
            difference=free-coarse@torque[::2]
            difference_weights=weights.copy()
            difference_weights[:,::2]-=coarse
            difference_sem=np.sqrt((difference_weights**2)@(uncertainty**2))
            reference["free_energy"]=free.tolist()
            reference["free_energy_sem"]=np.sqrt((weights**2)@(uncertainty**2)).tolist()
            reference["angular_refinement_difference"]=difference.tolist()
            reference["angular_refinement_sem"]=difference_sem.tolist()
            reference["free_energy_method"]="17-angle, seven-sine-mode integrated torque; symmetry-fixed endpoints"
            path.write_text(json.dumps(reference,indent=2)+"\n")
            report["cases"][case["case_id"]]={"difference":difference.tolist(),
                "difference_sem":difference_sem.tolist(),"midpoint_rhat":midpoint_rhat,
                "zmax":float(np.max(np.abs(difference)/np.maximum(difference_sem,1e-20)))}
    report["max_refinement_z"]=max(item["zmax"] for item in report["cases"].values())
    report["max_midpoint_rhat"]=max(max(values) for item in report["cases"].values() for values in item["midpoint_rhat"])
    report["status"]="PASS" if report["max_refinement_z"]<5.5 and report["max_midpoint_rhat"]<1.15 else "REQUIRES_REVIEW"
    (REFERENCE/"angular_refinement.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key!="cases"}),flush=True)


if __name__ == "__main__":
    main()
