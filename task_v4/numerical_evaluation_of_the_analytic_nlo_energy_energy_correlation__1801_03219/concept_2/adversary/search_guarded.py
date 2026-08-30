import concurrent.futures
import itertools
import json
from pathlib import Path
import time

import numpy as np
from scipy.linalg import svd
from scipy.optimize import linprog

from search import BINS,COLOR,Kernel,assess,basis,matrices,quantize,response
from search_single_leaf import leaf_error
from target import NODES,KWEIGHTS,COMPANION_NODES,COMPANION_WEIGHTS


ROOT = Path(__file__).resolve().parent


def companion_error(kernel,witness,leaf):
    lower,upper = BINS[witness["bin"]]
    def integrate_modes(nodes,weights):
        points = (leaf+(nodes+1)/2)/8
        spectra = 2*(upper-lower)*kernel(lower+(upper-lower)*points)*COLOR
        modes = response(points,witness)[:,None]*basis(points,witness)
        return np.einsum("n,nc,nk->ck",weights/16,spectra,modes)
    return integrate_modes(NODES,KWEIGHTS)-integrate_modes(COMPANION_NODES,COMPANION_WEIGHTS)


def screen(configuration):
    frequency,bin_name,tilt,curvature,leaves = configuration
    kernel = Kernel()
    template = {"version":1,"bin":bin_name,"band_start":frequency,"tilt":tilt,"curvature":curvature}
    constraints,unused_error,reference = matrices(kernel,template)
    selected = sorted(set(leaves)|{8+leaf//2 for leaf in leaves})
    matrix = np.concatenate([constraints[:,selected,:].reshape(-1,24),
                             np.concatenate([companion_error(kernel,template,leaf) for leaf in leaves])])
    matrix /= np.maximum(np.linalg.norm(matrix,axis=1)[:,None],1e-300)
    unused_left,singular,right_vectors = svd(matrix,full_matrices=True)
    rank = len(matrix)
    if rank >= 24:
        return None
    nullspace = right_vectors[rank:].T
    error = sum(leaf_error(kernel,template,leaf) for leaf in leaves)
    points = (np.arange(256)+0.5)/256
    lower,upper = BINS[bin_name]
    spectra = 2*(upper-lower)*kernel(lower+(upper-lower)*points)*COLOR
    modes = response(points,template)[:,None]*basis(points,template)
    best = None
    for channel in [0,1]:
        objective = error[channel]/np.linalg.norm(error[channel])
        weighted = modes*spectra[:,channel,None]
        weighted /= np.linalg.norm(weighted)/np.sqrt(weighted.size)
        equality = np.zeros((rank+1,280))
        equality[:rank,:24] = right_vectors[:rank]
        equality[-1,:24] = objective
        rhs = np.zeros(rank+1)
        rhs[-1] = 1
        result = linprog(np.r_[np.zeros(24),np.ones(256)/256],
                         A_ub=np.block([[weighted,-np.eye(256)],[-weighted,-np.eye(256)]]),
                         b_ub=np.zeros(512),A_eq=equality,b_eq=rhs,
                         bounds=[(None,None)]*24+[(0,None)]*256,method="highs",
                         options={"dual_feasibility_tolerance":1e-9,"primal_feasibility_tolerance":1e-9})
        if not result.success:
            continue
        try:
            witness = quantize(template,nullspace@(nullspace.T@result.x[:24]))
        except ValueError:
            continue
        diagnostics = assess(kernel,witness,reference)
        margin = min(item["margin_screen"] for item in diagnostics)
        if best is None or margin > best["margin"]:
            best = {"margin":margin,"witness":witness,"configuration":configuration,"diagnostics":diagnostics}
    return best


def main():
    started = time.monotonic()
    leaves = [(index,) for index in range(8)]+[(0,1),(2,3),(4,5),(6,7),(0,7),(1,6)]
    configurations = list(itertools.product([53,52,50,48,40,32],["central","collinear","backward"],[-4,0,4],[-4,0,4],leaves))
    np.random.default_rng(18262026).shuffle(configurations)
    configurations = configurations[:1200]
    records,best = [],None
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for result in executor.map(screen,configurations,chunksize=1):
            if result is None:
                continue
            records.append({"margin":result["margin"],"configuration":result["configuration"]})
            if best is None or result["margin"] > best["margin"]:
                best = result
                folder = ROOT/"guarded_best"
                folder.mkdir(exist_ok=True)
                (folder/"witness.json").write_text(json.dumps(best["witness"],indent=2)+"\n")
                (folder/"screen.json").write_text(json.dumps(best,indent=2)+"\n")
                print(json.dumps({"completed":len(records),"margin":best["margin"],"configuration":best["configuration"]}),flush=True)
    (ROOT/"guarded_search_outcomes.json").write_text(json.dumps({"generation":2,"configurations":len(configurations),"completed":len(records),"best_screen_margin":best["margin"] if best else None,"elapsed_seconds":time.monotonic()-started,"records":records,"certified":False},indent=2)+"\n")


if __name__ == "__main__":
    main()
