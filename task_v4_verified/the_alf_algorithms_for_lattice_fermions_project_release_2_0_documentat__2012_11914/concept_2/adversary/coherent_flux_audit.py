import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "adversary/champion_coherent_flux_v1"
specification = importlib.util.spec_from_file_location("audit_cluster_helpers", ROOT / "adversary/cluster_champion_failures.py")
helpers = importlib.util.module_from_spec(specification)
specification.loader.exec_module(helpers)
helpers.DIRECTORY = OUT


def main():
    started = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / "adversary/champion_audit_v1"
    for name in ("candidate.json", "baseline.json", "original_contract.json"):
        (OUT / name).write_bytes((source / name).read_bytes())
    candidate = json.loads((OUT / "candidate.json").read_text())["stages"]
    baseline = json.loads((OUT / "baseline.json").read_text())["stages"]
    rules = json.loads((OUT / "original_contract.json").read_text())
    generator = helpers.audit.load_module("coherent_generator", ROOT / "evaluator/hidden/generate.py")
    summaries = {}
    for pattern_index, pattern in enumerate(("uniform", "near_uniform", "binary_defects")):
        for size_index, shapes in enumerate(([[4,4],[4,6],[6,4]], [[6,6],[6,8],[8,8]])):
            name = pattern + ("_small" if size_index == 0 else "_large")
            seed = 82844000 + 100 * pattern_index + size_index
            sampling = copy.deepcopy(rules)
            sampling["sampling"]["families"] = [family for family in rules["sampling"]["families"] if family["name"] == "flux_disordered"]
            sampling["sampling"]["lattice_shapes"] = shapes
            instances = generator.draw_suite(sampling, seed, 192)["instances"]
            random = np.random.default_rng(seed + 1000)
            for instance in instances:
                size = len(instance["site_potential"])
                strength = float(random.uniform(0.5,2.0))
                chemical = float(random.uniform(-0.4,0.4))
                sign = int(random.choice([-1,1]))
                parameters = {"field_strength":strength,"chemical_potential":chemical,"global_sign":sign,"pattern":pattern}
                if pattern == "near_uniform":
                    noise = float(random.uniform(0.05,0.20))
                    fields = sign * (1 + noise * random.uniform(-1,1,size))
                    parameters["relative_noise"] = noise
                elif pattern == "binary_defects":
                    defect_probability = float(random.uniform(0.02,0.15))
                    fields = sign * np.where(random.random(size) < defect_probability, -1.0, 1.0)
                    parameters["defect_probability"] = defect_probability
                    parameters["actual_defects"] = int(np.count_nonzero(fields != sign))
                else:
                    fields = np.full(size,float(sign))
                instance["site_potential"] = (strength * fields - chemical).tolist()
                instance["audit_parameters"] = parameters
                instance["id"] = name + ':' + instance["id"]
            records = []
            for offset in range(0,len(instances),48):
                records.extend(helpers.audit.audit_batch(instances[offset:offset+48],candidate,baseline,rules["components"],[0.4,0.6,0.8,1.0]))
            law = {"hopping":"unchanged original flux_disordered hopping/Peierls law", "onsite":"V_i=A*s_i-mu; A=U[.5,2], mu=U[-.4,.4], equiprobable global sign", "pattern":pattern,"near_uniform_definition":"s_i=s*(1+rho*eta_i), rho=U[.05,.20], eta_i iid U[-1,1]", "binary_defects_definition":"flip the global sign independently at each site with p=U[.02,.15] drawn per instance", "shapes":shapes,"seed":seed,"field_seed":seed+1000,"count":192,"steps":[0.4,0.6,0.8,1.0],"repetitions":[1,4],"selection":"none; all generated cases tested"}
            summaries[name] = helpers.save_regime(name,instances,records,law)
            helpers.audit.write_json(OUT / "summary.json", {"candidate_sha256":hashlib.sha256((OUT / 'candidate.json').read_bytes()).hexdigest(),"elapsed_wall_seconds":time.monotonic()-started,"regimes":summaries,"participant_or_targets_modified":False})
    print("COHERENT_FLUX_AUDIT_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
