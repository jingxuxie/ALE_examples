import argparse
import concurrent.futures
import functools
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np

ROOT=Path(__file__).resolve().parent
CASES=[
    {"id":"ferro_competing_sites","temperature":0.70,"exchange":0.90,"axial":0.22,
     "onsite":[[0.05,0.02,0.42],[0.28,-0.03,0.06]]},
    {"id":"antiferro_axial_competition","temperature":0.60,"exchange":-0.70,"axial":0.32,
     "onsite":[[0.30,-0.08,0.05],[-0.02,0.24,0.37]]},
    {"id":"antiferro_small_moment","temperature":0.22,"exchange":-1.80,"axial":-0.28,
     "onsite":[[0.23,-0.05,0.11],[-0.07,0.19,0.31]]},
    {"id":"opposite_axial_exchange","temperature":0.45,"exchange":0.25,"axial":-0.65,
     "onsite":[[0.42,0.05,-0.12],[-0.08,0.12,0.36]]},
]
ANGLES=np.linspace(0,math.pi/2,33)


def save(path,data):
    def scalar(value):
        if isinstance(value,np.generic):
            return value.item()
        raise TypeError(type(value).__name__)
    path.write_text(json.dumps(data,indent=2,allow_nan=False,default=scalar)+"\n")


@functools.lru_cache(maxsize=None)
def nodes(order,azimuths,upper):
    roots,weights=np.polynomial.legendre.leggauss(order)
    longitudinal=upper*(roots+1)/2
    weights=upper*weights/2
    phase=2*math.pi*np.arange(azimuths)/azimuths
    return longitudinal[:,None],weights[:,None],np.cos(phase)[None,:],np.sin(phase)[None,:]


def quadrature(case,angle,order=256,azimuths=512,measure_power=1,bond_factor=1.0,upper=1.0):
    longitudinal,weights,cosine,sine=nodes(order,azimuths,upper)
    radius=np.sqrt(1-longitudinal**2)
    tangent=radius*cosine
    first=np.array([longitudinal*np.sin(angle)+tangent*np.cos(angle),radius*sine,
                    longitudinal*np.cos(angle)-tangent*np.sin(angle)])
    second=np.array([longitudinal*np.sin(angle)-tangent*np.cos(angle),-radius*sine,
                     longitudinal*np.cos(angle)+tangent*np.sin(angle)])
    tensors=np.array(case["onsite"])
    exchange=-case["exchange"]*(2*longitudinal**2-1)
    axial=-case["axial"]*first[2]*second[2]
    onsite=-(tensors[0,:,None,None]*first**2+tensors[1,:,None,None]*second**2).sum(axis=0)
    energy=onsite+exchange+axial
    sampling_energy=onsite+bond_factor*(exchange+axial)
    torque=2*(tensors[0,0]-tensors[0,2])*first[0]*first[2]
    torque+=2*(tensors[1,0]-tensors[1,2])*second[0]*second[2]
    torque-=case["axial"]*(first[0]*second[2]+first[2]*second[0])
    shift=float(sampling_energy.min())
    density=(measure_power+1)*longitudinal**measure_power*weights/azimuths
    weighted=density*np.exp(-(sampling_energy-shift)/case["temperature"])
    partition=float(weighted.sum())
    average=lambda values:float(np.sum(weighted*values)/partition)
    return {"log_partition":math.log(partition)-shift/case["temperature"],
            "torque":average(torque)/2,"moment":average(longitudinal),"energy":average(energy)/2}


def simpson_matrix():
    spacing=float(ANGLES[1]-ANGLES[0])
    matrix=np.zeros((len(ANGLES[::2]),len(ANGLES)))
    for row,last in enumerate(range(2,len(ANGLES),2),1):
        coefficients=np.ones(last+1)
        coefficients[1:-1:2]=4
        coefficients[2:-1:2]=2
        matrix[row,:last+1]=-spacing*coefficients/3
    return matrix


def prepare_oracle():
    report={"angles":ANGLES.tolist(),"measure":"2u du dphi/(2pi)","cases":{},"checks":{}}
    errors=[]
    derivative_errors=[]
    for case in CASES:
        samples=[]
        controls={"flat_u":[],"u_squared":[],"double_bond":[]}
        for angle in ANGLES:
            coarse=quadrature(case,angle,128,256)
            fine=quadrature(case,angle,256,512)
            errors.extend(abs(fine[key]-coarse[key]) for key in fine)
            samples.append(fine)
            controls["flat_u"].append(quadrature(case,angle,measure_power=0))
            controls["u_squared"].append(quadrature(case,angle,measure_power=2))
            controls["double_bond"].append(quadrature(case,angle,bond_factor=2))
        center=quadrature(case,math.pi/4,384,768)
        errors.extend(abs(center[key]-samples[16][key]) for key in center)
        delta=1e-5
        lower=quadrature(case,math.pi/4-delta)
        upper=quadrature(case,math.pi/4+delta)
        partition_torque=case["temperature"]*(upper["log_partition"]-lower["log_partition"])/(4*delta)
        derivative_errors.append(abs(center["torque"]-partition_torque))
        free=-case["temperature"]*(np.array([item["log_partition"] for item in samples])-samples[0]["log_partition"])/2
        integrated=simpson_matrix()@np.array([item["torque"] for item in samples])
        restricted=quadrature(case,math.pi/4,384,768,upper=0.2)
        report["cases"][case["id"]]={"parameters":case,"samples":samples,"free_energy":free.tolist(),
            "simpson_bias":(integrated-free[::2]).tolist(),"controls":controls,
            "probability_moment_below_point2_at_pi4":math.exp(restricted["log_partition"]-center["log_partition"])}
        print("ORACLE "+case["id"],flush=True)
    analytic=[]
    for exchange in [-1.8,0.0,0.9]:
        case={"exchange":exchange,"axial":0,"temperature":0.7,"onsite":[[0,0,0],[0,0,0]]}
        actual=quadrature(case,0.417)
        ratio=exchange/case["temperature"]
        expected_log=math.log(math.sinh(ratio)/ratio) if ratio else 0.0
        expected_energy=-exchange*(1/math.tanh(ratio)-1/ratio)/2 if ratio else 0.0
        analytic.extend([abs(actual["log_partition"]-expected_log),abs(actual["energy"]-expected_energy)])
        if not ratio:
            analytic.append(abs(actual["moment"]-2/3))
    report["checks"]={"maximum_order_refinement_error":max(errors),
        "maximum_partition_derivative_torque_error":max(derivative_errors),
        "maximum_isotropic_analytic_error":max(analytic)}
    report["status"]="PASS" if max(errors)<1e-10 and max(derivative_errors)<1e-8 and max(analytic)<1e-10 else "FAIL"
    save(ROOT/"results/oracle.json",report)
    return report


def worker(job):
    case,angle_index,chain,phase=job
    token=f"{phase}_{case['id']}_{angle_index:02d}_{chain:02d}"
    output=ROOT/"raw"/(token+".npz")
    if output.exists():
        return token
    burn,sweeps,block=(20000,100000,2000) if phase=="screen" else (100000,1000000,10000)
    seed=int(hashlib.sha256(("two-spin-exact-audit:"+token).encode()).hexdigest()[:15],16)
    environment=os.environ.copy()
    environment.pop("REFERENCE_HOT_START",None)
    if chain%2:
        environment["REFERENCE_HOT_START"]="1"
    started=time.monotonic()
    command=[str(ROOT/"frozen_engine"),str(ROOT/"models"/(case["id"]+".txt")),
             str(case["temperature"]),str(float(ANGLES[angle_index])),str(burn),str(sweeps),str(block),str(seed)]
    result=subprocess.run(command,capture_output=True,text=True,env=environment,check=True,timeout=180)
    blocks=np.array([[float(value) for value in line.split()] for line in result.stdout.splitlines()])
    if blocks.shape!=(sweeps//block,6) or not np.isfinite(blocks).all():
        raise RuntimeError("Invalid native output: "+token)
    np.savez_compressed(output,blocks=blocks,seed=seed,burn=burn,sweeps=sweeps,block=block,
                        seconds=time.monotonic()-started,hot_start=bool(chain%2))
    return token


def statistics(blocks):
    chain_means=blocks.mean(axis=1)
    chains,count,_=blocks.shape
    within=np.var(blocks,axis=1,ddof=1).mean(axis=0)
    between=count*np.var(chain_means,axis=0,ddof=1)
    rhat=np.sqrt(np.maximum(0,((count-1)*within+between)/(count*np.maximum(within,1e-30))))
    uncertainty=np.std(chain_means,axis=0,ddof=1)/math.sqrt(chains)
    for grouping in [1,2,5]:
        reblocked=blocks.reshape(chains,count//grouping,grouping,6).mean(axis=2)
        variance=np.var(reblocked,axis=1,ddof=1).mean(axis=0)
        uncertainty=np.maximum(uncertainty,np.sqrt(variance/(chains*(count//grouping))))
    return chain_means.mean(axis=0),uncertainty,rhat


def load(case,index,chains,phase):
    return np.array([np.load(ROOT/"raw"/(f"{phase}_{case['id']}_{index:02d}_{chain:02d}.npz"),allow_pickle=False)["blocks"]
                     for chain in range(chains)])


def evaluate(oracle,phase,chains,indices):
    report={"phase":phase,"chains":chains,"cases":{},"status":"PENDING"}
    z_values=[]
    rhats=[]
    constraints=[]
    free_z=[]
    bias_ratios=[]
    powers=[]
    for case in CASES:
        records=[]
        gold=oracle["cases"][case["id"]]
        control_z={key:[] for key in gold["controls"]}
        for index in indices:
            blocks=load(case,index,chains,phase)
            mean,sem,rhat=statistics(blocks)
            target=np.array([gold["samples"][index][name] for name in ["torque","moment","energy"]])
            difference=mean[:3]-target
            standardized=difference/np.maximum(sem[:3],1e-15)
            z_values.extend(abs(standardized))
            rhats.extend(rhat[:3])
            constraints.extend([blocks[:,:,3].max(),blocks[:,:,4].max()])
            for name,predictions in gold["controls"].items():
                wrong=np.array([predictions[index][key] for key in ["torque","moment","energy"]])
                control_z[name].extend(abs(mean[:3]-wrong)/np.maximum(sem[:3],1e-15))
            records.append({"angle":float(ANGLES[index]),"native_mean":mean[:3].tolist(),
                "quadrature_mean":target.tolist(),"block_sem":sem[:3].tolist(),"z":standardized.tolist(),
                "rhat":rhat[:3].tolist(),"maximum_block_mean_constraint_drift":float(blocks[:,:,3].max()),
                "maximum_block_mean_norm_error":float(blocks[:,:,4].max()),"acceptance":float(mean[5])})
        entry={"angle_comparisons":records,"wrong_target_zmax":{key:float(max(values)) for key,values in control_z.items()}}
        powers.extend(entry["wrong_target_zmax"].values())
        if phase=="full":
            weights=simpson_matrix()
            means=np.array([item["native_mean"][0] for item in records])
            sems=np.array([item["block_sem"][0] for item in records])
            free=weights@means
            uncertainty=np.sqrt((weights**2)@(sems**2))
            exact=np.array(gold["free_energy"])[::2]
            standardized=(free-exact)/np.maximum(uncertainty,1e-15)
            free_z.extend(abs(standardized[1:]))
            ratios=np.abs(gold["simpson_bias"])/np.maximum(uncertainty,1e-15)
            bias_ratios.extend(ratios[1:])
            entry["free_energy"]={"angles":ANGLES[::2].tolist(),"native_integrated_torque":free.tolist(),
                "direct_log_partition":exact.tolist(),"propagated_block_sem":uncertainty.tolist(),
                "raw_z":standardized.tolist(),"quadrature_only_simpson_bias":gold["simpson_bias"],
                "integration_bias_corrected":False}
        report["cases"][case["id"]]=entry
    report.update(max_observable_z=float(max(z_values)),max_rhat=float(max(rhats)),
                  max_constraint_or_norm=float(max(constraints)),minimum_wrong_target_zmax=float(min(powers)))
    if phase=="full":
        report.update(max_free_energy_z=float(max(free_z)),max_simpson_bias_over_sem=float(max(bias_ratios)))
    gates={"oracle":oracle["status"]=="PASS","stationary_moments":max(z_values)<(7 if phase=="screen" else 5.5),
           "constraint_and_norm":max(constraints)<1e-7}
    if phase=="full":
        gates.update(mixing=max(rhats)<1.05,free_energy=max(free_z)<5.5,
                     angular_bias_below_sampling_noise=max(bias_ratios)<0.25,negative_control_power=min(powers)>8)
    report["gates"]={key:bool(value) for key,value in gates.items()}
    report["status"]="PASS" if all(gates.values()) else "FAIL"
    save(ROOT/"results"/(phase+".json"),report)
    print(json.dumps({key:value for key,value in report.items() if key!="cases"}),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=16)
    parser.add_argument("--aggregate-only",action="store_true")
    arguments=parser.parse_args()
    for folder in ["models","raw","results"]:
        (ROOT/folder).mkdir(exist_ok=True)
    for case in CASES:
        lines=["2 1"]+[" ".join(format(value,".17g") for value in row+[0,0,0,0]) for row in case["onsite"]]
        lines.append(f"0 1 {case['exchange']:.17g} {case['axial']:.17g}")
        (ROOT/"models"/(case["id"]+".txt")).write_text("\n".join(lines)+"\n")
    save(ROOT/"cases.json",{"cases":CASES,"angles":ANGLES.tolist(),"n_spins":2,"audit_only":True})
    oracle_path=ROOT/"results/oracle.json"
    oracle=json.loads(oracle_path.read_text()) if oracle_path.exists() else prepare_oracle()
    if oracle["status"]!="PASS":
        raise RuntimeError("Independent quadrature validation failed")
    for phase,chains,indices in [("screen",6,[8,16,24]),("full",12,list(range(len(ANGLES))))]:
        jobs=[(case,index,chain,phase) for case in CASES for index in indices for chain in range(chains)]
        if not arguments.aggregate_only:
            with concurrent.futures.ThreadPoolExecutor(max_workers=arguments.workers) as executor:
                for index,future in enumerate(concurrent.futures.as_completed([executor.submit(worker,job) for job in jobs]),1):
                    token=future.result()
                    if index%24==0 or index==len(jobs):
                        print(f"{phase} jobs {index}/{len(jobs)}: {token}",flush=True)
        result=evaluate(oracle,phase,chains,indices)
        if result["status"]!="PASS":
            save(ROOT/"STATUS.json",{"status":"FAIL","phase":phase,"gates":result["gates"],"action":"Alert main; do not modify pilot targets or references"})
            raise RuntimeError("FROZEN ENGINE AUDIT FAILED: "+phase)
    save(ROOT/"STATUS.json",{"status":"PASS","stationary_ensemble":"directional solid-angle, 2u du dphi/(2pi)",
        "cases":4,"angles_per_case":len(ANGLES),"independent_chains_per_angle":12,
        "burn_sweeps":100000,"measured_sweeps":1000000,"block_sweeps":10000,
        "max_observable_z":result["max_observable_z"],"max_free_energy_z":result["max_free_energy_z"],
        "max_rhat":result["max_rhat"],"pilot_modified":False,"model_agents_launched":False})


if __name__ == "__main__":
    main()
