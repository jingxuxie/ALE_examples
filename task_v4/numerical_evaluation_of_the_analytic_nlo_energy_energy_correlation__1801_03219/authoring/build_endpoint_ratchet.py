import concurrent.futures
import json
from pathlib import Path
import sys
import time

import mpmath as mp
import numpy as np
from scipy.fft import dct

from endpoint_basis import leading_terms, native_chart
import native_kernel


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT/"concept_1"
sys.path.insert(0,str(CONCEPT/"participant/workspace"))
from model import evaluate, bin_average


def native_value(request):
    coordinate,chart = request
    with mp.workdps(140):
        return [float(mp.re(value)) for value in native_chart(mp.mpf(float(coordinate)),chart,native_kernel)]


def native_derivative(request):
    coordinate,chart = request
    with mp.workdps(180):
        displacement = mp.mpf("1e-40")
        return [float(mp.im(value)/displacement) for value in native_chart(mp.mpf(float(coordinate))+mp.j*displacement,chart,native_kernel)]


def make_reference(degree,executor):
    knots = np.linspace(-24,24,25)
    canonical = np.cos(np.arange(degree+1)*np.pi/degree)
    charts = ["collinear" if right <= -4 else "backward" if left >= 4 else "density"
              for left,right in zip(knots[:-1],knots[1:])]
    requests = [(left+(right-left)*(coordinate+1)/2,chart)
                for left,right,chart in zip(knots[:-1],knots[1:],charts) for coordinate in canonical]
    samples = np.asarray(list(executor.map(native_value,requests,chunksize=8))).reshape(24,degree+1,3)
    coefficients = []
    for samples_block in samples:
        values = dct(samples_block,type=1,axis=0)/degree
        values[[0,-1]] /= 2
        coefficients.append(values.T)
    return {"knots":knots,"coefficients":np.asarray(coefficients),"charts":np.asarray(charts)}


def main():
    started = time.monotonic()
    hidden = CONCEPT/"evaluator/hidden"
    high_path,low_path = hidden/"oracle.npz",hidden/"oracle_low.npz"
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        high,low = make_reference(40,executor),make_reference(24,executor)
        np.savez(high_path,**high)
        np.savez(low_path,**low)
        generator = np.random.default_rng(180103220)
        audit_coordinates = generator.uniform(-24,24,96)
        requests = [(coordinate,"collinear" if coordinate < -4 else "backward" if coordinate >= 4 else "density") for coordinate in audit_coordinates]
        native_values = np.asarray(list(executor.map(native_value,requests)))
        native_derivatives = np.asarray(list(executor.map(native_derivative,requests)))
    dense = np.linspace(-24,24,12001)
    audit = {}
    for label,derivative in [("values",False),("derivatives",True)]:
        truth = evaluate(high,dense,derivative)
        audit["degree_24_40_"+label] = float(np.max(np.abs(evaluate(low,dense,derivative)-truth)/(1+np.abs(truth))))
    for label,truth,derivative in [("native_values",native_values,False),("native_derivatives",native_derivatives,True)]:
        audit[label] = float(np.max(np.abs(evaluate(high,audit_coordinates,derivative)-truth)/(1+np.abs(truth))))
    if max(audit.values()) > 2e-9:
        raise ValueError(f"oracle audit failed: {audit}")
    coordinates = np.linspace(-24,24,769)
    np.savez(CONCEPT/"participant/input/calibration.npz",coordinates=coordinates,
             values=evaluate(high,coordinates),derivatives=evaluate(high,coordinates,True),
             density_values=evaluate(high,coordinates,observable="density"))
    hidden_coordinates = np.concatenate([generator.uniform(-24,24,1600),[-24,24,-4,4],
                                          np.nextafter([-4.,4.],-np.inf)])
    lower = generator.uniform(-23.9,23.9,360)
    upper = np.minimum(24,lower+np.exp(generator.uniform(np.log(1e-5),np.log(12),len(lower))))
    bins = np.column_stack((lower,upper))
    weights = generator.normal(size=(len(hidden_coordinates),3))
    weights /= np.sum(np.abs(weights),axis=1)[:,None]
    truth = evaluate(high,hidden_coordinates)
    for index in range(0,len(hidden_coordinates),3):
        vector = [truth[index,1],-truth[index,0],0]
        weights[index] = vector/np.sum(np.abs(vector))
    density_reference = dict(np.load(CONCEPT/"champions/generation_1/task_snapshot/evaluator/hidden/oracle.npz"))
    averages = np.array([bin_average(density_reference,left,right) for left,right in bins])
    np.savez(hidden/"cases.npz",coordinates=hidden_coordinates,values=truth,
             derivatives=evaluate(high,hidden_coordinates,True),bins=bins,averages=averages,weights=weights)
    source_density = evaluate(density_reference,hidden_coordinates,observable="density")
    audit["reconstructed_density_discrepancy"] = float(np.max(np.abs(evaluate(high,hidden_coordinates,observable="density")-source_density)/(1+np.abs(source_density))))
    audit.update({"native_dps":140,"derivative_dps":180,"complex_step":"1e-40", "elapsed_seconds":time.monotonic()-started})
    (hidden/"oracle_audit.json").write_text(json.dumps(audit,indent=2)+"\n")
    print(json.dumps(audit,indent=2),flush=True)


if __name__ == "__main__":
    main()
